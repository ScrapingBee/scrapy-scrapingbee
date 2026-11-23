import asyncio
import logging
import warnings

import pytest
from scrapy.exceptions import ScrapyDeprecationWarning
from scrapy.utils.test import get_crawler

from scrapy_scrapingbee import ScrapingBeeRequest, ScrapingBeeSpider
from scrapy_scrapingbee.spider import HideApiKeyFormatter


class PlainSpider(ScrapingBeeSpider):
    name = 'plain'


class OldStyleSpider(ScrapingBeeSpider):
    '''A 0.0.x subclass that took and forwarded fmt/datefmt'''
    name = 'old'

    def __init__(self, fmt, datefmt, *args, **kwargs):
        super().__init__(fmt, datefmt, *args, **kwargs)


@pytest.mark.parametrize('spidercls', [PlainSpider, OldStyleSpider])
def test_spider_still_works_and_warns(spidercls):
    '''Existing subclasses should still be created, with a warning'''
    crawler = get_crawler(spidercls)
    with pytest.warns(ScrapyDeprecationWarning,
                      match=f'{spidercls.__name__} inherits from'):
        spider = spidercls.from_crawler(crawler, foo='bar')
    assert spider.crawler is crawler
    assert spider.foo == 'bar'


class StartRequestsSpider(ScrapingBeeSpider):
    '''The pattern the 0.0.x README documented'''
    name = 'start_requests'

    def start_requests(self):
        yield ScrapingBeeRequest('https://example.com')


class SuperStartRequestsSpider(ScrapingBeeSpider):
    '''start_requests() built on the default one, removed in Scrapy 2.16'''
    name = 'super_start_requests'

    def start_requests(self):
        for request in super().start_requests():
            yield ScrapingBeeRequest(request.url, params={'wait': 1})


@pytest.mark.parametrize('spidercls,expected', [
    (StartRequestsSpider, ['https://example.com']),
    (SuperStartRequestsSpider, ['https://start.com']),
    (PlainSpider, ['https://start.com']),
])
def test_spider_start_calls_start_requests(spidercls, expected):
    '''start() should still use start_requests() on Scrapy 2.16+'''
    with pytest.warns(ScrapyDeprecationWarning):
        spider = spidercls(start_urls=['https://start.com'])

    async def collect():
        with warnings.catch_warnings():
            if spidercls is SuperStartRequestsSpider:
                # Scrapy 2.13-2.15 deprecate calling super().start_requests().
                warnings.simplefilter('ignore', ScrapyDeprecationWarning)
            return [r.meta['scrapingbee']['params']['url']
                    if isinstance(r, ScrapingBeeRequest) else r.url
                    async for r in spider.start()]
    loop = asyncio.new_event_loop()
    try:
        urls = loop.run_until_complete(collect())
    finally:
        loop.close()
    assert [u.rstrip('/') for u in urls] == expected


@pytest.mark.parametrize('spidercls,hint', [
    (PlainSpider, False),
    (StartRequestsSpider, True),
])
def test_spider_warning_mentions_start_requests_if_defined(spidercls, hint):
    '''Only a subclass with start_requests() is told to rename it'''
    with pytest.warns(ScrapyDeprecationWarning,
                      match='inherits from ScrapingBeeSpider') as caught:
        spidercls()
    assert ('rename start_requests()' in str(caught[0].message)) is hint


def test_hide_api_key_formatter_still_works_and_warns():
    '''The old formatter should still redact, with a warning'''
    with pytest.warns(ScrapyDeprecationWarning, match='HideApiKeyFormatter'):
        formatter = HideApiKeyFormatter('%(message)s')
    record = logging.LogRecord(
        'x', logging.INFO, '', 0, 'GET /?api_key=SECRET&url=a', None, None)
    assert formatter.format(record) == 'GET /?api_key=HIDDEN&url=a'


def test_process_url_still_works_and_warns():
    '''The old url helper should still quote, with a warning'''
    with pytest.warns(ScrapyDeprecationWarning, match='process_url'):
        assert ScrapingBeeRequest.process_url('https://a.com?p=1') == \
            'https%3A//a.com%3Fp%3D1'
