# cookie-classify
Classify cookies based on their function.

## Setup
Tested on Ubuntu 20.04. Requires [miniconda](https://docs.conda.io/en/latest/miniconda.html).

To create the `cookie-classify` conda environment, run:
```bash
./install.sh
```

Activate the environment with:
```bash
conda activate cookie-classify
```

## Usage
To crawl the list of sites in `./inputs/sites/sites.txt`, run:
```bash
python3 main.py
```

View logs and screenshots in the `./crawls` folder.