#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

echo "Applying Kubernetes manifests"

microk8s kubectl apply -f k8s/00-namespace-production.yml
microk8s kubectl apply -f k8s/01-config-maps-production.yml
microk8s kubectl apply -f k8s/02-secrets-producao.yml

# Databases - user
echo "Deploying user database..."
microk8s kubectl apply -f k8s/databases/mysql-user/00-init-mysql-configmap.yml
microk8s kubectl apply -f k8s/databases/mysql-user/01-pvc.yml
microk8s kubectl apply -f k8s/databases/mysql-user/02-statefulset.yml
microk8s kubectl apply -f k8s/databases/mysql-user/03-service.yml

# Databases - product
echo "Deploying product database..."
microk8s kubectl apply -f k8s/databases/mysql-product/00-init-mysql-configmap.yml
microk8s kubectl apply -f k8s/databases/mysql-product/01-pvc.yml
microk8s kubectl apply -f k8s/databases/mysql-product/02-statefulset.yml
microk8s kubectl apply -f k8s/databases/mysql-product/03-service.yml

# Services - user
echo "Deploying user service..."
microk8s kubectl apply -f k8s/services/user-service/01-deployment.yml
microk8s kubectl apply -f k8s/services/user-service/02-service.yml
microk8s kubectl apply -f k8s/services/user-service/03-hpa.yml

# Services - product
echo "Deploying product service..."
microk8s kubectl apply -f k8s/services/product-service/01-product-deployment.yml
microk8s kubectl apply -f k8s/services/product-service/02-product-service.yml
microk8s kubectl apply -f k8s/services/product-service/03-product-hpa.yml

# Networking
echo "Deploying ingress..."
microk8s kubectl apply -f k8s/networking/01-ingress.yml

# Wait for pods
echo "Waiting for pods to be ready..."
sleep 30

# Status final
echo ""
echo "========================================="
echo "Final status:"
echo "========================================="
microk8s kubectl get pods -n projeto-final
echo ""
microk8s kubectl get svc -n projeto-final
echo ""
microk8s kubectl get hpa -n projeto-final
echo ""

echo "Deployment completed successfully!"