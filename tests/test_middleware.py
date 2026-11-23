import json
from urllib.parse import parse_qs, quote_plus, urlsplit

import pytest
from scrapy import Request, signals
from scrapy.exceptions import IgnoreRequest
from scrapy.http import Response
from scrapy.utils.request import request_from_dict
from scrapy.utils.test import get_crawler

from scrapy_scrapingbee import ScrapingBeeRequest, ScrapingBeeMiddleware
from scrapy_scrapingbee.request import log_scrapingbee_error

DEFAULT_API_URL = ScrapingBeeMiddleware.scrapingbee_api_url
DEFAULT_API_KEY = 'API-KEY'
DEFAULT_URL = 'https://example.com'


def get_spb_url(api_url, url):
    return f'{api_url}?url={quote_plus(url)}'


@pytest.fixture
def crawler():
    return get_crawler(settings_dict={'SCRAPINGBEE_API_KEY': DEFAULT_API_KEY})


@pytest.fixture
def spb_md(crawler):
    return ScrapingBeeMiddleware.from_crawler(crawler)


@pytest.fixture
def spb_req(url=DEFAULT_URL):
    return ScrapingBeeRequest(url)


@pytest.fixture
def spb_res(url=DEFAULT_URL):
    spb_url = get_spb_url(DEFAULT_API_URL, url)
    headers = {'Spb-Resolved-Url': url}
    return Response(spb_url, headers=headers)


@pytest.fixture
def download(crawler, spb_md):
    '''Take a request to the downloader and back, like Scrapy does'''
    def download(request, response=None):
        api_req = spb_md.process_request(request) or request
        assert spb_md.process_request(api_req) is None
        crawler.signals.send_catch_log(
            signals.request_reached_downloader, request=api_req, spider=None)
        sent = api_req.headers.get('Authorization')
        crawler.signals.send_catch_log(
            signals.request_left_downloader, request=api_req, spider=None)
        if response is not None:
            spb_md.process_response(api_req, response)
        return api_req, sent
    return download


def test_process_request(spb_md, spb_req):
    '''It should return a normal Request with a ScrapingBee API url'''
    spb_url = get_spb_url(DEFAULT_API_URL, DEFAULT_URL)
    new_req = spb_md.process_request(spb_req)
    assert isinstance(new_req, Request)
    assert new_req.url == spb_url
    assert new_req.meta['allow_offsite']
    assert not new_req.dont_filter


def test_process_request_bearer_auth(download, spb_req):
    '''It should send the API key in the Authorization header only'''
    new_req, sent = download(spb_req)
    assert sent == f'Bearer {DEFAULT_API_KEY}'.encode()
    assert 'api_key' not in new_req.url
    assert DEFAULT_API_KEY not in new_req.url


def test_process_request_keeps_forwarded_headers(download):
    '''It should keep the Spb- prefixed headers next to Authorization'''
    req = ScrapingBeeRequest(DEFAULT_URL, headers={'Authorization': 'site'})
    new_req, sent = download(req)
    assert new_req.headers.get('Spb-Authorization') == b'site'
    assert sent == f'Bearer {DEFAULT_API_KEY}'.encode()


def test_process_request_overrides_authorization(
        spb_md, download, spb_req, caplog):
    '''It should replace Authorization with the API key and warn once'''
    spb_req.headers['Authorization'] = 'Basic xxx'
    new_req = spb_md.process_request(spb_req)
    assert 'Authorization' not in new_req.headers
    assert download(spb_req)[1] == f'Bearer {DEFAULT_API_KEY}'.encode()
    assert spb_req.headers.get('Authorization') == b'Basic xxx'
    warnings = [r for r in caplog.records
                if 'replaces the Authorization header' in r.getMessage()]
    assert len(warnings) == 1


def test_process_request_no_warning_without_authorization(
        spb_md, spb_req, caplog):
    '''It should not warn when there is no Authorization header to replace'''
    spb_md.process_request(spb_req)
    assert not [r for r in caplog.records
                if 'replaces the Authorization header' in r.getMessage()]


def test_process_request_per_request_api_key(download):
    '''It should send a params api_key as Bearer, never in the url'''
    req = ScrapingBeeRequest(DEFAULT_URL, params={'api_key': 'OTHER-KEY'})
    new_req, sent = download(req)
    assert sent == b'Bearer OTHER-KEY'
    assert 'OTHER-KEY' not in new_req.url
    assert 'api_key' not in new_req.url
    assert req.meta['scrapingbee']['params']['api_key'] == 'OTHER-KEY'


def test_key_is_on_the_request_only_in_the_downloader(
        spb_md, download, spb_req):
    '''The key and allow_offsite should not outlive the download'''
    api_req = spb_md.process_request(spb_req)
    assert spb_md.process_request(api_req) is None
    assert DEFAULT_API_KEY not in str(api_req.to_dict())
    assert download(api_req)[1]
    assert 'Authorization' not in api_req.headers
    assert 'allow_offsite' not in api_req.meta


def test_cached_response_leaves_no_allow_offsite(spb_md, spb_req, spb_res):
    '''A response from the HTTP cache skips the downloader'''
    api_req = spb_md.process_request(spb_req)
    spb_md.process_response(api_req, spb_res)
    assert 'allow_offsite' not in api_req.meta


def test_retried_api_request_gets_the_key_again(download, spb_req, spb_res):
    '''A copy of the API request (a retry) is still the API call'''
    api_req, _ = download(spb_req, spb_res)
    retry = api_req.copy()
    assert retry.meta['allow_offsite']
    assert download(retry)[1] == f'Bearer {DEFAULT_API_KEY}'.encode()


@pytest.mark.parametrize('url', [
    'https://example.com/next',
    f'{DEFAULT_API_URL}?url=https%3A%2F%2Fevil.test&stealth_proxy=true',
    get_spb_url(DEFAULT_API_URL, DEFAULT_URL),
])
def test_derived_request_gets_no_key(spb_md, download, spb_req, spb_res, url):
    '''A redirect or replace(url=...) of the API request is not an API call'''
    queued = spb_md.process_request(spb_req).replace(url=url)
    api_req, _ = download(spb_req, spb_res)
    for derived in (queued, api_req.replace(url=url),
                    request_from_dict(api_req.replace(url=url).to_dict()),
                    api_req.replace(url=url, cls=Request),
                    type(api_req)(url)):
        assert download(derived)[1] is None
        assert 'allow_offsite' not in derived.meta


def test_other_requests_are_left_alone(download):
    '''A plain Request keeps its own Authorization and allow_offsite'''
    req = Request(DEFAULT_URL, headers={'Authorization': 'Basic xxx'},
                  meta={'allow_offsite': True})
    assert download(req, Response(DEFAULT_URL)) == (req, b'Basic xxx')
    assert req.headers.get('Authorization') == b'Basic xxx'
    assert req.meta['allow_offsite']


def test_response_url_of_derived_request_is_kept(spb_md, download, spb_req):
    '''A directly fetched page must not set response.url with a header'''
    derived = download(spb_req)[0].replace(url='https://example.com/next')
    res = Response(derived.url, headers={'Spb-Resolved-Url': 'https://x.com'})
    assert spb_md.process_response(derived, res) is res


def test_from_crawler_override_without_super(spb_req, spb_res):
    '''Without the downloader signals the key is added in process_request'''
    class CustomMiddleware(ScrapingBeeMiddleware):
        @classmethod
        def from_crawler(cls, crawler):
            return cls(api_key=DEFAULT_API_KEY)

    middleware = CustomMiddleware.from_crawler(get_crawler())
    api_req = middleware.process_request(spb_req)
    middleware.process_request(api_req)
    assert api_req.headers.get('Authorization') == \
        f'Bearer {DEFAULT_API_KEY}'.encode()
    middleware.process_response(api_req, spb_res)
    assert 'Authorization' not in api_req.headers


def test_requests_dropped_without_api_key(spb_req, caplog):
    '''Without a key, ScrapingBee requests are dropped, not fetched directly'''
    middleware = ScrapingBeeMiddleware.from_crawler(get_crawler())
    api_req = ScrapingBeeMiddleware.from_crawler(get_crawler(settings_dict={
        'SCRAPINGBEE_API_KEY': DEFAULT_API_KEY})).process_request(spb_req)
    # api_req: an API request saved in JOBDIR, resumed without a key.
    for req in (spb_req, spb_req, api_req):
        with pytest.raises(IgnoreRequest, match='SCRAPINGBEE_API_KEY'):
            middleware.process_request(req)
    errors = [r for r in caplog.records if 'is not set' in r.getMessage()]
    assert len(errors) == 1
    assert middleware.process_request(Request(DEFAULT_URL)) is None


def test_per_request_api_key_without_settings_key():
    '''A params api_key is enough when the settings have none'''
    crawler = get_crawler()
    middleware = ScrapingBeeMiddleware.from_crawler(crawler)
    req = ScrapingBeeRequest(DEFAULT_URL, params={'api_key': 'OTHER-KEY'})
    api_req = middleware.process_request(req)
    assert middleware.process_request(api_req) is None
    crawler.signals.send_catch_log(
        signals.request_reached_downloader, request=api_req, spider=None)
    assert api_req.headers.get('Authorization') == b'Bearer OTHER-KEY'


def test_middleware_subclass_without_super_init(spb_req):
    '''A subclass __init__ that doesn't call super() should still work'''
    class CustomMiddleware(ScrapingBeeMiddleware):
        def __init__(self):
            self.api_key = DEFAULT_API_KEY

    spb_req.headers['Authorization'] = 'Basic xxx'
    assert CustomMiddleware().process_request(spb_req) is not None


def test_process_response_ignores_plain_request(spb_md):
    '''It should return the response unchanged for a plain Request'''
    req = Request(DEFAULT_URL)
    res = Response(DEFAULT_URL, request=req,
                   headers={'Spb-Resolved-Url': 'https://other.com'})
    assert spb_md.process_response(req, res) is res


def test_process_request_encodes_params(spb_md):
    '''It should url-encode every query parameter exactly once'''
    url = 'https://example.com/?a=1&b=two words'
    rules = {'title': 'h1'}
    req = ScrapingBeeRequest(url, params={
        'custom_google': 'a&b=c',
        'render_js': False,
        'extract_rules': rules,
    }, headers={'X-T': '1'}, cookies={'k': 'v;x'})
    new_req = spb_md.process_request(req)
    qs = parse_qs(urlsplit(new_req.url).query)
    assert qs == {
        'url': [url],
        'cookies': ['k=v;x'],
        'custom_google': ['a&b=c'],
        'render_js': ['false'],
        'extract_rules': [json.dumps(rules)],
        'forward_headers': ['true'],
    }


def test_process_response(spb_md, spb_req, spb_res):
    '''It should return a normal Response with the website url'''
    new_req = spb_md.process_request(spb_req)
    new_res = spb_md.process_response(new_req, spb_res)
    assert isinstance(new_res, Response)
    # Compare with the resolved url header, not spb_req.url: w3lib 2.6+
    # adds a trailing slash to Request urls but not Response urls.
    assert new_res.url == spb_res.headers['Spb-Resolved-Url'].decode()


def test_process_response_without_resolved_url(spb_md, spb_req):
    '''An API error has no Spb-Resolved-Url; it should get the target url'''
    api_req = spb_md.process_request(spb_req)
    res = spb_md.process_response(api_req, Response(api_req.url, status=401))
    assert res.url == DEFAULT_URL


def test_api_request_survives_serialization(spb_md, download, spb_req):
    '''The API request keeps its default errback through to_dict()'''
    new_req = spb_md.process_request(spb_req)
    restored = request_from_dict(new_req.to_dict())
    assert restored.url == new_req.url
    assert restored.errback is log_scrapingbee_error
    assert dict(restored.headers) == dict(new_req.headers)
    assert restored.meta == new_req.meta
    assert download(restored)[1] == f'Bearer {DEFAULT_API_KEY}'.encode()
