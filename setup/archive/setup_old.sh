#!/bin/bash
# Date: 13.03.2025
# Deploy the multi-cloud-multi-tenant platform to a Kubernetes cluster

# Check required arguments 
if [ $# -ne 3 ]; then
  echo "Usage: $0 <BACK_END_VERSION> <FRONT_END_VERSION> <PROJECT_DIR>"
  exit 1
fi

BACK_END_VERSION=$1 # v1.0.0
FRONT_END_VERSION=$2 # v1.2.3
PROJECT_DIR=$3 # ~/workspace/multi-cloud-multi-tenant

# Navigate to the setup directory
cd "$PROJECT_DIR/setup" || { echo "Failed to navigate to $PROJECT_DIR/setup"; exit 1; }

# Install Secrets Store CSI driver - CSI (Container Storage Interface) https://github.com/container-storage-interface/spec/blob/master/spec.md
echo "Installing Secrets Store CSI driver..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.3.4/deploy/rbac-secretproviderclass.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.3.4/deploy/csidriver.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.3.4/deploy/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.3.4/deploy/secrets-store.csi.x-k8s.io_secretproviderclasspodstatuses.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.3.4/deploy/secrets-store-csi-driver.yaml

# Install GCP provider for Secrets Store CSI driver
echo "Installing GCP provider for Secrets Store CSI driver..."
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/secrets-store-csi-driver-provider-gcp/main/deploy/provider-gcp-plugin.yaml

# Create a SecretProviderClass: define a Kubernetes custom resource enabling secure access of secrets stored in GCP Secrets Manager
echo "Creating SecretProviderClass..."
kubectl apply -f gcp-secret-provider-class.yaml

# Verify the provisioned pods
echo "Verifying provisioned pods..."
kubectl get pods -n kube-system -l app=csi-secrets-store-provider-gcp
kubectl get pods -n kube-system -l app=csi-secrets-store

# Database setup and security setup using Terraform
echo "Initializing Terraform..."
terraform init || { echo "Terraform initialization failed"; exit 1; }

echo "Planning Terraform configuration..."
terraform plan || { echo "Terraform plan failed"; exit 1; }

echo "Applying Terraform configuration..."
terraform apply -auto-approve || { echo "Terraform apply failed"; exit 1; }

# Authenticate with GCP
echo "Authenticating with GCP..."
gcloud auth login || { echo "GCP login failed"; exit 1; }
gcloud auth configure-docker || { echo "Docker configuration failed"; exit 1; }

# Build and push the backend Docker image
echo "Building and pushing the backend Docker image..."
cd "$PROJECT_DIR/backend" || { echo "Failed to navigate to $PROJECT_DIR/backend"; exit 1; }
docker build -t nginx-backend:"$BACK_END_VERSION" . || { echo "Backend Docker build failed"; exit 1; }
project_id=$(gcloud config get-value project) || { echo "Failed to get GCP project ID"; exit 1; }
docker tag nginx-backend:"$BACK_END_VERSION" "gcr.io/${project_id}/nginx-backend:$BACK_END_VERSION" || { echo "Backend Docker tag failed"; exit 1; }
docker push "gcr.io/${project_id}/nginx-backend:$BACK_END_VERSION" || { echo "Backend Docker push failed"; exit 1; }

# Deploy the backend to Kubernetes
echo "Deploying the backend..."
kubectl apply -f backend-deployment.yaml || { echo "Backend deployment failed"; exit 1; }
kubectl apply -f backend-service.yaml || { echo "Backend service deployment failed"; exit 1; }

# Build and push the frontend Docker image
echo "Building and pushing the frontend Docker image..."
cd "$PROJECT_DIR/frontend" || { echo "Failed to navigate to $PROJECT_DIR/frontend"; exit 1; }
docker build -t nginx-frontend:"$FRONT_END_VERSION" . || { echo "Frontend Docker build failed"; exit 1; }
project_id=$(gcloud config get-value project) || { echo "Failed to get GCP project ID"; exit 1; }
docker tag nginx-frontend:"$FRONT_END_VERSION" "gcr.io/${project_id}/nginx-frontend:$FRONT_END_VERSION" || { echo "Frontend Docker tag failed"; exit 1; }
docker push "gcr.io/${project_id}/nginx-frontend:$FRONT_END_VERSION" || { echo "Frontend Docker push failed"; exit 1; }

# Deploy the frontend to Kubernetes
echo "Deploying the frontend..."
kubectl apply -f frontend-deployment.yaml || { echo "Frontend deployment failed"; exit 1; }
kubectl apply -f frontend-service.yaml || { echo "Frontend service deployment failed"; exit 1; }
kubectl apply -f frontend-ingress.yaml || { echo "Frontend ingress deployment failed"; exit 1; }

echo "Deployment completed successfully!"