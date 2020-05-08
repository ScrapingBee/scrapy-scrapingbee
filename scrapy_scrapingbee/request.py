import base64
import copy
import urllib

from scrapy import Request


class ScrapingBeeRequest(Request):
    
    def __init__(self, url, params={}, meta=None, **kwargs):
        meta = copy.deepcopy(meta) or {}

        scrapingbee_params = self.get_scrapingbee_params({
            **{'url': url},
            **params
        })
        meta['scrapingbee'] = {
            'real_url': url,
            'params': scrapingbee_params,
        }

        super().__init__(url, meta=meta, **kwargs)

    @staticmethod
    def process_url(value):
        return urllib.parse.quote(value)

    @staticmethod
    def process_js_snippet(value):
        return base64.b64encode(value.encode()).decode()

    @classmethod
    def get_scrapingbee_params(cls, params):
        new_params = {}
        for k, v in params.items():
            if k == 'url':
                new_params[k] = cls.process_url(v)
            elif k == 'js_snippet':
                new_params[k] = cls.process_js_snippet(v)
            else:
                new_params[k] = v
        return new_params
