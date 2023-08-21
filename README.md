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

---

To uninstall, run:
```bash
./uninstall.sh
```

## Usage

To crawl the list of sites in `inputs/sites/sites.txt`, run:

```bash
python3 main.py
```

Logs and screenshots are saved in the `crawls` folder. To analyze, use the `wip_tracker_analysis.ipynb` Jupyter Notebook.
