import base64
import copy
import logging

from scrapy import Request
from scrapy.spidermiddlewares.httperror import HttpError

logger = logging.getLogger(__name__)


class ScrapingBeeRequest(Request):

    def __init__(self, url, params={}, headers=None, body=None,
                 cookies=None, meta=None, **kwargs):
        meta = copy.deepcopy(meta) or {}

        if headers:
            params['forward_headers'] = True
            headers = self.process_headers(headers)

        scrapingbee_params = self.process_scrapingbee_params({
            **{'url': url},
            **{'cookies': cookies},
            **params
        })
        meta['scrapingbee'] = {
            'params': scrapingbee_params
        }

        super().__init__(
            url,
            headers=headers,
            body=body,
            meta=meta,
            errback=self.handle_error,
            **kwargs
        )

    @staticmethod
    def process_js_snippet(s):
        return base64.b64encode(s.encode()).decode()

    @staticmethod
    def process_headers(d, prefix='Spb-'):
        return {f'{prefix}{k}': v for k, v in d.items()}

    @staticmethod
    def process_cookies(d):
        if isinstance(d, dict):
            return ';'.join(f'{k}={v}' for k, v in d.items())
        elif isinstance(d, list):
            # ScrapingBee only supports name=value cookies ATM
            raise NotImplementedError
        elif isinstance(d, str):
            return d

    @classmethod
    def process_scrapingbee_params(cls, params):
        new_params = {}
        for k, v in params.items():
            if v in (None, '', [], {}):
                continue
            elif k == 'js_snippet':
                new_params[k] = cls.process_js_snippet(v)
            elif k == 'cookies':
                new_params[k] = cls.process_cookies(v)
            else:
                new_params[k] = v
        return new_params

    def handle_error(self, error):
        if error.check(HttpError):
            logger.error(
                f'Got ScrapingBee error: {error.value.response.text}')
        else:
            logger.error(repr(error))
