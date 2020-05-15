# -*- coding: utf-8 -*-
BOT_NAME = 'httpbin'

SPIDER_MODULES = ['httpbin.spiders']
NEWSPIDER_MODULE = 'httpbin.spiders'

SCRAPINGBEE_API_KEY = 'REPLACE-WITH-YOUR-API-KEY'

DOWNLOADER_MIDDLEWARES = {
    'scrapy_scrapingbee.ScrapingBeeMiddleware': 725,
}

CONCURRENT_REQUESTS = 1
