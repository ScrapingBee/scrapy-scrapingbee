# Changelog

## 0.1.0 - 2026-11-24

### Breaking changes

- Requires Python 3.9+ (was 3.5+) and Scrapy 2.13+ (previously unbounded).
- Pass raw parameter values. If you URL-encoded values yourself (e.g. `quote(json.dumps(rules))` or pre-quoted cookies) to work around older versions, remove that encoding, or the API will receive them double-encoded. A warning is logged (once per parameter) when a value looks like URL-encoded JSON.
- `request.meta['scrapingbee']['params']` now holds the `url` and `cookies` values unquoted, and dict or list parameters as JSON strings.
- Without `SCRAPINGBEE_API_KEY` (and without an `api_key` in `params`), a `ScrapingBeeRequest` is dropped with an error instead of being fetched directly from your machine; this also applies to requests resumed from `JOBDIR`. Other requests are not affected.
- API request URLs no longer contain `api_key`, so existing `HTTPCACHE_DIR` entries won't match and those pages will be fetched (and billed) again.

### Changed

- The API key is sent in the `Authorization: Bearer` header instead of the `api_key` query parameter, so it no longer appears in request URLs or in Scrapy's request log lines. The header is on the request only while it is being downloaded: it isn't stored in `JOBDIR` or the HTTP cache, isn't on `response.request`, and isn't passed on to redirects. (A per-request `api_key` in `params` stays in `request.meta`.)
- Dict, list and tuple parameters (`extract_rules`, `js_scenario`, `ai_extract_rules`, ...) are sent as JSON. They used to be sent as Python repr.
- A per-request `api_key` in `params` is sent as the Bearer token for that request instead of in the URL.
- The middleware logs a one-time warning when it replaces an existing `Authorization` header (for example one added by `HttpAuthMiddleware`).
- Middleware methods no longer require the `spider` argument, so Scrapy 2.14+ does not emit deprecation warnings.
- The middleware sends a `ScrapingBeeApiRequest` (a `Request` subclass) to the API, instead of a plain `Request`. It carries `allow_offsite` in its meta until it is downloaded, so `allowed_domains` doesn't drop it. A `ScrapingBeeMiddleware` subclass that overrides `from_crawler()` should call `super().from_crawler()`: otherwise the key is added when the request passes the middleware and removed when the response comes back.
- `ScrapingBeeRequest.process_cookies()` returns the cookie string unencoded; the middleware encodes it with the other parameters.
- When an API response has no `Spb-Resolved-Url` header (an API error), `response.url` is the target URL instead of the API URL.

### Fixed

- Parameter values other than `url` and `cookies` containing `&`, `#` or `+` were truncated or corrupted because they were not URL-encoded; all values are now encoded correctly.
- `ScrapingBeeRequest` no longer mutates its `params` argument or a shared default, which leaked `forward_headers=True` into later requests. `params=None` no longer raises.
- With `JOBDIR` set, requests lost their cookies and every ScrapingBee parameter except `url`, and forwarded headers were mangled, after passing through Scrapy's disk queue. Requests using the default errback, including the rewritten API request, couldn't be serialized at all, so they stayed in memory and every request still queued when the crawl was paused was lost. Both now survive serialization unchanged. (If a `ScrapingBeeRequest` subclass overrides `handle_error`, its API request can't be serialized, like any errback that isn't a spider method; pass a spider method as `errback` instead.)
- Spiders with `allowed_domains` sent no requests on Scrapy 2.11.2+: Scrapy's offsite middleware dropped the rewritten API request because the API host isn't in the list.
- Headers passed with bytes keys or as a Scrapy `Headers` object were forwarded under mangled names like ``Spb-b'Accept-Language'``.
- The default errback no longer raises `AttributeError` when an error response has a non-text body (for example a failed screenshot request).
- `copy()` and `replace()` on a `ScrapingBeeRequest` dropped its parameters and prefixed forwarded headers twice; they now keep both.
- Boolean parameters are sent as lowercase `true`/`false`, as the API documents, instead of `True`/`False`.
- `ScrapingBeeSpider` subclasses that define `start_requests()`, as the 0.0.x README showed, had it ignored on Scrapy 2.16+, which no longer calls it: `start_urls` were fetched directly instead of through ScrapingBee (or nothing was crawled if there were none). `ScrapingBeeSpider` now calls it for them.

### Deprecated

These still work but emit a `ScrapyDeprecationWarning` and will be removed in a future release:

- `ScrapingBeeSpider`: inherit from `scrapy.Spider` instead and rename `start_requests()` to `async def start()`. It no longer rewrites log formatters (nothing to hide now); `fmt` and `datefmt` are still accepted and ignored, so existing subclasses keep working.
- `HideApiKeyFormatter`: no longer needed, since the key is not in URLs.
- `ScrapingBeeRequest.process_url`: the middleware now encodes every parameter itself, so it is no longer called and overriding it has no effect.
