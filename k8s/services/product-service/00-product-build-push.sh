#k8s/services/product-service/00-product-build-push.sh
#!/bin/bash

echo "Building and pushing Product service image"

cd ~/Downloads/Projeto_final/product-service

docker build -t product-service:1.0.0 \
    --build-arg ENVIRONMENT=production \
    --build-arg PORT=5002 \
    .

docker tag product-service:1.0.0 localhost:32000/product-service:1.0.0

microk8s enable registry 

docker push localhost:32000/product-service:1.0.0

echo "Product service pushed"