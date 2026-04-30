#k8s/services/product-service/00-product-build-push.sh
#!/bin/bash

echo "Building and pushing Product service image"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "script dir = $SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
echo "Project root = $PROJECT_ROOT"

cd "$PROJECT_ROOT/product-service"

docker build -t product-service:1.0.0 \
    --build-arg ENVIRONMENT=production \
    --build-arg PORT=5002 \
    .

docker tag product-service:1.0.0 localhost:32000/product-service:1.0.0

microk8s enable registry 

docker push localhost:32000/product-service:1.0.0

echo "Product service pushed"