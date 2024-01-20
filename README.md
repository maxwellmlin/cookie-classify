# cookie-classify
This repository contains both web crawling and analysis code for the project "HTTP Cookie Classification".

Read our initial paper [here](https://maxwellmlin.com/assets/pdf/cookie-2023.pdf).

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
Modify crawl parameters in `config.py` and crawl behavior in the `worker` function of `main.py`.

To start a crawl, execute:
```bash
python3 main.py
```

Crawl data is saved in the `crawls` folder. To analyze, use the appropriate Jupyter Notebook.

## Architecture
### Crawler
Our crawler uses Selenium to drive a headless Firefox instance.

The entry point of the crawler is `main.py` which feeds a list of websites to an instance of `Crawler`, defined in `crawler.py`. Our `Crawler` has two primary algorithms.

#### Website Compliance Algorithm
The function `compliance_algo` in `crawler.py` collects data that is used to classify whether a given website is compliant or non-compliant with privacy laws. Specifically, a website is non-compliant if it continues to use tracking cookies after a user explicitly denies their usage. This is a lower bound on the number of non-compliant websites since websites may be in violation with web privacy laws in other ways. However, tracking cookies arguably pose the most serious privacy threat as they collect user data to transmit to third parties for commercial purposes.

For websites that use the OneTrust CMP, we enable all cookies except for tracking cookies by modifying the `OptanonConsent` cookie. For all other websites, we use a modified version of [BannerClick](https://github.com/maxwellmlin/bannerclick) to click the "Reject All" button. In either case, if any tracking cookies are still present after the reject, we classify the website as non-compliant.

To increase robustness, this algorithm can crawl websites up to a given maximum depth. For a website at depth=$d$, we record all links present as the new frontier nodes of depth=$d+1$. This process occurs recursively until the specified max depth is reached.

#### Cookie Classification Algorithm
The function `classification_algo` in `crawler.py` collects data that is used to determines whether a website requires necessary cookies. Specifically, we assume necessary cookies must have some visible impact on the website.

This algorithm generates and traverse clickstreams across different experimental conditions (i.e., with different subsets of cookies
enabled). After each action in a clickstream, data is collected (e.g., screenshots, website text, URLs of images, hyperlinks). 

If we observe a significant difference between data collected in a run with all cookies enabled vs. all cookie disabled, we conclude that that website requires the use of cookies. There is one important caveat: the content of some websites change naturally (e.g., social media, news websites). To take this into account, we crawl each website twice without applying an experimental condition. If these two crawls are similar, however, the experimental crawl is significantly different, then we can conclude that our experimental condition likely caused the change in website behavior.

##### Comparison Algorithms
- Screenshots
  - Difference in Difference
  - Chunk by Chunk
- URLs