import logging

from scrapy import Request
from scrapy.exceptions import NotConfigured

from .request import ScrapingBeeRequest

logger = logging.getLogger(__name__)


class ScrapingBeeMiddleware:
    scrapingbee_api_url = 'https://app.scrapingbee.com/api/v1/'

    def __init__(self, api_key):
        self.api_key = api_key

    @classmethod
    def from_crawler(cls, crawler):
        api_key = crawler.settings.get('SCRAPINGBEE_API_KEY')
        if not api_key:
            raise NotConfigured

        return cls(api_key=api_key)

    def _get_scrapingbee_url(self, params):
        qs_params = {
            'api_key': self.api_key,
        }
        qs_params.update(params)

        qs = '&'.join(f'{k}={v}' for k, v in qs_params.items())
        return f'{self.scrapingbee_api_url}?{qs}'

    @staticmethod
    def _replace_response_url(response):
        resolved_url = response.headers.get(
            'Spb-Resolved-Url', def_val=response.url)
        return response.replace(
            url=resolved_url.decode(response.headers.encoding))

    def process_request(self, request, spider):
        if not isinstance(request, ScrapingBeeRequest):
            return

        scrapingbee_url = self._get_scrapingbee_url(
            request.meta['scrapingbee']['params'])

        new_request = request.replace(
            cls=Request, url=scrapingbee_url, meta=request.meta)

        return new_request

    def process_response(self, request, response, spider):
        if 'scrapingbee' not in request.meta:
            return response

        new_response = self._replace_response_url(response)

        return new_response
