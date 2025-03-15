#!/bin/bash
# Date: 13.03.2025
# Deploy the multi-cloud-multi-tenant platform to a Kubernetes cluster

set -euo pipefail

source ./functions.sh

# Check required arguments 
if [ $# -ne 5 ]; then
  echo "Usage: $0 <BACK_END_VERSION> <FRONT_END_VERSION> <PROJECT_DIR> <BACKEND_RELEASE_URL> <FRONTEND_RELEASE_URL>"
  exit 1
fi

BACK_END_VERSION=$1 # v1.0.0
FRONT_END_VERSION=$2 # v1.2.3
PROJECT_DIR=$3 # ~/workspace/multi-cloud-multi-tenant

BACK_END_RELEASE=$4 # e.g. https://github.com/dbd311/backend-multicloud/archive/refs/tags/v1.0.0.zip
FRONT_END_RELEASE=$5 # e.g. https://github.com/dbd311/frontend-multicloud/archive/refs/tags/v1.0.0.zip

# Navigate to the setup directory
if ! cd "$PROJECT_DIR/setup"; then
  echo "Failed to navigate to $PROJECT_DIR/setup"
  exit 1
fi

if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running"
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
#!/bin/bash

# Function to build and push Docker images
build_and_push() {
  local component=$1  # e.g., frontend
  local version=$2   # e.g., 1.0.0
  local release=$3    # e.g., https://github.com/dbd311/frontend-multicloud/archive/refs/tags/v1.0.0.zip

  echo "Building and pushing the $component Docker image..."

  # Navigate to the project directory
  if ! cd "$PROJECT_DIR"; then
    echo "Failed to navigate to $PROJECT_DIR"
    exit 1
  fi

  # Download the release
  echo "Downloading repository..."
  if ! wget -q "$release"; then
    echo "Failed to download the release from $release"
    exit 1
  fi

  # Extract the release zip file
  local zip_file=$(basename "$release")
  local extract_dir="${component}-${version}"

  echo "Unzipping $zip_file..."
  if ! unzip -q "$zip_file" -d "$extract_dir"; then
    echo "Failed to unzip $zip_file"
    exit 1
  fi

  # Navigate to the extracted directory
  if ! cd "$extract_dir"/*; then
    echo "Failed to navigate to the extracted directory"
    exit 1
  fi

  # Build the Docker image
  echo "Building Docker image for $component..."
  if ! docker build -t "$component:$version" .; then
    echo "$component Docker build failed"
    exit 1
  fi

  # Tag the Docker image
  local project_id=$(gcloud config get-value project)
  echo "Tagging Docker image for $component..."
  if ! docker tag "$component:$version" "gcr.io/${project_id}/$component:$version"; then
    echo "$component Docker tag failed"
    exit 1
  fi

  # Push the Docker image
  echo "Pushing Docker image for $component..."
  if ! docker push "gcr.io/${project_id}/$component:$version"; then
    echo "$component Docker push failed"
    exit 1
  fi

  # Clean up
  echo "Cleaning up..."
  cd "$PROJECT_DIR"
  rm -rf "$zip_file" "$extract_dir"
}

# Build and push backend and frontend images
build_and_push "nginx-backend" "$BACK_END_VERSION" "backend" "$BACK_END_RELEASE" 
build_and_push "nginx-frontend" "$FRONT_END_VERSION" "frontend" "$FRONT_END_RELEASE" 

# Deploy to Kubernetes
deploy_component() {
  local component=$1

  echo "Deploying the $component..."
  for file in "$component-configMap.yaml" "$component-deployment.yaml" "$component-service.yaml" "$component-ingress.yaml"; do
    if [ -f "$file" ]; then
      kubectl apply -f "$file" || { echo "$component deployment failed"; exit 1; }
    fi
  done
}

# Create DNS record for backend if it does not exist
# gcloud dns managed-zones list

create_backend_dns_record(){
  BACKEND_IP=$(kubectl get svc backend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  MANAGED_ZONE="backend-zone"
  DNS_NAME="api.${DOMAIN_NAME}."
  DNS_TYPE="A"
  DNS_TTL="300"

  # Step 1: Check if the managed zone exists
  echo "Checking if managed zone '$MANAGED_ZONE' exists..."
  EXISTING_ZONE=$(gcloud dns managed-zones list --filter="name=$MANAGED_ZONE" --format="value(name)")

  if [[ -z "$EXISTING_ZONE" ]]; then
    echo "Managed zone '$MANAGED_ZONE' does not exist. Creating it..."
    gcloud dns managed-zones create "$MANAGED_ZONE" \
      --dns-name="$DNS_NAME" \
      --description="Managed zone for backend services" \
      --visibility="public" \
      --project="$PROJECT_ID"
    echo "Managed zone '$MANAGED_ZONE' created."
  else
    echo "Managed zone '$MANAGED_ZONE' already exists."
  fi

  # Step 2: Check if the DNS record exists
  echo "Checking if DNS record '$DNS_NAME' exists..."
  EXISTING_RECORD=$(gcloud dns record-sets list --zone="$MANAGED_ZONE" --name="$DNS_NAME" --type="$DNS_TYPE" --format="value(name)")

  if [[ -n "$EXISTING_RECORD" ]]; then
    echo "DNS record '$DNS_NAME' exists. Deleting it..."
    gcloud dns record-sets delete "$DNS_NAME" \
      --zone="$MANAGED_ZONE" \
      --type="$DNS_TYPE" \
      --project="$PROJECT_ID"
    echo "DNS record '$DNS_NAME' deleted."
  else
    echo "DNS record '$DNS_NAME' does not exist."
  fi

  # Step 3: Create the DNS record
  echo "Creating DNS record '$DNS_NAME'..."
  gcloud dns record-sets create "$DNS_NAME" \
    --zone="$MANAGED_ZONE" \
    --type="$DNS_TYPE" \
    --ttl="$DNS_TTL" \
    --rrdatas="$DNS_DATA" \
    --project="$PROJECT_ID"
  echo "DNS record '$DNS_NAME' created."
}

# Wait for a few minutes until DB setup successfully done and docker images are available in the image registry
#Sleep 180


deploy_component "backend"
kubectl wait --for=condition=available --timeout=300s deployment/backend-service

create_backend_dns_record
deploy_component "frontend"

echo "Deployment completed successfully!"
