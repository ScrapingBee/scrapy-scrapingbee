## Scrapy ScrapingBee Middleware

Integrate Scrapy with ScrapingBee API to handle headless browsers and proxy rotation. Requires to create an account on [scrapingbee.com](https://scrapingbee.com) to get an API key.

### Installation

TODO: replace with instructions to install from PyPi

Locally, clone the project. Create a virtual environment, install the requirements and install the alpha version in editable mode with:

```
pip install -e .
```

### Configuration

In your Scrapy project settings.py add your `SCRAPINGBEE_API_KEY` and the `ScrapingBeeMiddleware` to `DOWNLOADER_MIDDLEWARES`.
Don't forget to set CONCURRENT_REQUESTS according to your [ScrapingBee plan](https://www.scrapingbee.com/#pricing).

```
SCRAPINGBEE_API_KEY = 'REPLACE-WITH-YOUR-API-KEY'

DOWNLOADER_MIDDLEWARES = {
    'scrapy_scrapingbee.ScrapingBeeMiddleware': 725,
}

CONCURRENT_REQUESTS = 1
```

### Usage

You can inherit your spiders from `ScrapingBeeSpider` and yield a `ScrapingBeeRequest`.

`ScrapingBeeSpider` overrides the default logger to hide your API_KEY in the Scrapy logs.

Below you can see an example from the spider in [httpbin.py](examples/httpbin/spiders/httpbin.py).

```
from scrapy_scrapingbee import ScrapingBeeSpider, ScrapingBeeRequest


class HttpbinSpider(ScrapingBeeSpider):
    name = 'httpbin'
    start_urls = [
        'https://httpbin.org',
        'https://httpbin.org/anything',
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield ScrapingBeeRequest(url, params={
                #'render_js': False,
                #'block_ads': True,
                #'block_resources': False,
                #'js_snippet': 'window.scrollTo(0, document.body.scrollHeight);',
                #'premium_proxy': True,
                #'country_code': 'fr',
                #'return_page_source': True,
                #'wait': 3000,
                #'wait_for': '#swagger-ui',
            },
            headers={
                #'Accept-Language': 'En-US',
            },
            cookies={
                #'name_1': 'value_1',
            })

    def parse(self, response):
        ...
```

You can pass [documented ScrapingBee parameters](https://www.scrapingbee.com/documentation/) in the `params` argument of `ScrapingBeeRequest`. Cookies and headers have reserved arguments like normal Scrapy requests. `ScrapingBeeRequest` takes care of formatting all parameters, headers and cookies so that you can pass normal types.

TODO: handle POST requests

## Examples

Add your API key to [settings.py](examples/httpbin/httpbin/settings.py).

Go to `examples/httpbin/httpbin` and run the example spider with:

```
scrapy crawl httpbin
```
