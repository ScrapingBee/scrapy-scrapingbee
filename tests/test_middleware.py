import pytest
from scrapy import Request
from scrapy.http import Response
from scrapy.utils.test import get_crawler

from scrapy_scrapingbee import ScrapingBeeRequest, ScrapingBeeMiddleware

DEFAULT_API_URL = ScrapingBeeMiddleware.scrapingbee_api_url
DEFAULT_API_KEY = 'API-KEY'
DEFAULT_URL = 'https://example.com'


def get_spb_url(api_url, api_key, url):
    encoded_url = ScrapingBeeRequest.process_url(url)
    return f'{api_url}?api_key={api_key}&url={encoded_url}'


@pytest.fixture
def spb_md(api_key=DEFAULT_API_KEY):
    crawler = get_crawler(settings_dict={
        'SCRAPINGBEE_API_KEY': api_key})
    return ScrapingBeeMiddleware.from_crawler(crawler)


@pytest.fixture
def spb_req(url=DEFAULT_URL):
    return ScrapingBeeRequest(url)


@pytest.fixture
def spb_res(api_key=DEFAULT_API_KEY, url=DEFAULT_URL):
    spb_url = get_spb_url(DEFAULT_API_URL, api_key, url)
    headers = {'Spb-Resolved-Url': url}
    return Response(spb_url, headers=headers)


def test_process_request(spb_md, spb_req):
    '''It should return a normal Request with a ScrapingBee API url'''
    spb_url = get_spb_url(DEFAULT_API_URL, DEFAULT_API_KEY, DEFAULT_URL)
    new_req = spb_md.process_request(spb_req, None)
    assert isinstance(new_req, Request)
    assert new_req.url == spb_url


def test_process_response(spb_md, spb_req, spb_res):
    '''It should return a normal Response with the website url'''
    new_req = spb_md.process_request(spb_req, None)
    new_res = spb_md.process_response(new_req, spb_res, None)
    assert isinstance(new_res, Response)
    assert new_res.url == spb_req.url
