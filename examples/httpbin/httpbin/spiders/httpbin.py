# -*- coding: utf-8 -*-
from scrapy_scrapingbee import ScrapingBeeSpider, ScrapingBeeRequest

from httpbin.items import HttpbinItem

JS_SNIPPET = 'window.scrollTo(0, document.body.scrollHeight);'


class HttpbinSpider(ScrapingBeeSpider):
    name = 'httpbin'
    start_urls = [
        'https://httpbin.org',
        'https://httpbin.org/anything',
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
            }, headers={
                # 'Accept-Language': 'En-US',
            }, cookies={
                # 'name_1': 'value_1',
            })

    def parse(self, response):
        body = response.body.decode(response.encoding)
        return HttpbinItem(
            url=response.url,
            status=response.status,
            body=body,
            headers=response.headers,
        )
