## Scrapy ScrapingBee Middleware (Alpha Version)

Integrate Scrapy with ScrapingBee API  to handle headless browsers and proxy rotation. Requires to create an account on [scrapingbee.com](https://scrapingbee.com).

### Installation

Locally, clone the project. Create a virtual environment, install the requirements and install the alpha version in editable mode with:

```
pip install -e .
```

### Configuration

In your Scrapy project, add your SCRAPINGBEE_API_KEY in settings.py and add the ScrapingBeeMiddleware to DOWNLOADER_MIDDLEWARES.

```
SCRAPINGBEE_API_KEY = 'REPLACE-WITH-YOUR-API-KEY'

DOWNLOADER_MIDDLEWARES = {
    'scrapy_scrapingbee.ScrapingBeeMiddleware': 725,
}
```

### Example spider

You can go to `examples/homepage` and run the example spider with:

```
scrapy crawl homepage
```

In `examples/homepage/spiders/homepage.py` you can yield a ScrapingBeeRequest and modify the default options with the `params` argument:

```
yield ScrapingBeeRequest(url, params={
    #'block_ads': True,
    #'block_resources': True,
    #'cookies': '',
    #'forward_headers': False,
    #'js_snippet': '',
    #'premium_proxy': False,
    #'render_js': True,
    #'return_page_source': False,
    #'wait': 0,
})
```
