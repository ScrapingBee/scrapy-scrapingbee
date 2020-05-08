import copy

from scrapy import Request

from .request import ScrapingBeeRequest


class ScrapingBeeAPIKeyNotConfigured(Exception):
    """Forgot to set SCRAPINGBEE_API_KEY in settings.py"""


class ScrapingBeeMiddleware:
    scrapingbee_api_url = 'https://app.scrapingbee.com/api/v1/'

    def __init__(self, api_key):
        self.api_key = api_key

    @classmethod
    def from_crawler(cls, crawler):
        api_key = crawler.settings.get('SCRAPINGBEE_API_KEY')
        if not api_key:
            raise ScrapingBeeAPIKeyNotConfigured

        return cls(api_key=api_key)

    def _get_scrapingbee_url(self, params):
        qs_params = {
            'api_key': self.api_key,
        }
        qs_params.update(params)
        
        qs = '&'.join(f'{k}={v}' for k, v in qs_params.items())
        return f'{self.scrapingbee_api_url}?{qs}'

    def process_request(self, request, spider):
        if not isinstance(request, ScrapingBeeRequest):
            return

        scrapingbee_url = self._get_scrapingbee_url(
            request.meta['scrapingbee']['params'])

        # NOTE: Scrapy logs request with API KEY unmasked
        new_request = request.replace(
            cls=Request, url=scrapingbee_url, meta=request.meta)

        return new_request

    def process_response(self, request, response, spider):
        if not 'scrapingbee' in request.meta:
            return response

        # Modify response url to real url
        response = response.replace(
            url=request.meta['scrapingbee']['real_url'])

        return response
