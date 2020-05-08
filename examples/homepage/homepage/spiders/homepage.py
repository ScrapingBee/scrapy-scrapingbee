# -*- coding: utf-8 -*-
import scrapy

from scrapy_scrapingbee import ScrapingBeeRequest

from homepage.items import HomepageItem


class HomepageSpider(scrapy.Spider):
    name = 'homepage'
    allowed_domains = ['scrapingbee.com']
    start_urls = [
        'https://scrapingbee.com',
    ]

    def start_requests(self):
        for url in self.start_urls:
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

    def parse(self, response):
        return HomepageItem(
            url=response.url,
            h1=response.xpath('//h1//text()').extract()
        )
