#!/bin/bash
set -e
#run scripts to build images

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "script dir = $SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
echo "Project root = $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# Pre requistes check
echo "Verifying pre-requisites"

# Verifying if Microk8s is running
if ! microk8s status 2>/dev/null | grep -q "microk8s is running"; then
  echo "ERROR: MicroK8s not running, automatic start"
  microk8s start
  echo "Waiting for MicroK8s to start"
  sleep 60
fi
echo "Microk8s is running"

# Verify and activate addons 
for addon in registry dns ingress metrics-server hostpath-storage; do
    if microk8s status | grep -q "$addon: disabled"; then
    echo "Activating addon: $addon"
    microk8s enable $addon
    sleep 5
  else
    echo "Addon $addon: OK"
  fi
done

# Verify if registry is active

echo "Verifying registry..."
REGISTRY_OK=false
for i in $(seq 1 24); do
  if curl -s http://localhost:32000/v2/ > /dev/null 2>&1; then
    echo "Registry accessible: OK"
    REGISTRY_OK=true
    break
  fi
  echo "Waiting for registry($i/24)"
  sleep 5
done

# Se ainda não responde, tenta activar e aguarda mais
if [ "$REGISTRY_OK" = false ]; then
  echo "Registry not responding. Activating addon..."
  microk8s enable registry
  sleep 30
  if curl -s http://localhost:32000/v2/ > /dev/null 2>&1; then
    echo "Registry accessible after enable: OK"
  else
    echo "ERROR: Registry not accessible after 150s"
    exit 1
  fi
fi

# BUILD AND PUSH IMAGES
cp requirements/production_requirements.txt user-service/requirements.txt
cp requirements/production_requirements.txt product-service/requirements.txt

echo "building user-service"
"$PROJECT_ROOT/k8s/services/user-service/00-build-push.sh"

if [ $? -ne 0 ]; then
    echo "fail to build user-service"
    exit 1
fi

echo "building product-service"
"$PROJECT_ROOT/k8s/services/product-service/00-product-build-push.sh"

if [ $? -ne 0 ]; then
    echo "fail to build product-service"
    exit 1
fi

echo "build completed"