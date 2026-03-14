#!/bin/bash

# Apply Kubernetes manifests
microk8s kubectl apply -f k8s/00-namespace-production.yml
microk8s kubectl apply -f k8s/01-config-maps-production.yml
microk8s kubectl apply -f k8s/02-secrets-producao.yml
microk8s kubectl apply -f k8s/databases/
microk8s kubectl apply -f k8s/services/
microk8s kubectl apply -f k8s/networking/

# status verification
microk8s kubectl get all -n projeto-final

echo "Deployment completed successfully!"