import base64
import copy
import json
import logging
import re
import urllib.parse
import warnings

from scrapy import Request
from scrapy.exceptions import ScrapyDeprecationWarning
from scrapy.http import Headers, TextResponse
from scrapy.spidermiddlewares.httperror import HttpError

logger = logging.getLogger(__name__)

# A URL-encoded JSON object or array, e.g. quote(json.dumps(rules)).
ENCODED_JSON = re.compile(r'%[57]B', re.IGNORECASE)
_warned_pre_encoded = set()
# Carries the original arguments through to_dict() (JOBDIR disk queues)
# and replace().
RESTORE_META_KEY = '_scrapingbee_restore'
DEFAULT_ERRBACK_META_KEY = '_scrapingbee_default_errback'


class ScrapingBeeRequest(Request):

    def __init__(self, url, params=None, headers=None, body=None,
                 cookies=None, meta=None, **kwargs):
        meta = copy.deepcopy(meta) or {}
        restore = meta.pop(RESTORE_META_KEY, None)
        target_url = url
        if restore is not None:
            target_url = restore.get('url', url)
            params = restore.get('params', params)
            headers = restore.get('headers', headers)
            cookies = restore.get('cookies', cookies)
        if isinstance(headers, Headers):
            # A plain dict, for process_headers() overrides and disk queues.
            headers = {k.decode(): v for k, v in headers.items()}
        self._init_args = copy.deepcopy({
            'url': target_url, 'params': params, 'headers': headers,
            'cookies': cookies})
        if restore is not None and restore.get('default_errback'):
            kwargs['errback'] = self.handle_error
        params = dict(params or {})

        if headers:
            params['forward_headers'] = True
            headers = self.process_headers(headers)

        scrapingbee_params = self.process_scrapingbee_params({
            **{'url': target_url},
            **{'cookies': cookies},
            **params
        })
        meta['scrapingbee'] = {
            'params': scrapingbee_params
        }
        errback = kwargs.pop("errback", self.handle_error)
        if getattr(errback, '__func__', None) is type(self).handle_error:
            # replace() passes the old request's default errback; rebind it.
            errback = self.handle_error

        super().__init__(
            url,
            headers=headers,
            body=body,
            meta=meta,
            errback=errback,
            **kwargs
        )

    def replace(self, *args, **kwargs):
        # Like to_dict(), hand the original arguments that aren't being
        # replaced over in meta, so copy() and replace() keep params and don't
        # prefix headers twice, also when a subclass sets params itself.
        if issubclass(kwargs.get('cls') or type(self), ScrapingBeeRequest):
            restore = {k: v for k, v in self._init_args.items()
                       if k not in kwargs}
            meta = kwargs.get('meta', self.meta) or {}
            kwargs['meta'] = {**meta, RESTORE_META_KEY: restore}
        return super().replace(*args, **kwargs)

    def to_dict(self, *, spider=None):
        # __init__ prefixes headers and rebuilds params, so serialize the
        # original arguments rather than the processed ones. The default
        # errback is a method of this request, which Scrapy can't serialize
        # by name, so it is dropped here and re-attached in __init__.
        default_errback = self.errback == self.handle_error
        errback, self.errback = self.errback, (
            None if default_errback else self.errback)
        try:
            d = super().to_dict(spider=spider)
        finally:
            self.errback = errback
        d['meta'] = {**d['meta'], RESTORE_META_KEY: {
            **self._init_args, 'default_errback': default_errback}}
        return d

    @staticmethod
    def process_url(s):
        # Deprecated: the middleware now encodes every param itself.
        warnings.warn(
            'ScrapingBeeRequest.process_url is deprecated and will be removed '
            'in a future release.', ScrapyDeprecationWarning, stacklevel=2)
        return urllib.parse.quote(s)

    @staticmethod
    def process_js_snippet(s):
        return base64.b64encode(s.encode()).decode()

    @staticmethod
    def process_headers(d, prefix='Spb-'):
        return {f'{prefix}{k.decode() if isinstance(k, bytes) else k}': v
                for k, v in d.items()}

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
            if v in (None, '', [], (), {}):
                continue
            elif k == 'js_snippet':
                new_params[k] = cls.process_js_snippet(v)
            elif k == 'cookies':
                new_params[k] = cls.process_cookies(v)
            elif isinstance(v, (dict, list, tuple)):
                # extract_rules, js_scenario, ai_extract_rules, ...
                new_params[k] = json.dumps(v)
            else:
                new_params[k] = v
                cls._warn_if_pre_encoded(k, v)
        return new_params

    @staticmethod
    def _warn_if_pre_encoded(key, value):
        # 0.0.x sent most values unencoded, so callers often passed
        # quote(json.dumps(...)); that is now encoded twice. Only encoded
        # JSON is checked: %XX is legitimate in proxies and selectors.
        if (isinstance(value, str) and key not in _warned_pre_encoded
                and ENCODED_JSON.match(value)):
            _warned_pre_encoded.add(key)
            logger.warning(
                f'ScrapingBee param {key!r} looks like URL-encoded JSON. '
                'Since scrapy-scrapingbee 0.1.0 values are encoded for you; '
                'if you encoded it yourself, pass the raw value instead.')

    def handle_error(self, error):
        log_scrapingbee_error(error)


class ScrapingBeeApiRequest(Request):
    """The request ScrapingBeeMiddleware sends to the API."""

    attributes = Request.attributes + ('is_api_call',)

    def __init__(self, *args, is_api_call=False, **kwargs):
        meta = kwargs.get('meta')
        if meta and meta.pop(DEFAULT_ERRBACK_META_KEY, False):
            kwargs['errback'] = log_scrapingbee_error
        super().__init__(*args, **kwargs)
        self.is_api_call = is_api_call

    def replace(self, *args, **kwargs):
        meta = dict(kwargs.get('meta', self.meta) or {})
        if 'url' in kwargs:
            # A redirect, even one back to the same URL, is not the API call
            # the middleware built: no key and no offsite exemption for it.
            kwargs.setdefault('is_api_call', False)
            meta.pop('allow_offsite', None)
        elif self.is_api_call:
            # A copy (a retry) goes to the API host again.
            meta['allow_offsite'] = True
        kwargs['meta'] = meta
        cls = kwargs.get('cls')
        if cls is not None and not issubclass(cls, ScrapingBeeApiRequest):
            # Other request classes don't take is_api_call.
            kwargs['cls'] = lambda *a, is_api_call=None, **kw: cls(*a, **kw)
        return super().replace(*args, **kwargs)

    def to_dict(self, *, spider=None):
        # Scrapy serializes errbacks by spider method name, so the default
        # one is replaced by a flag and re-attached in __init__.
        if self.errback is not log_scrapingbee_error:
            return super().to_dict(spider=spider)
        self.errback = None
        try:
            d = super().to_dict(spider=spider)
        finally:
            self.errback = log_scrapingbee_error
        d['meta'] = {**d['meta'], DEFAULT_ERRBACK_META_KEY: True}
        return d


def log_scrapingbee_error(error):
    if error.check(HttpError):
        response = error.value.response
        if isinstance(response, TextResponse):
            body = response.text
        else:
            body = f'<{len(response.body)} bytes of non-text content>'
        logger.error(f'Got ScrapingBee error: {body}')
    else:
        logger.error(repr(error))
