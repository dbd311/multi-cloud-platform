from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from kubernetes import client, config
import random
import string
import bcrypt
from google.cloud import secretmanager
import os

app = Flask(__name__)

# Initialize Google Cloud Secret Manager client
secret_client = secretmanager.SecretManagerServiceClient()

# Function to retrieve a secret from GCP Secret Manager
def get_secret(secret_name):
    response = secret_client.access_secret_version(request={"name": secret_name})
    return response.payload.data.decode("UTF-8")

# Retrieve JWT secret key and database URI from GCP Secret Manager
app.config['JWT_SECRET_KEY'] = get_secret("projects/multi-cloud/secrets/jwt-secret/versions/latest")
app.config['SQLALCHEMY_DATABASE_URI'] = get_secret("projects/multi-cloud/secrets/database-uri/versions/latest")

# Initialize SQLAlchemy for PostgreSQL
db = SQLAlchemy(app)

# Configure JWT
jwt = JWTManager(app)

# User model for PostgreSQL
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# Load Kubernetes config for the selected cloud provider
def load_kube_config(cloud_provider):
    if cloud_provider == "aws":
        config.load_kube_config(context="aws-eks-cluster")  # e.g. arn:aws:eks:<region>:<account-id>:cluster/<cluster-name>
    elif cloud_provider == "gcp":
        config.load_kube_config(context="gcp-gke-cluster")  # e.g. gke_<project-id>_<region>_<cluster-name>
    elif cloud_provider == "azure":
        config.load_kube_config(context="azure-aks-cluster")  # e.g. my-aks-cluster
    # add other cloud providers here ...
    # to get all contexts: kubectl config get-contexts    
    else:
        raise ValueError("Unsupported cloud provider")

# Generate a unique public URL
def generate_public_url(cloud_provider, domain):    
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"http://{random_string}.{domain}"

# User login endpoint
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    # Query the user from the PostgreSQL database
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Verify the password
    if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"error": "Invalid credentials"}), 401

    # Create a JWT token
    access_token = create_access_token(identity={"username": user.username, "role": user.role})
    return jsonify({"access_token": access_token})

#
# User logout functions etc.
#

# Protected endpoint to deploy Nginx
@app.route('/deploy', methods=['POST'])
@jwt_required()  # Protect this endpoint with JWT authentication
def deploy():
    # Get the current user's identity from the JWT
    current_user = get_jwt_identity()
    if current_user['role'] != 'user':
        return jsonify({"error": "Unauthorized"}), 403

    cloud_provider = request.json.get('cloud_provider', 'aws')  # Default to AWS
    domain = request.json.get('domain', 'example.com')
    load_kube_config(cloud_provider)

    # Generate a unique app name and public URL
    app_name = f"nginx-{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
    public_url = generate_public_url(cloud_provider, domain)

    # Create Kubernetes deployment
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=app_name),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": app_name}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": app_name}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name=app_name, image="nginx:latest")]
                )
            )
        )
    )
    apps_v1 = client.AppsV1Api()
    apps_v1.create_namespaced_deployment(namespace="default", body=deployment)

    # Create Kubernetes service
    service = client.V1Service(
        metadata=client.V1ObjectMeta(name=app_name),
        spec=client.V1ServiceSpec(
            selector={"app": app_name},
            ports=[client.V1ServicePort(port=80, target_port=80)]
        )
    )
    k8s = client.CoreV1Api()
    k8s.create_namespaced_service(namespace="default", body=service)

    # Create Kubernetes ingress
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
    networking_v1.create_namespaced_ingress(namespace="default", body=ingress)

    return jsonify({"status": "Deployment created", "public_url": public_url})

# Initialize the database (run once)
#@app.before_first_request
#def initialize_database():
#    db.create_all()
    # Add a sample user (for testing purposes)
#    if not User.query.filter_by(username="john_doe").first():
#        hashed_password = bcrypt.hashpw(b"password123", bcrypt.gensalt())
#        new_user = User(username="john_doe", password_hash=hashed_password, role="user")
#        db.session.add(new_user)
#        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)