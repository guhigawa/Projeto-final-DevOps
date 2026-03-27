#!/bin/bash
#run scripts to build images

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "script dir = $SCRIPT_DIR"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
echo "Project root = $PROJECT_ROOT"

cd "$PROJECT_ROOT"
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