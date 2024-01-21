# cookie-classify
This repository contains both web crawling and analysis code for the Duke Independent Study project "Automated HTTP Cookie Classification and Enforcement".

Read our [initial paper](https://maxwellmlin.com/assets/pdf/cookie-2023.pdf).

## Setup
Only Ubuntu 20.04 LTS is officially supported.

To create the `cookie-classify` [conda](https://docs.conda.io/en/latest/miniconda.html) environment, execute:

```bash
conda env create -f environment.yml
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

Crawl data is saved in the `crawls` folder. To analyze, use the appropriate Jupyter Notebook (see [Architecture](#architecture)).

## Architecture
### Crawler
Our crawler uses Selenium to drive a headless Firefox instance.

The entry point `main.py` feeds a list of websites to an instance of `Crawler`, defined in `crawler.py`. Our `Crawler` has two primary algorithms.

#### Website Compliance Algorithm
The function `compliance_algo` in `crawler.py` collects data that is used to classify whether a given website is compliant or non-compliant with privacy laws such as GDPR or CCPA. Specifically, a website is *non-compliant* if it continues to use tracking cookies after a user explicitly denies their usage. This is obviously a lower bound on the number of non-compliant websites since websites may be in violation with web privacy laws in other ways. However, out of the 4 different cookie categories defined by the UK ICC, tracking cookies arguably pose the most serious privacy threat as they collect user data to transmit to third parties for commercial purposes. Therefore, we focus on verifying that websites do not use tracking cookies if the user does not consent to their usage.

For websites that use the OneTrust CMP, we reject tracking cookies (and accept all other types) by modifying the `OptanonConsent` cookie. For all other websites, we use a modified version of [BannerClick](https://github.com/maxwellmlin/bannerclick) to click the reject button. In either case, if any tracking cookies remain after the reject action, we classify the website as non-compliant since they did not respect the user's choice.

To increase robustness, this algorithm can crawl websites up to a given maximum depth. For a website at depth=$d$, we record all links present as the new frontier nodes of depth=$d+1$. This process occurs recursively until the specified max depth is reached.

To analyze the crawl data generated from `compliance_algo`, use the following Jupyter notebooks:
- `tracker_analysis.ipynb`: Compare the number of trackers before/after BannerClick reject action.
- `only_reject_trackers_analysis.ipynb`: Compare the number of trackers before/after OneTrust reject only trackers action.

#### Cookie Classification Algorithm
The function `classification_algo` in `crawler.py` collects data that is used to classify whether a website requires necessary cookies. Specifically, we assume necessary cookies must have some observable effect on the website.

To do so, this algorithm generates and traverse clickstreams across different experimental conditions (i.e., with different subsets of cookies enabled). After each action in a clickstream, data is collected (e.g., screenshots, website text, URLs of images, hyperlinks). 

If we observe a significant difference between data collected when all cookies are enabled versus when all cookies are disabled, we conclude that that website requires the use of cookies. However, there is one important caveat: the content of some websites change naturally upon page refreshes (e.g., social media websites). To take this into account, we crawl each website twice without applying an experimental condition. If these two crawls are similar but the experimental crawl is significantly different, then we can conclude that our experimental condition (likely) caused the observed change in website behavior.

To analyze the crawl data generated from `classification_algo`, use the following Jupyter notebook:
- `clickstream_analysis.ipynb`: Compare the differences between baseline, control, and experimental conditions.
