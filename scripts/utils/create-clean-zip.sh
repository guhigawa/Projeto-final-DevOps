#!/bin/bash
# create clean zip file

cd ~/Downloads/DevOps/
DATA=$(date +%Y%m%d)
ARCHIVE_NAME="Inventory_${DATA}.zip"

zip -r "${ARCHIVE_NAME}" Inventory \
     -x "*.git/*" \
    -x "*.venv*" \
    -x "*__pycache__*" \
    -x "*.pytest_cache*" \
    -x "*.pyc" \
    -x "*.log" \
    -x "*.pid" \
    -x "*.sonar*" \
    -x "actions-runner/*" \
    -x "Inventory/actions-runner/*" \
    -x "Inventory/user-service/tests/evidence/*" \
    -x "Inventory/product-service/products_tests/products_evidence/*" \
    -x "generate_hashed_password.py" \
    -x "requirements.txt.backup" \
    -x ".vscode/*" \
    -x "**/.coverage" \
    -x "**/htmlcov/*" \
    -x "*.db" \
    -x "*.sqlite" \
    -x "*.tmp" \
    -x "**/migrations/*.pyc" \
    -x "**/migrations/__pycache__/*" \
    -x "Inventory/generate_hashed_password.py" \
    -x "Inventory/k8s/02-secrets-producao.yml"

