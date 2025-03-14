#
# The backend of the Multi-cloud multi-tenant platform
#
from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from kubernetes import client, config
import random
import string
import re
import boto3  # For AWS Route 53

from google.cloud import dns  # For Google Cloud DNS
from google.cloud import secretmanager  # For Google Cloud Secret Manager

from azure.mgmt.dns import DnsManagementClient  # For Azure DNS
from azure.identity import DefaultAzureCredential  # For Azure authentication
import os

app = Flask(__name__)

# Initialize Google Cloud Secret Manager client
secret_client = secretmanager.SecretManagerServiceClient()

# Function to retrieve a secret from GCP Secret Manager
def get_secret(secret_name):
    try:
        response = secret_client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Failed to retrieve secret: {e}")
        raise

# Retrieve SQLALCHEMY_DATABASE_URI and JWT_SECRET_KEY from GCP Secret Manager
try:
    app.config['SQLALCHEMY_DATABASE_URI'] = get_secret("projects/multi-cloud-platform/secrets/database-uri/versions/latest")
    app.config['JWT_SECRET_KEY'] = get_secret("projects/multi-cloud-platform/secrets/jwt-secret-key/versions/latest")
except Exception as e:
    print(f"Failed to retrieve secrets: {e}")
    exit(1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# Deployment model
class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(80), nullable=False)
    public_url = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
# Validate domain using regex
def validate_domain(domain):
    domain_regex = re.compile(
        r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.IGNORECASE
    )
    return bool(domain_regex.match(domain))

# Generate a unique app name
# App name has a random 4-character alphanumeric string
def generate_app_name():
    return f"nginx-{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"

# Generate a public URL
# app_name must be unique ==> genenerated URL is unique for each deployment
def generate_public_url(cloud_provider, domain, namespace, app_name):
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"http://{namespace}.{app_name}.{cloud_provider}.{domain}"
    
# Create DNS record for AWS Route 53
def create_aws_dns_record(domain, ip_address):
    client = boto3.client('route53')
    hosted_zone_id = os.getenv('AWS_HOSTED_ZONE_ID')  # Hosted Zone ID for your domain
    response = client.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': domain,
                        'Type': 'A',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': ip_address}]
                    }
                }
            ]
        }
    )
    return response

# Create DNS record for Google Cloud DNS
def create_gcp_dns_record(domain, ip_address):
    client = dns.Client()
    zone = client.zone(os.getenv('GCP_DNS_ZONE_NAME'))  # DNS zone name
    record_set = zone.resource_record_set(
        domain, 'A', 300, [ip_address])
    changes = zone.changes()
    changes.add_record_set(record_set)
    changes.create()
    return changes

# Create DNS record for Azure DNS
def create_azure_dns_record(domain, ip_address):
    credential = DefaultAzureCredential()
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    resource_group = os.getenv('AZURE_DNS_RESOURCE_GROUP')
    zone_name = os.getenv('AZURE_DNS_ZONE_NAME')

    dns_client = DnsManagementClient(credential, subscription_id)
    dns_client.record_sets.create_or_update(
        resource_group,
        zone_name,
        domain,
        'A',
        {
            "ttl": 300,
            "arecords": [{"ipv4_address": ip_address}]
        }
    )

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    username = request.json['username']
    password = request.json['password']
    role = request.json['role']

    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    new_user = User(username=username, password_hash=password_hash, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"status": "User registered"})


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(username=username).first()

    if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        access_token = create_access_token(identity={"username": user.username, "role": user.role})
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dev_dashboard'))
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/admin-dashboard')
def admin_dashboard():
    return "Welcome to the Admin Dashboard"

@app.route('/dev-dashboard')
def dev_dashboard():
    return "Welcome to the Dev Dashboard"
        
# Protected endpoint to deploy Nginx
@app.route('/deploy', methods=['POST'])
@jwt_required()  # Protect this endpoint with JWT authentication
def deploy():
    # Get the current user's identity from the JWT
    current_user = get_jwt_identity()
    if current_user['role'] != 'dev' and current_user['role'] != 'admin': # as defined in the spec, only dev and admin are allowed in the platform
        return jsonify({"error": "Unauthorized"}), 403

    # Validate inputs
    cloud_provider = request.json.get('cloud_provider', 'aws')  # Default to AWS
    domain = request.json.get('domain', 'example.com')
    namespace = request.json.get('namespace', 'default') # If no namespace is specified, default namespace is used
    app_name = request.json.get('appname', 'default-app') # If no app is specified, default-app is used
    
    if not validate_domain(domain):
        return jsonify({"error": "Invalid domain"}), 400

    if cloud_provider not in ["aws", "gcp", "azure"]:
        return jsonify({"error": "Unsupported cloud provider"}), 400

    # Load Kubernetes config for the specified cloud provider
    try:
        config.load_kube_config(context=cloud_provider)
    except Exception as e:
        return jsonify({"error": f"Failed to load Kubernetes config: {str(e)}"}), 500

    # Generate a unique app name and public URL
    #app_name = generate_app_name()
    public_url = generate_public_url(cloud_provider, domain, namespace, app_name)

    # Create Kubernetes deployment
    try:
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=app_name),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": app_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": app_name}),
                    spec=client.V1PodSpec(
                        containers=[client.V1Container(name=app_name, image="nginx:latest")] # use the latest version of nginx Docker image available at https://hub.docker.com/_/nginx 
                    )
                )
            )
        )
        apps_v1 = client.AppsV1Api()
        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
    except Exception as e:
        return jsonify({"error": f"Failed to create deployment: {str(e)}"}), 500

    # Create Kubernetes service https://kubernetes.io/docs/concepts/services-networking/service/
    # to expose the nginx application (that is running as one or more Pods) in the cluster.
    try:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=app_name),
            spec=client.V1ServiceSpec(
                selector={"app": app_name},
                ports=[client.V1ServicePort(port=80, target_port=80)]
            )
        )
        k8s = client.CoreV1Api()
        k8s.create_namespaced_service(namespace=namespace, body=service)
    except Exception as e:
        return jsonify({"error": f"Failed to create service: {str(e)}"}), 500

    # Create Kubernetes ingress https://kubernetes.io/docs/concepts/services-networking/ingress/
    # to manage external access to the http service on port 80 in a cluster
    try:
        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(name=app_name, annotations={
                "nginx.ingress.kubernetes.io/rewrite-target": "/"
            }),
            spec=client.V1IngressSpec(
                rules=[client.V1IngressRule(
                    host=public_url.split("//")[1],
                    http=client.V1HTTPIngressRuleValue(
                        paths=[client.V1HTTPIngressPath(
                            path="/",
                            path_type="Prefix",
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    name=app_name,
                                    port=client.V1ServiceBackendPort(number=80)
                                )
                            )
                        )]
                    )
                )]
            )
        )
        networking_v1 = client.NetworkingV1Api()
        networking_v1.create_namespaced_ingress(namespace=namespace, body=ingress)
    except Exception as e:
        return jsonify({"error": f"Failed to create ingress: {str(e)}"}), 500
    
    # Retrieve the external IP address of the ingress
    try:
        ingress_ip = networking_v1.read_namespaced_ingress(
            name=app_name, namespace=namespace
        ).status.load_balancer.ingress[0].ip
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve ingress IP: {str(e)}"}), 500

    # Create DNS record based on the cloud provider
    try:
        if cloud_provider == "aws":
            create_aws_dns_record(public_url.split("//")[1], ingress_ip)
        elif cloud_provider == "gcp":
            create_gcp_dns_record(public_url.split("//")[1], ingress_ip)
        elif cloud_provider == "azure":
            create_azure_dns_record(public_url.split("//")[1], ingress_ip)
    except Exception as e:
        return jsonify({"error": f"Failed to create DNS record: {str(e)}"}), 500

    return jsonify({"status": "Deployment created", "public_url": public_url})

# Undeploy a specific Nginx deployment
@app.route('/undeploy', methods=['POST'])
@jwt_required()  # Protect this endpoint with JWT authentication
def undeploy():
    # Get the current user's identity from the JWT
    current_user = get_jwt_identity()
    if current_user['role'] != 'dev' and current_user['role'] != 'admin': # as defined in the spec, only dev and admin are allowed in the platform
        return jsonify({"error": "Unauthorized"}), 403

    # Get the deployment name from the request
    app_name = request.json.get('app_name')
    if not app_name:
        return jsonify({"error": "App name is required"}), 400

    # Delete the Kubernetes deployment
    try:
        apps_v1 = client.AppsV1Api()
        apps_v1.delete_namespaced_deployment(
            name=app_name,
            namespace="default",
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
    except Exception as e:
        return jsonify({"error": f"Failed to delete deployment: {str(e)}"}), 500

    # Delete the Kubernetes service
    try:
        core_v1 = client.CoreV1Api()
        core_v1.delete_namespaced_service(
            name=app_name,
            namespace="default",
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
    except Exception as e:
        return jsonify({"error": f"Failed to delete service: {str(e)}"}), 500

    # Delete the Kubernetes ingress
    try:
        networking_v1 = client.NetworkingV1Api()
        networking_v1.delete_namespaced_ingress(
            name=app_name,
            namespace="default",
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
    except Exception as e:
        return jsonify({"error": f"Failed to delete ingress: {str(e)}"}), 500

    # Delete the DNS record
    
    return jsonify({"status": "Undeployment successful", "app_name": app_name})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)