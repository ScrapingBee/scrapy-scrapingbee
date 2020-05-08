# -*- coding: utf-8 -*-
import scrapy


class HomepageItem(scrapy.Item):
    url = scrapy.Field()
    h1 = scrapy.Field()
