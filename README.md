# Multi-Cloud Multi-Tenant Platform Deployment

Prerequisites
1.	Kubernetes Cluster: Set up a Kubernetes cluster (e.g., using Minikube for local development or managed Kubernetes services like GKE, EKS, or AKS).
2.	Ingress Controller: Install an Ingress Controller (e.g., NGINX Ingress Controller) to expose applications publicly.
3.	PostgreSQL Database: Set up a PostgreSQL database for storing user and deployment information.
4.	Docker: Install Docker to containerize the backend and frontend.
5.	Helm: the package manager that facilitates deployment of Kubernetes resources.
   
Dependencies
1.	Flask: The web framework used to build the backend (python).
2.	Flask-SQLAlchemy: Provides integration between Flask and SQLAlchemy (database management in python).
3.	Flask-JWT-Extended: Handles JWT-based authentication and authorization.
4.	kubernetes: The official Python client for interacting with Kubernetes clusters.
5.	bcrypt: Used for hashing passwords securely.
6.	gunicorn: A production-ready WSGI server for serving the Flask app.
7.	psycopg2-binary: A PostgreSQL adapter for Python (required for connecting to the PostgreSQL database).



Automate the deployment of a multi-cloud, multi-tenant platform to a Kubernetes cluster. It sets up required infrastructure, provisions secrets management, and deploys backend and frontend services using Docker and Kubernetes.

## Prerequisites

Before running the script, ensure the following tools are installed and configured:

- [bash](https://www.gnu.org/software/bash/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://www.terraform.io/downloads.html)
- [Docker](https://docs.docker.com/get-docker/)

Also, make sure:

- You have access to a Kubernetes cluster.
- Your GCP project and credentials are configured (`gcloud auth login` and `gcloud config set project <YOUR_PROJECT_ID>`).

## Usage

```bash
./deploy_multicloud.sh <BACK_END_VERSION> <FRONT_END_VERSION> <PROJECT_DIR> <BACKEND_RELEASE_URL> <FRONTEND_RELEASE_URL>
```

**Arguments:**

- `BACK_END_VERSION` — The version of the backend Docker image (e.g., `v1.0.0`)
- `FRONT_END_VERSION` — The version of the frontend Docker image (e.g., `v1.2.3`)
- `PROJECT_DIR` — The root directory of the project (e.g., `~/workspace/multi-cloud-multi-tenant`)
- `BACKEND_RELEASE_URL` — The release URL of the backend 
- `FRONTEND_RELEASE_URL` — The release URL of the frontend

## What the Script Does

1. **Sets up Secrets Management:**
   - Installs the Secrets Store CSI driver.
   - Installs the GCP provider for the Secrets Store.
   - Applies the `SecretProviderClass` configuration.
2. **Verifies CSI Driver Installation:**
   - Checks that the Secrets Store and GCP provider pods are running.
3. **Infrastructure Setup:**
   - Initializes and applies Terraform configuration.
4. **GCP Authentication:**
   - Logs into GCP and configures Docker for GCP Container Registry.
5. **Builds and Pushes Docker Images:**
   - Builds and pushes backend and frontend images to GCP Container Registry.
6. **Deploys Services to Kubernetes:**
   - Deploys the backend and frontend Kubernetes deployments, services, and ingress.

## Example

```bash
./deploy_multicloud.sh v1.0.0 v1.2.3 ~/workspace/multi-cloud-multi-tenant https://github.com/dbd311/backend-multicloud/archive/refs/tags/v1.0.0.zip https://github.com/dbd311/frontend-multicloud/archive/refs/tags/v1.0.0.zip 
```

## Troubleshooting

- If the script fails, check the logs for the exact step that failed.
- Ensure your GCP project and Kubernetes context are set correctly.
- Verify Terraform and Docker permissions.

## Cleanup

To clean up deployed resources:

```bash
kubectl delete -f backend-deployment.yaml
kubectl delete -f backend-service.yaml
kubectl delete -f frontend-deployment.yaml
kubectl delete -f frontend-service.yaml
kubectl delete -f frontend-ingress.yaml
```

## Install Minikube and its dependencies on Windows 10:

Open PowerShell as Administrator and run to enable HyperV:

    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

    Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All


Install Chocolatey (Package Manager for Windows)    

    Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

    choco --version

Install kubectl (Kubernetes CLI)

    choco install kubernetes-cli

    kubectl version --client

Install Minikube

    choco install minikube

    minikube version

Start Minikube

Launch PowerShell (Admin) and run:

    minikube start --driver=hyperv

(If using VirtualBox, replace hyperv with virtualbox.)


Verify Installation

    minikube status

    kubectl get nodes

    minikube dashboard

Troubleshooting

Delete and recreate the K82 cluster again

    minikube delete && minikube start --driver=hyperv

Allocate more CPU and RAM

    minikube config set cpus 4
    
    minikube config set memory 8192

Alternative: Start minikube with Docker Desktop

    minikube start --driver=docker

Check minikube and kubectl version

    minikube version

    kubectl version --client

    

## Tutorial

   https://www.youtube.com/watch?v=X48VuDVv0do