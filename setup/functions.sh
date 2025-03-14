#!/bin/bash

source ./env_vars.sh

# Function to check if a project exists
project_exists() {
    gcloud projects list --filter="projectId=${PROJECT_ID}" --format="value(projectId)" | grep -q "^${PROJECT_ID}$"
}

# Check if the project already exists
if project_exists; then
    echo "Project '${PROJECT_ID}' already exists."
else
    echo "Project '${PROJECT_ID}' does not exist. Creating a new project..."

    # Create the new project
    gcloud projects create "${PROJECT_ID}" --name="${PROJECT_NAME}" --billing-account="${BILLING_ACCOUNT}"

    # Check if the project creation was successful
    if [ $? -eq 0 ]; then
        echo "Project '${PROJECT_ID}' created successfully."
    else
        echo "Failed to create project '${PROJECT_ID}'. Exiting."
        exit 1
    fi
fi

# Set the newly created project as the active project
gcloud config set project "${PROJECT_ID}"

# Retrieve and display the project ID
RETRIEVED_PROJECT_ID=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectId)")
echo "Active Project ID: ${RETRIEVED_PROJECT_ID}"

# Function to create a DNS record for the backend
create_backend_dns_record() {
  local BACKEND_IP=$(kubectl get svc backend-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  local MANAGED_ZONE="backend-zone"
  local DNS_NAME="backend.${DOMAIN_NAME}."
  local DNS_TYPE="A"
  local DNS_TTL="300"
  local DNS_DATA="$BACKEND_IP"

  # Step 1: Check if the managed zone exists
  echo "Checking if managed zone '$MANAGED_ZONE' exists..."
  local EXISTING_ZONE=$(gcloud dns managed-zones list --filter="name=$MANAGED_ZONE" --format="value(name)")

  if [[ -z "$EXISTING_ZONE" ]]; then
    echo "Managed zone '$MANAGED_ZONE' does not exist. Creating it..."
    gcloud dns managed-zones create "$MANAGED_ZONE" \
      --dns-name="$DOMAIN_NAME." \
      --description="Managed zone for backend services" \
      --visibility="public" \
      --project="$PROJECT_ID"
    echo "Managed zone '$MANAGED_ZONE' created."
  else
    echo "Managed zone '$MANAGED_ZONE' already exists."
  fi

  # Step 2: Check if the DNS record exists
  echo "Checking if DNS record '$DNS_NAME' exists..."
  local EXISTING_RECORD=$(gcloud dns record-sets list --zone="$MANAGED_ZONE" --name="$DNS_NAME" --type="$DNS_TYPE" --format="value(name)")

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