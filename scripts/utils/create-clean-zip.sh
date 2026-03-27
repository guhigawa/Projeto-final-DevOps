#!/bin/bash
# create clean zip file

cd ~/Downloads/ 
DATA=$(date +%Y%m%d)
ARCHIVE_NAME="Projeto_final_${DATA}.tar.gz"

tar --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -czvf ${ARCHIVE_NAME} Projeto_final/


