import logging
import re
import warnings

import scrapy
from scrapy.exceptions import ScrapyDeprecationWarning


class HideApiKeyFormatter(logging.Formatter):
    """Deprecated: the API key is no longer in URLs, so there is nothing to
    hide."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            'HideApiKeyFormatter is deprecated and will be removed in a '
            'future release.', ScrapyDeprecationWarning, stacklevel=2)
        super().__init__(*args, **kwargs)

    def format(self, record):
        formatted = super().format(record)
        return re.sub(r'api_key=[^&]*', 'api_key=HIDDEN', formatted)


class ScrapingBeeSpider(scrapy.Spider):
    """Deprecated: inherit from scrapy.Spider instead.

    It used to hide the API key in logs; the key is no longer in URLs.
    fmt and datefmt are still accepted (and ignored) so old subclasses work.
    """

    def __init__(self, fmt=None, datefmt=None, *args, **kwargs):
        message = (
            f'{type(self).__name__} inherits from ScrapingBeeSpider, which is '
            'deprecated and will be removed in a future release; inherit '
            'from scrapy.Spider instead')
        cls, base = type(self), ScrapingBeeSpider
        if (cls.start is base.start
                and cls.start_requests is not base.start_requests):
            message += ' and rename start_requests() to async def start()'
        warnings.warn(f'{message}.', ScrapyDeprecationWarning, stacklevel=2)
        super().__init__(*args, **kwargs)

    if not hasattr(scrapy.Spider, 'start_requests'):
        def start_requests(self):
            # Scrapy 2.16 removed it; this keeps super().start_requests()
            # working in subclasses.
            for url in self.start_urls:
                yield scrapy.Request(url, dont_filter=True)

    async def start(self):
        # Scrapy 2.16+ no longer calls start_requests(), which 0.0.x
        # subclasses were documented to define; keep calling it for them.
        if type(self).start_requests is not ScrapingBeeSpider.start_requests:
            for request in self.start_requests():
                yield request
        else:
            async for request in super().start():
                yield request

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        return super().from_crawler(
            crawler, crawler.settings.get('LOG_FORMAT'),
            crawler.settings.get('LOG_DATEFORMAT'), *args, **kwargs)
