#!/bin/bash
# create clean zip file

cd ~/Downloads/ 
DATA=$(date +%Y%m%d)
ARCHIVE_NAME="Projeto_final_${DATA}.zip"

zip -r "${ARCHIVE_NAME}" Projeto_final \
     -x "*.git/*" \
    -x "*.venv*" \
    -x "*__pycache__*" \
    -x "*.pytest_cache*" \
    -x "*.pyc" \
    -x "*.log" \
    -x "*.pid" \
    -x "*.sonar*" \
    -x "actions-runner/*" \
    -x "Projeto_final/actions-runner/*" \
    -x "Projeto_final/user-service/tests/evidence/*" \
    -x "Projeto_final/product-service/products_tests/products_evidence/*" \
    -x "Projeto_final/documentation/tests_outputs/*" \
    -x "*.env" \
    -x "*.env.staging" \
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
    -x "Projeto_final/generate_hashed_password.py" 

