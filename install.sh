# Immediately exit if any command has a non-zero exit status.
set -e

# Make conda available to shell script
eval "$(conda shell.bash hook)"

echo 'Creating/Overwriting `cookie-classify` conda environment.'
conda create --name cookie-classify --file requirements.txt

echo 'Activating environment.'
conda activate cookie-classify

echo 'Installing required packages via pip.'
$CONDA_PREFIX/bin/pip install selenium-wire

echo 'Creating directory structure.'
mkdir screenshots

echo 'Install finished successfully.'