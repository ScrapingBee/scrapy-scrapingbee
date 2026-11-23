import logging
from urllib.parse import urlencode

from scrapy import signals
from scrapy.exceptions import IgnoreRequest

from .request import (ScrapingBeeApiRequest, ScrapingBeeRequest,
                      log_scrapingbee_error)

logger = logging.getLogger(__name__)


class ScrapingBeeMiddleware:
    scrapingbee_api_url = 'https://app.scrapingbee.com/api/v1/'
    _warned_authorization = False
    _warned_missing_key = False
    _signals_connected = False

    def __init__(self, api_key):
        self.api_key = api_key

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(api_key=crawler.settings.get('SCRAPINGBEE_API_KEY'))
        # The key is on an API request only while it is in the downloader, so
        # redirects, caches, disk queues and spider code never get it.
        crawler.signals.connect(
            middleware._add_key, signal=signals.request_reached_downloader)
        crawler.signals.connect(
            middleware._clean, signal=signals.request_left_downloader)
        middleware._signals_connected = True
        return middleware

    def _get_scrapingbee_url(self, params):
        # The API documents lowercase booleans (render_js=false).
        params = {k: str(v).lower() if isinstance(v, bool) else v
                  for k, v in params.items()}
        return f'{self.scrapingbee_api_url}?{urlencode(params)}'

    @staticmethod
    def _replace_response_url(response):
        resolved_url = response.headers.get(
            'Spb-Resolved-Url', def_val=response.url)
        return response.replace(
            url=resolved_url.decode(response.headers.encoding))

    @staticmethod
    def _is_api_call(request):
        return (isinstance(request, ScrapingBeeApiRequest)
                and request.is_api_call)

    def _add_key(self, request):
        if self._is_api_call(request):
            params = request.meta.get('scrapingbee', {}).get('params', {})
            api_key = params.get('api_key') or self.api_key
            request.headers['Authorization'] = f'Bearer {api_key}'

    def _clean(self, request):
        if self._is_api_call(request):
            request.headers.pop('Authorization', None)
            # Only needed on the way to the downloader, and it must not
            # reach requests built with meta=response.meta.
            request.meta.pop('allow_offsite', None)

    def _require_key(self, request):
        # Without a key, drop the request rather than fetch it directly.
        params = request.meta.get('scrapingbee', {}).get('params', {})
        if params.get('api_key') or self.api_key:
            return
        if not self._warned_missing_key:
            self._warned_missing_key = True
            logger.error(
                'SCRAPINGBEE_API_KEY is not set, so ScrapingBee requests are '
                'dropped. Set it in your settings, or pass api_key in params.')
        raise IgnoreRequest('SCRAPINGBEE_API_KEY is not set')

    # Optional `spider`: Scrapy 2.13 passes it, 2.14+ warns if it's required.
    def process_request(self, request, spider=None):
        if self._is_api_call(request):
            # A request saved in JOBDIR can be resumed without a key.
            self._require_key(request)
            if not self._signals_connected:
                # A subclass whose from_crawler() doesn't call this class's.
                self._add_key(request)
            return
        if not isinstance(request, ScrapingBeeRequest):
            return
        self._require_key(request)

        params = dict(request.meta['scrapingbee']['params'])
        # A per-request api_key goes in the header too, never in the URL.
        params.pop('api_key', None)
        scrapingbee_url = self._get_scrapingbee_url(params)

        headers = request.headers.copy()
        if 'Authorization' in headers:
            del headers['Authorization']
            if not self._warned_authorization:
                self._warned_authorization = True
                logger.warning(
                    'ScrapingBeeMiddleware replaces the Authorization header '
                    'with your ScrapingBee API key. To send credentials to '
                    'the target site, pass them in '
                    'ScrapingBeeRequest(headers=...).')

        errback = request.errback
        default = ScrapingBeeRequest.handle_error
        if getattr(errback, '__func__', None) is default:
            # JOBDIR can't serialize a method of the request; see to_dict().
            errback = log_scrapingbee_error

        # allow_offsite: allowed_domains doesn't list the API host, and the
        # original request already passed the offsite check.
        new_request = request.replace(
            cls=ScrapingBeeApiRequest, url=scrapingbee_url, headers=headers,
            meta={**request.meta, 'allow_offsite': True}, errback=errback,
            is_api_call=True)

        return new_request

    def process_response(self, request, response, spider=None):
        if not self._is_api_call(request):
            return response

        # A response from the HTTP cache never reached the downloader.
        self._clean(request)
        if 'Spb-Resolved-Url' not in response.headers:
            # API errors don't have it; the API URL would be no use.
            params = request.meta.get('scrapingbee', {}).get('params', {})
            return response.replace(url=params.get('url', response.url))

        new_response = self._replace_response_url(response)

        return new_response
