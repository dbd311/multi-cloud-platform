#!/bin/bash
# Date: 13.03.2025
# Deploy the multi-cloud-multi-tenant platform to a Kubernetes cluster

set -euo pipefail

# Check required arguments 
if [ $# -ne 3 ]; then
  echo "Usage: $0 <BACK_END_VERSION> <FRONT_END_VERSION> <PROJECT_DIR>"
  exit 1
fi

BACK_END_VERSION=$1 # v1.0.0
FRONT_END_VERSION=$2 # v1.2.3
PROJECT_DIR=$3 # ~/workspace/multi-cloud-multi-tenant

# Navigate to the setup directory
if ! cd "$PROJECT_DIR/setup"; then
  echo "Failed to navigate to $PROJECT_DIR/setup"
  exit 1
fi

# Install Secrets Store CSI driver
CSI_DRIVER_VERSION="v1.3.4"
echo "Installing Secrets Store CSI driver..."
for manifest in rbac-secretproviderclass csidriver secrets-store.csi.x-k8s.io_secretproviderclasses secrets-store.csi.x-k8s.io_secretproviderclasspodstatuses secrets-store-csi-driver; do
  kubectl apply -f "https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/$CSI_DRIVER_VERSION/deploy/$manifest.yaml"
done

# Install GCP provider for Secrets Store CSI driver
echo "Installing GCP provider for Secrets Store CSI driver..."
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/secrets-store-csi-driver-provider-gcp/main/deploy/provider-gcp-plugin.yaml

# Create SecretProviderClass
echo "Creating SecretProviderClass..."
kubectl apply -f gcp-secret-provider-class.yaml

# Verify provisioned pods
echo "Verifying provisioned pods..."
kubectl get pods -n kube-system -l app=csi-secrets-store-provider-gcp
kubectl get pods -n kube-system -l app=csi-secrets-store

# Database setup and security setup using Terraform
echo "Initializing Terraform..."
if ! terraform init; then
  echo "Terraform initialization failed"
  exit 1
fi

if ! terraform plan; then
  echo "Terraform plan failed"
  exit 1
fi

if ! terraform apply -auto-approve; then
  echo "Terraform apply failed"
  exit 1
fi

# Authenticate with GCP
echo "Authenticating with GCP..."
if ! gcloud auth login; then
  echo "GCP login failed"
  exit 1
fi

if ! gcloud auth configure-docker; then
  echo "Docker configuration failed"
  exit 1
fi

# Helper function to build and push Docker images
build_and_push() {
  local component=$1
  local version=$2
  local dir=$3

  echo "Building and pushing the $component Docker image..."
  if ! cd "$PROJECT_DIR/$dir"; then
    echo "Failed to navigate to $PROJECT_DIR/$dir"
    exit 1
  fi

  if ! docker build -t "$component:$version" .; then
    echo "$component Docker build failed"
    exit 1
  fi

  project_id=$(gcloud config get-value project)
  if ! docker tag "$component:$version" "gcr.io/${project_id}/$component:$version"; then
    echo "$component Docker tag failed"
    exit 1
  fi

  if ! docker push "gcr.io/${project_id}/$component:$version"; then
    echo "$component Docker push failed"
    exit 1
  fi
}

# Build and push backend and frontend images
build_and_push "nginx-backend" "$BACK_END_VERSION" "backend"
build_and_push "nginx-frontend" "$FRONT_END_VERSION" "frontend"

# Deploy to Kubernetes
deploy_component() {
  local component=$1

  echo "Deploying the $component..."
  for file in "$component-deployment.yaml" "$component-service.yaml" "$component-ingress.yaml"; do
    if [ -f "$file" ]; then
      kubectl apply -f "$file" || { echo "$component deployment failed"; exit 1; }
    fi
  done
}

# Wait for a few minutes until DB setup successfully done and docker images are available in the image registry
Sleep 180

deploy_component "backend"
deploy_component "frontend"

echo "Deployment completed successfully!"
