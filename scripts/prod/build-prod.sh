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
  echo "ERRO: MicroK8s não está a correr."
  echo "Execute: microk8s start"
  exit 1
fi
echo "Microk8s is running"

# Verify and activate addons 
for addon in registry dns ingress metrics-server; do
    if microk8s status | grep -q "$addon: disabled"; then
    echo "Activando addon: $addon"
    microk8s enable $addon
    sleep 5
  else
    echo "Addon $addon: OK"
  fi
done

# Verify if registry is active

echo "Verificando registry..."
for i in $(seq 1 12); do
  if curl -s http://localhost:32000/v2/ > /dev/null 2>&1; then
    echo "Registry acessível: OK"
    break
  fi
  echo "Aguardando registry($i/12)"
  sleep 5
  if [ "$i" -eq 12 ]; then
    echo "ERRO: Registry não está acessível após 60s"
    echo "Execute: microk8s enable registry"
    exit 1
  fi
done
echo "Pré-requisitos OK"

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