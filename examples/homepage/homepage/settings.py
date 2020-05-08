# -*- coding: utf-8 -*-
BOT_NAME = 'homepage'

SPIDER_MODULES = ['homepage.spiders']
NEWSPIDER_MODULE = 'homepage.spiders'

# NOTE: Add your own API key from ScrapingBee
SCRAPINGBEE_API_KEY = ''

DOWNLOADER_MIDDLEWARES = {
    'scrapy_scrapingbee.ScrapingBeeMiddleware': 725,
}
