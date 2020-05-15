# -*- coding: utf-8 -*-
import scrapy


class HttpbinItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    body = scrapy.Field()
    headers = scrapy.Field()
