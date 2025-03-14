from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from kubernetes import client, config
from dns_manager import create_dns_record, delete_dns_record

deployment_bp = Blueprint('deployment', __name__)

# Protected endpoint to deploy Nginx app
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

    create_dns_record(cloud_provider, public_url, ingress_ip)

    return jsonify({"status": "Deployment created", "public_url": public_url})

# Endpoint to Undeploy an nginx app
@app.route('/undeploy', methods=['POST'])
@jwt_required()  # Protect this endpoint with JWT authentication
def undeploy():
    # Get the current user's identity from the JWT
    current_user = get_jwt_identity()
    if current_user['role'] != 'dev' and current_user['role'] != 'admin': # as defined in the spec, only dev and admin are allowed in the platform
        return jsonify({"error": "Unauthorized"}), 403

    cloud_provider = request.json.get('cloud_provider', 'aws')  # Default to AWS
    domain = request.json.get('domain', 'example.com')
    namespace = request.json.get('namespace', 'default') # If no namespace is specified, default namespace is used
    app_name = request.json.get('appname', 'default-app') # If no app is specified, default-app is used

    # Delete the Kubernetes deployment
    try:
        apps_v1 = client.AppsV1Api()
        apps_v1.delete_namespaced_deployment(
            name=app_name,
            namespace=namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
    except Exception as e:
        return jsonify({"error": f"Failed to delete deployment: {str(e)}"}), 500

    # Delete the Kubernetes service
    try:
        core_v1 = client.CoreV1Api()
        core_v1.delete_namespaced_service(
            name=app_name,
            namespace=namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
    except Exception as e:
        return jsonify({"error": f"Failed to delete service: {str(e)}"}), 500

    # Delete the Kubernetes ingress
    try:
        networking_v1 = client.NetworkingV1Api()
        networking_v1.delete_namespaced_ingress(
            name=app_name,
            namespace=namespace,
            body=client.V1DeleteOptions(propagation_policy="Foreground")
        )
    except Exception as e:
        return jsonify({"error": f"Failed to delete ingress: {str(e)}"}), 500

    # Delete the DNS record
    delete_dns_record(cloud_provider, domain, namespace, app_name)
    return jsonify({"status": "Undeployment successful", "app_name": app_name, "namespace": namespace, "domain": domain, "cloud_provider": cloud_provider})    

