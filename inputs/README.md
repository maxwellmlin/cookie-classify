# Inputs
This directory contains data used in crawling or analysis.

- `blocklists`: Known tracking domains obtained from [JustDomains](https://github.com/justdomains/blocklists).
- `databases`
    - `cookie_script.json`: Scraped data from [Cookie-Script](https://cookie-script.com) that classifies cookies as one of the four ICC UK categories or *unclassified* if no database entry is found.
    - `open_cookie_database.csv`: Cookie classification data from the [Open Cookie Database](https://github.com/jkwakman/Open-Cookie-Database). Note that there is a one-to-one mapping between the ICC UK categories and the categories used by the Open Cookie Database.
- `sites`: Domains to be crawled.
    - `detected_banner.txt`: Websites that have a cookie banner.
    - `onetrust.txt`: Websites that use the OneTrust CMP.
- `cdn`: CDN lists.
    - `cnamechain.json`: Obtained from [cdnfinder](https://github.com/turbobytes/cdnfinder/blob/master/assets/cnamechain.json). Maps hostname to CDN name.