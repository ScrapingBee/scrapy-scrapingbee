## Scrapy ScrapingBee Middleware

[![build](https://github.com/scrapingbee/scrapy-scrapingbee/workflows/build/badge.svg)](https://github.com/scrapingbee/scrapy-scrapingbee/actions)
[![version](https://img.shields.io/pypi/v/scrapy-scrapingbee.svg)](https://pypi.org/project/scrapy-scrapingbee/)
[![python](https://img.shields.io/pypi/pyversions/scrapy-scrapingbee.svg)](https://pypi.org/project/scrapy-scrapingbee/)

Integrate Scrapy with ScrapingBee API to use headless browsers for JavaScript and proxy rotation. Requires to create an account on [scrapingbee.com](https://scrapingbee.com) to get an API key.

### Installation

`pip install scrapy-scrapingbee`

Requires Python 3.9+ and Scrapy 2.13 or newer. Upgrading from 0.0.x? Read the [changelog](https://github.com/scrapingbee/scrapy-scrapingbee/blob/master/CHANGELOG.md) first: 0.1.0 has breaking changes.

### Configuration

Add your `SCRAPINGBEE_API_KEY` and the `ScrapingBeeMiddleware` to your project settings.py. Don't forget to set `CONCURRENT_REQUESTS` according to your [ScrapingBee plan](https://www.scrapingbee.com/#pricing). Every request goes to the ScrapingBee API host, so `CONCURRENT_REQUESTS_PER_DOMAIN` limits concurrency too: it is 8 by default, and a `scrapy startproject` project sets it to 1 with `DOWNLOAD_DELAY = 1`.

```python
SCRAPINGBEE_API_KEY = 'REPLACE-WITH-YOUR-API-KEY'

DOWNLOADER_MIDDLEWARES = {
    'scrapy_scrapingbee.ScrapingBeeMiddleware': 725,
}

CONCURRENT_REQUESTS = 1
```

### Usage

Yield a `ScrapingBeeRequest` from any Scrapy spider. `ScrapingBeeSpider` is deprecated: existing subclasses still work but log a warning, so switch them to `scrapy.Spider` (and rename `start_requests()` to `async def start()`, since Scrapy 2.16+ no longer calls `start_requests()`).

Your API key is sent in the `Authorization: Bearer` header, never in the request URL, so Scrapy's request log lines don't contain it. The header is on the request only while it is being downloaded, so it isn't on `response.request`, in the job directory (`JOBDIR`) or in the HTTP cache (`HTTPCACHE_DIR`). Two exceptions: a per-request `api_key` passed in `params` stays in `request.meta`, and the API's error message for a rejected key repeats that key, which the default errback logs.

The middleware replaces any `Authorization` header (e.g. from `HttpAuthMiddleware`) with your API key. To authenticate to the target site, pass `ScrapingBeeRequest(headers={'Authorization': ...})` instead. This also applies to credentials in the target URL (`https://user:pass@host/`), which Scrapy 2.20+ turns into an `Authorization` header.

Below you can see an example from the spider in [httpbin.py](https://github.com/scrapingbee/scrapy-scrapingbee/blob/master/examples/httpbin/httpbin/spiders/httpbin.py).

```python
import scrapy
from scrapy_scrapingbee import ScrapingBeeRequest

JS_SNIPPET = 'window.scrollTo(0, document.body.scrollHeight);'


class HttpbinSpider(scrapy.Spider):
    name = 'httpbin'
    start_urls = [
        'https://httpbin.org',
    ]

    async def start(self):
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

You can pass [ScrapingBee parameters](https://www.scrapingbee.com/documentation/) in the params argument of a ScrapingBeeRequest. Headers and cookies are passed like a normal Scrapy Request. ScrapingBeeRequest formats all parameters, headers and cookies to the format expected by the ScrapingBee API: dict and list values such as `extract_rules` or `js_scenario` are sent as JSON, and every value is URL-encoded for you, so pass raw values.

Scrapy's duplicate filter compares the target URL only, not the ScrapingBee parameters. To fetch the same URL more than once with different parameters (for example several `country_code` values), pass `dont_filter=True`.

With `ROBOTSTXT_OBEY = True` (the `scrapy startproject` default), Scrapy fetches each target site's `robots.txt` directly from your machine, not through ScrapingBee. Set `ROBOTSTXT_OBEY = False`, or `meta={'dont_obey_robotstxt': True}` on a request, if you don't want that.

Requests that Scrapy creates itself from a ScrapingBee response (a meta refresh redirect), and plain requests such as `response.follow()`, are also fetched directly, not through ScrapingBee. Yield a `ScrapingBeeRequest` for follow-up pages, and set `METAREFRESH_ENABLED = False` to stop Scrapy following meta refresh tags.

### Examples

Add your API key to [settings.py](https://github.com/scrapingbee/scrapy-scrapingbee/blob/master/examples/httpbin/httpbin/settings.py).

To run the examples you need to clone this repository. In your terminal, go to `examples/httpbin/httpbin` and run the example spider with:

```bash
scrapy crawl httpbin
```
