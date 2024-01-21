# Inputs
This directory contains data used in crawling or analysis.

- `blocklists`: Known tracking domains obtained from [JustDomains](https://github.com/justdomains/blocklists)
- `databases`
    - `cookie_script.json`: Scraped data from [Cookie-Script](https://cookie-script.com) that classifies cookies as one of the four ICC UK categories or *Unclassified* if no database entry is found
    - `open_cookie_database.csv`: Data from the [Open Cookie Database](https://github.com/jkwakman/Open-Cookie-Database). Note that there is a one-to-one mapping between the ICC UK categories and the categories used by the Open Cookie Database. See their README for details.
- `sites`: Domains to be crawled