import logging
import re

import scrapy


class HideApiKeyFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        super(HideApiKeyFormatter, self).__init__(*args, **kwargs)

    def format(self, record):
        formatted = super(HideApiKeyFormatter, self).format(record)
        return re.sub(r'api_key=[^&]*', 'api_key=HIDDEN', formatted)


class ScrapingBeeSpider(scrapy.Spider):

    def __init__(self, fmt, datefmt, *args, **kwargs):
        formatter = HideApiKeyFormatter(fmt=fmt, datefmt=datefmt)
        root = logging.getLogger()
        for h in root.handlers:
            h.setFormatter(formatter)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        log_format = crawler.settings.get('LOG_FORMAT')
        log_dateformat = crawler.settings.get('LOG_DATEFORMAT')
        spider = cls(log_format, log_dateformat, *args, **kwargs)
        spider._set_crawler(crawler)
        return spider
