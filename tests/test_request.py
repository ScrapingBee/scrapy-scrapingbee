import json
import urllib.parse

import pytest
from scrapy.http import Headers, Response, TextResponse
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.request import request_from_dict
from twisted.python.failure import Failure

from scrapy_scrapingbee import ScrapingBeeRequest
from scrapy_scrapingbee import request as request_module
from scrapy_scrapingbee.request import RESTORE_META_KEY

DEFAULT_URL = 'https://example.com'


def test_scrapingbee_request():
    '''It should add the raw url to the request meta'''
    req = ScrapingBeeRequest(
        'https://example.com?p=1'
    )
    assert req.meta['scrapingbee']['params']['url'] == \
        'https://example.com?p=1'


def test_scrapingbee_params():
    '''It should add the parameters to the request meta'''
    req = ScrapingBeeRequest(DEFAULT_URL, params={
        'render_js': False,
    })
    assert req.meta['scrapingbee']['params']['render_js'] is False


def test_scrapingbee_js_snippet():
    '''It should b64 encode the JavaScript code'''
    req = ScrapingBeeRequest(DEFAULT_URL, params={
        'js_snippet': 'window.scrollTo(0, document.body.scrollHeight);'
    })
    assert req.meta['scrapingbee']['params']['js_snippet'] == \
        'd2luZG93LnNjcm9sbFRvKDAsIGRvY3VtZW50LmJvZHkuc2Nyb2xsSGVpZ2h0KTs='


def test_scrapingbee_headers():
    '''It should prefix headers with Spb- and set forward_headers param'''
    req = ScrapingBeeRequest(DEFAULT_URL, headers={
        'Accept-Language': 'En-US',
    })
    assert req.headers.get('Spb-Accept-Language') == b'En-US'
    assert req.meta['scrapingbee']['params']['forward_headers'] is True


@pytest.mark.parametrize('headers', [
    {b'Accept-Language': 'fr'},
    Headers({'Accept-Language': 'fr'}),
])
def test_scrapingbee_headers_bytes_keys(headers):
    '''It should prefix bytes keys and Headers objects correctly'''
    req = ScrapingBeeRequest(DEFAULT_URL, headers=headers)
    assert dict(req.headers) == {b'Spb-Accept-Language': [b'fr']}
    again = request_from_dict(req.to_dict())
    assert dict(again.headers) == dict(req.headers)


def test_scrapingbee_process_headers_override():
    '''A 0.0.x-style process_headers override should still get str keys'''
    class SkipRequest(ScrapingBeeRequest):
        @staticmethod
        def process_headers(d, prefix='Spb-'):
            return {f'{prefix}{k}': v for k, v in d.items() if k != 'X-Skip'}

    for headers in ({'Accept': 'a', 'X-Skip': '1'},
                    Headers({'Accept': 'a', 'X-Skip': '1'})):
        req = SkipRequest(DEFAULT_URL, headers=headers)
        assert dict(req.headers) == {b'Spb-Accept': [b'a']}
    assert ScrapingBeeRequest.process_headers({'a': 'b'}) == {'Spb-a': 'b'}


def test_scrapinbee_cookies():
    '''It should add the formated cookies to the request meta'''
    req = ScrapingBeeRequest(DEFAULT_URL, cookies={
        'name_1': 'value_1',
        'name_2': 'value_2',
    })
    assert req.meta['scrapingbee']['params']['cookies'] == \
        'name_1=value_1;name_2=value_2'


def test_scrapingbee_custom_errback():
    '''It should use the errback that was passed'''
    def errback(err):
        pass
    req = ScrapingBeeRequest('https://example.com?p=1', errback=errback)
    assert req.errback is errback


def test_scrapingbee_params_not_shared():
    '''It should not leak params into the caller's dict or later requests'''
    params = {'render_js': False}
    ScrapingBeeRequest(DEFAULT_URL, params=params, headers={'X': '1'})
    assert params == {'render_js': False}
    ScrapingBeeRequest(DEFAULT_URL, headers={'X': '1'})
    req = ScrapingBeeRequest(DEFAULT_URL)
    assert 'forward_headers' not in req.meta['scrapingbee']['params']


@pytest.fixture
def pre_encoded_warnings(caplog):
    request_module._warned_pre_encoded.clear()

    def collect():
        return [r for r in caplog.records
                if 'looks like URL-encoded JSON' in r.getMessage()]
    return collect


def test_scrapingbee_warns_on_pre_encoded_json(pre_encoded_warnings):
    '''It should warn once per param that looks like URL-encoded JSON'''
    rules = urllib.parse.quote(json.dumps({'title': 'h1'}))
    scenario = urllib.parse.quote(json.dumps([{'wait': 1}]))
    ScrapingBeeRequest(DEFAULT_URL, params={'extract_rules': rules})
    ScrapingBeeRequest(DEFAULT_URL, params={
        'extract_rules': rules, 'js_scenario': scenario})
    warned = [r.getMessage() for r in pre_encoded_warnings()]
    assert len(warned) == 2
    assert "'extract_rules'" in warned[0]
    assert "'js_scenario'" in warned[1]


def test_scrapingbee_no_warning_on_legitimate_escapes(pre_encoded_warnings):
    '''It should not warn for raw values or legitimate %XX escapes'''
    ScrapingBeeRequest('https://example.com/a%20b', params={
        'extract_rules': {'link': "a[href*='%2F']"},
        'js_scenario': '{"instructions": []}',
        'own_proxy': 'http://us%40er:p%40ss@proxy:8080',
        'wait': 1000,
    }, cookies='prefs=%7B%22lang%22%3A%22en%22%7D;sid=1')
    assert pre_encoded_warnings() == []


def test_scrapingbee_survives_serialization():
    '''It should rebuild identically from to_dict() (JOBDIR disk queues)'''
    req = ScrapingBeeRequest(DEFAULT_URL, params={
        'premium_proxy': True,
        'extract_rules': {'title': 'h1'},
    }, headers={'X-Test': 'hello'}, cookies={'a': '1'}, meta={'depth': 1})
    restored = request_from_dict(req.to_dict())
    assert isinstance(restored, ScrapingBeeRequest)
    assert restored.meta['scrapingbee'] == req.meta['scrapingbee']
    assert restored.meta['depth'] == 1
    assert RESTORE_META_KEY not in restored.meta
    assert dict(restored.headers) == dict(req.headers)
    assert restored.errback == restored.handle_error
    # A second round trip must not drift either.
    again = request_from_dict(restored.to_dict())
    assert again.meta['scrapingbee'] == req.meta['scrapingbee']
    assert dict(again.headers) == dict(req.headers)


def test_scrapingbee_copy_and_replace():
    '''copy() and replace() should keep params, headers and the errback'''
    req = ScrapingBeeRequest(DEFAULT_URL, params={'premium_proxy': True},
                             headers={'X-Test': 'hello'}, cookies={'a': '1'})
    for new in (req.copy(), req.replace(priority=5), req.replace(cls=None)):
        assert new.meta['scrapingbee'] == req.meta['scrapingbee']
        assert dict(new.headers) == dict(req.headers)
        assert new.errback == new.handle_error
        again = request_from_dict(new.to_dict())
        assert again.meta['scrapingbee'] == req.meta['scrapingbee']
        assert RESTORE_META_KEY not in new.meta
    moved = req.replace(url='https://other.com')
    assert moved.meta['scrapingbee']['params']['url'] == 'https://other.com'
    assert moved.meta['scrapingbee']['params']['premium_proxy'] is True


def test_scrapingbee_copy_subclass_with_fixed_params():
    '''copy() and replace() should work when a subclass sets params itself'''
    class PremiumRequest(ScrapingBeeRequest):
        def __init__(self, url, **kwargs):
            super().__init__(url, params={'premium_proxy': True}, **kwargs)

    req = PremiumRequest(DEFAULT_URL)
    for new in (req.copy(), req.replace(priority=5)):
        assert new.meta['scrapingbee'] == req.meta['scrapingbee']


def test_scrapingbee_reused_arguments():
    '''Reusing a params or headers dict must not change earlier requests'''
    params, headers = {'country_code': 'us'}, {'X-Test': 'us'}
    first = ScrapingBeeRequest(DEFAULT_URL, params=params, headers=headers)
    params['country_code'] = headers['X-Test'] = 'fr'
    ScrapingBeeRequest(DEFAULT_URL, params=params, headers=headers)
    for req in (request_from_dict(first.to_dict()), first.replace()):
        assert req.meta['scrapingbee']['params']['country_code'] == 'us'
        assert req.headers.get('Spb-X-Test') == b'us'


def test_handle_error_text_response(caplog):
    '''It should log the API error body for text responses'''
    req = ScrapingBeeRequest(DEFAULT_URL)
    res = TextResponse(DEFAULT_URL, status=500, body=b'{"error": "bad"}',
                       encoding='utf-8', request=req)
    req.handle_error(Failure(HttpError(res)))
    assert 'Got ScrapingBee error: {"error": "bad"}' in caplog.text


def test_handle_error_binary_response(caplog):
    '''It should not crash on non-text (e.g. screenshot) error bodies'''
    req = ScrapingBeeRequest(DEFAULT_URL)
    res = Response(DEFAULT_URL, status=500, body=b'\x89PNG' + b'0' * 96,
                   request=req)
    req.handle_error(Failure(HttpError(res)))
    assert '100 bytes of non-text content' in caplog.text


def test_scrapingbee_json_params():
    '''It should serialize dict and list params as JSON'''
    rules = {'title': 'h1', 'links': {'selector': 'a', 'type': 'list'}}
    scenario = {'instructions': [{'click': '#b'}, {'wait': 1000}]}
    req = ScrapingBeeRequest(DEFAULT_URL, params={
        'extract_rules': rules,
        'js_scenario': scenario,
        'a_list': ['a', 'b'],
        'a_tuple': ('c', 'd'),
        'empty_tuple': (),
    })
    params = req.meta['scrapingbee']['params']
    assert json.loads(params['extract_rules']) == rules
    assert json.loads(params['js_scenario']) == scenario
    assert json.loads(params['a_list']) == ['a', 'b']
    assert json.loads(params['a_tuple']) == ['c', 'd']
    assert 'empty_tuple' not in params
