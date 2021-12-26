import urllib.parse

from scrapy_scrapingbee import ScrapingBeeRequest

DEFAULT_URL = 'https://example.com'


def test_scrapingbee_request():
    '''It should add the encoded url to the request meta'''
    req = ScrapingBeeRequest(
        'https://example.com?p=1'
    )
    assert req.meta['scrapingbee']['params']['url'] == \
        'https%3A//example.com%3Fp%3D1'


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


def test_scrapinbee_cookies():
    '''It should add the formated cookies to the request meta'''
    req = ScrapingBeeRequest(DEFAULT_URL, cookies={
        'name_1': 'value_1',
        'name_2': 'value_2',
    })
    assert urllib.parse.unquote(req.meta['scrapingbee']['params']['cookies']) \
           == 'name_1=value_1;name_2=value_2'


def test_scrapingbee_custom_errback():
    '''It should add the encoded url to the request meta'''
    req = ScrapingBeeRequest(
        'https://example.com?p=1',
        errback=lambda err: print(err)
    )
    assert req.errback
