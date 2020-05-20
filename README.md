## Scrapy ScrapingBee Middleware

[![build](https://github.com/scrapingbee/scrapy-scrapingbee/workflows/build/badge.svg)](https://github.com/scrapingbee/scrapy-scrapingbee/actions)
[![version](https://img.shields.io/pypi/v/scrapy-scrapingbee.svg)](https://pypi.org/project/scrapy-scrapingbee/)
[![python](https://img.shields.io/pypi/pyversions/scrapy-scrapingbee.svg)](https://pypi.org/project/scrapy-scrapingbee/)

Integrate Scrapy with ScrapingBee API to use headless browsers for JavaScript and proxy rotation. Requires to create an account on [scrapingbee.com](https://scrapingbee.com) to get an API key.

### Installation

`pip install scrapy-scrapingbee`

### Configuration

Add your `SCRAPINGBEE_API_KEY` and the `ScrapingBeeMiddleware` to your project settings.py. Don't forget to set `CONCURRENT_REQUESTS` according to your [ScrapingBee plan](https://www.scrapingbee.com/#pricing).

```python
SCRAPINGBEE_API_KEY = 'REPLACE-WITH-YOUR-API-KEY'

DOWNLOADER_MIDDLEWARES = {
    'scrapy_scrapingbee.ScrapingBeeMiddleware': 725,
}

CONCURRENT_REQUESTS = 1
```

### Usage

Inherit your spiders from `ScrapingBeeSpider` and yield a `ScrapingBeeRequest`.

ScrapingBeeSpider overrides the default logger to hide your API key in the Scrapy logs.

Below you can see an example from the spider in [httpbin.py](examples/httpbin/httpbin/spiders/httpbin.py).

```python
from scrapy_scrapingbee import ScrapingBeeSpider, ScrapingBeeRequest

JS_SNIPPET = 'window.scrollTo(0, document.body.scrollHeight);'


class HttpbinSpider(ScrapingBeeSpider):
    name = 'httpbin'
    start_urls = [
        'https://httpbin.org',
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield ScrapingBeeRequest(url, params={
                # 'render_js': False,
                # 'block_ads': True,
                # 'block_resources': False,
                # 'js_snippet': JS_SNIPPET,
                # 'premium_proxy': True,
                # 'country_code': 'fr',
                # 'return_page_source': True,
                # 'wait': 3000,
                # 'wait_for': '#swagger-ui',
            },
            headers={
                # 'Accept-Language': 'En-US',
            },
            cookies={
                # 'name_1': 'value_1',
            })

    def parse(self, response):
        ...
```

You can pass [ScrapingBee parameters](https://www.scrapingbee.com/documentation/) in the params argument of a ScrapingBeeRequest. Headers and cookies are passed like a normal Scrapy Request. ScrapingBeeRequest formats all parameters, headers and cookies to the format expected by the ScrapingBee API.

### Examples

Add your API key to [settings.py](examples/httpbin/httpbin/settings.py).

To run the examples you need to clone this repository. In your terminal, go to `examples/httpbin/httpbin` and run the example spider with:

```bash
scrapy crawl httpbin
```
