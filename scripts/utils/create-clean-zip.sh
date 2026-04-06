#!/bin/bash
# create clean zip file

cd ~/Downloads/ 
DATA=$(date +%Y%m%d)
ARCHIVE_NAME="Projeto_final_${DATA}.zip"

zip -r "${ARCHIVE_NAME}" Projeto_final \
    -x "*.git*" \
    -x "*.venv*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x "*.log" \
    -x "*.pid" \
    -x "actions-runner/*" \
    -x "Projeto_final/actions-runner/*" \
    -x "Projeto_final/user-service/tests/evidence/*" \
    -x "Projeto_final/product-service/products_tests/products_evidence/*" \
    -x "Projeto_final/documentation/tests_outputs/*" \
    -x "generate_hashed_password.py" \
    -x "requirements.txt.backup"

