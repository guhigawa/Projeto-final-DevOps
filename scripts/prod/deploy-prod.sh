#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

echo "Applying Kubernetes manifests"

microk8s kubectl apply -f k8s/00-namespace-production.yml
microk8s kubectl apply -f k8s/01-config-maps-production.yml
microk8s kubectl apply -f k8s/02-secrets.template.yml

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
echo "Waiting for pods to be ready"


wait_for_pods() {
    local namespace="projeto-final"
    local timeout=300  # 5 minutos
    local interval=5
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        # Contar pods não prontos
        NOT_READY=$(microk8s kubectl get pods -n "$namespace" --no-headers 2>/dev/null | grep -v "Running" | grep -v "Completed" | wc -l || echo "0")
        
        if [ "$NOT_READY" -eq 0 ]; then
            # Verificar se todos os pods têm READY 1/1
            ALL_READY=$(microk8s kubectl get pods -n "$namespace" --no-headers 2>/dev/null | awk '{print $2}' | grep -v "1/1" | wc -l || echo "0")
            if [ "$ALL_READY" -eq 0 ]; then
                echo "All pods are ready after $elapsed seconds!"
                return 0
            fi
        fi
        
        echo " Waiting for pods to be ready($elapsed seconds)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    echo " timeout reached while waiting for pods to be ready! $timeout seconds "
    return 1
}


# Status final
if wait_for_pods; then
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

echo ""
echo "========================================="
    echo "Configuring services accessibility"
    echo "========================================="
    
    # Verificar se as entradas já existem no /etc/hosts
    if grep -q "user.local.prod" /etc/hosts 2>/dev/null; then
        echo "Entries already exist in /etc/hosts"
    else
        echo "Adding entries to /etc/hosts..."
        echo "127.0.0.1 user.local.prod product.local.prod" | sudo tee -a /etc/hosts > /dev/null
        echo "Entries added successfully!"
    fi
    
    echo ""
    echo " Available Endpoints:"
    echo "   User Service:    http://user.local.prod/health"
    echo "   Product Service: http://product.local.prod/health"
    echo ""
    echo " Test the endpoints:"
    echo "   curl http://user.local.prod/health"
    echo "   curl http://product.local.prod/health"
    echo "========================================="
else
    echo ""
    echo "Some pods are not ready after waiting for 5 minutes. Please check the status of the pods and investigate any issues."
    echo "Verify with: microk8s kubectl get pods -n projeto-final"
fi