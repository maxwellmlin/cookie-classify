#!/bin/bash

set -euo pipefail

echo 'Initializing conda.'
eval "$(conda shell.bash hook)"

echo 'Removing `cookie-classify` conda environment.'
conda remove --name cookie-classify --all

echo 'Uninstall finished successfully.'