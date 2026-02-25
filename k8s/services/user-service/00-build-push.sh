# k8s/services/user-service/00-build-push.sh
#!/bin/bash

echo "Building and pushing User service image"

cd ~/Downloads/Projeto_final/user-service

docker build -t user-service:1.0.0 \
    --build-arg ENVIRONMENT=production \
    --build-arg PORT=5001 \
    .

docker tag user-service:1.0.0 localhost:32000/user-service:1.0.0 #local registry for microk8s in port 32000, instead of sending it to the docker hub

microk8s enable registry #Once enabled stays on until the reboot of the machine or use the disable command

docker push localhost:32000/user-service:1.0.0 

echo "User service image pushed"