'''Contract tests against the installed Scrapy version.

These go through Scrapy's own machinery (middleware manager, a real crawl)
rather than calling middleware methods directly, so they fail when Scrapy
changes how it loads or calls downloader middlewares.
'''
import subprocess
import sys
import threading
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest
from scrapy.core.downloader.middleware import DownloaderMiddlewareManager
from scrapy.utils.test import get_crawler

API_KEY = 'CONTRACT-API-KEY'
TARGET_URL = 'https://example.com/?a=1&b=two words'
MIDDLEWARE = 'scrapy_scrapingbee.ScrapingBeeMiddleware'

CRAWL_SCRIPT = '''
import sys

import scrapy
from scrapy.crawler import CrawlerProcess

from scrapy_scrapingbee import ScrapingBeeMiddleware, ScrapingBeeRequest

ScrapingBeeMiddleware.scrapingbee_api_url = sys.argv[1]


class ContractSpider(scrapy.Spider):
    name = 'contract'
    # The API host is never listed; the API request must not be filtered.
    allowed_domains = sys.argv[5:]

    async def start(self):
        yield ScrapingBeeRequest(sys.argv[3], params={'render_js': False})

    def parse(self, response):
        print('RESPONSE_URL', response.url)


process = CrawlerProcess(settings={
    'SCRAPINGBEE_API_KEY': sys.argv[2],
    'DOWNLOADER_MIDDLEWARES': {'%s': 725},
    'JOBDIR': sys.argv[4],
})
process.crawl(ContractSpider)
process.start()
''' % MIDDLEWARE


def test_no_spider_argument_deprecation():
    '''Scrapy should not warn about our middleware method signatures'''
    crawler = get_crawler(settings_dict={
        'SCRAPINGBEE_API_KEY': API_KEY,
        'DOWNLOADER_MIDDLEWARES': {MIDDLEWARE: 725},
    })
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        DownloaderMiddlewareManager.from_crawler(crawler)
    ours = [str(w.message) for w in caught
            if 'ScrapingBeeMiddleware' in str(w.message)]
    assert ours == []


@pytest.fixture
def stub_api():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append((self.path, dict(self.headers)))
            status, body = 200, b'ok'
            if 'flaky' in self.path and len(received) == 1:
                status = 500
            if 'refresh' in self.path:
                # A page that tries to make the crawler call the API again.
                body = (b'<meta http-equiv="refresh" content="0;url=http://%s'
                        b'/api/v1/?url=https%%3A%%2F%%2Fevil.test">'
                        % self.headers['Host'].encode())
            self.send_response(status)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Spb-Resolved-Url', 'https://example.com/done')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}/api/v1/', received
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def crawl(api_url, target_url, jobdir, *allowed_domains, api_key=API_KEY):
    result = subprocess.run(
        [sys.executable, '-c', CRAWL_SCRIPT, api_url, api_key, target_url,
         str(jobdir), *allowed_domains],
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result


def test_real_crawl(stub_api, tmp_path):
    '''A real crawl should use Bearer auth and encode params properly'''
    api_url, received = stub_api
    result = crawl(api_url, TARGET_URL, tmp_path / 'job', 'example.com')

    assert len(received) == 1
    path, headers = received[0]
    assert headers['Authorization'] == f'Bearer {API_KEY}'
    assert API_KEY not in path
    assert parse_qs(urlsplit(path).query) == {
        'url': [TARGET_URL],
        'render_js': ['false'],
    }
    assert 'RESPONSE_URL https://example.com/done' in result.stdout
    assert API_KEY not in result.stdout + result.stderr
    # Every request, including the rewritten API one, went to the disk queue.
    assert "'scheduler/enqueued/disk': 2" in result.stderr
    assert 'scheduler/unserializable' not in result.stderr
    # Scrapy logs crawl-time warnings; some name only our class, not module.
    ours = [line for line in result.stderr.splitlines()
            if 'Warning' in line
            and ('scrapy_scrapingbee' in line or 'ScrapingBee' in line)]
    assert ours == []


def test_retry_with_allowed_domains(stub_api, tmp_path):
    '''A retried API request should not be filtered as offsite'''
    api_url, received = stub_api
    result = crawl(api_url, 'https://example.com/flaky', tmp_path / 'job',
                   'example.com')
    assert [headers.get('Authorization') for _, headers in received] == \
        [f'Bearer {API_KEY}'] * 2
    assert 'RESPONSE_URL https://example.com/done' in result.stdout


@pytest.mark.parametrize('allowed_domains,expected', [
    # Filtered as offsite: the redirect is not exempt like the API request.
    (['example.com'], [f'Bearer {API_KEY}']),
    # Followed like any meta refresh, without the key.
    ([], [f'Bearer {API_KEY}', None]),
])
def test_scraped_page_cannot_call_the_api(
        stub_api, tmp_path, allowed_domains, expected):
    '''A meta refresh to the API in a scraped page should not get the key'''
    api_url, received = stub_api
    crawl(api_url, 'https://example.com/refresh', tmp_path / 'job',
          *allowed_domains)
    assert [headers.get('Authorization') for _, headers in received] == \
        expected


def test_no_api_key(stub_api, tmp_path):
    '''Without a key, nothing is fetched, through the API or directly'''
    api_url, received = stub_api
    result = crawl(api_url, TARGET_URL, tmp_path / 'job', api_key='')
    assert received == []
    assert 'RESPONSE_URL' not in result.stdout
    assert 'SCRAPINGBEE_API_KEY is not set' in result.stderr
