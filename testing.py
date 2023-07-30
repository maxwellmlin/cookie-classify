from crawler import Crawler, InteractionType

crawler = Crawler(".")
crawler.crawl("https://rackspace.com", 0, InteractionType.NO_ACTION)


