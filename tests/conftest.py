from scrapy.utils.reactor import install_reactor

# Scrapy 2.13 and 2.14 need a reactor installed before get_crawler() is used.
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')
