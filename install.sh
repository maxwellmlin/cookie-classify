#!/bin/bash

set -euo pipefail

echo 'Initializing conda.'
eval "$(conda shell.bash hook)"

echo 'Creating `cookie-classify` conda environment.'
conda env create -f environment.yml

echo 'Creating directory structure.'
mkdir -p crawls

echo 'Install finished successfully.'
echo 'Run `conda activate cookie-classify` to activate environment.'