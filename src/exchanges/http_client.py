"""
HTTP helper — thin wrapper around urllib for exchange API calls.
No heavy dependencies. Supports JSON, query params, HMAC signing,
and automatic retry with exponential backoff for transient failures.
"""

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class HttpClient:
    """Lightweight HTTP client using stdlib urllib with retry and rate-limit support."""

    def __init__(self, base_url: str, headers: dict | None = None, timeout: int = 15,
                 max_retries: int = 3, retry_base_delay: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.default_headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    def request(self, method: str, path: str, params: dict | None = None,
                body: dict | None = None, headers: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        hdrs = {**self.default_headers, **(headers or {})}

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                body_text = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    # Rate limited — respect Retry-After header
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    delay = float(retry_after) if retry_after else self.retry_base_delay * (2 ** attempt)
                    if attempt < self.max_retries:
                        logger.warning(
                            "Rate limited (429) from %s, retry %d/%d in %.1fs",
                            url, attempt + 1, self.max_retries, delay,
                        )
                        time.sleep(delay)
                        last_error = ExchangeRateLimitError(url, delay)
                        continue
                    raise ExchangeRateLimitError(url, delay) from e
                if e.code >= 500 and attempt < self.max_retries:
                    # Server errors are retryable
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "Server error (HTTP %d) from %s, retry %d/%d in %.1fs",
                        e.code, url, attempt + 1, self.max_retries, delay,
                    )
                    time.sleep(delay)
                    last_error = ExchangeAPIError(e.code, body_text, url)
                    continue
                raise ExchangeAPIError(e.code, body_text, url) from e
            except urllib.error.URLError as e:
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "Connection error to %s: %s, retry %d/%d in %.1fs",
                        url, e.reason, attempt + 1, self.max_retries, delay,
                    )
                    time.sleep(delay)
                    last_error = ExchangeConnectionError(str(e.reason), url)
                    continue
                raise ExchangeConnectionError(str(e.reason), url) from e
            except (TimeoutError, OSError) as e:
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "Timeout/network error to %s: %s, retry %d/%d in %.1fs",
                        url, e, attempt + 1, self.max_retries, delay,
                    )
                    time.sleep(delay)
                    last_error = e
                    continue
                raise

        # Should not reach here, but just in case:
        if last_error:
            raise last_error
        return {}

    def get(self, path: str, params: dict | None = None, **kw) -> dict | list:
        return self.request("GET", path, params=params, **kw)

    def post(self, path: str, body: dict | None = None, params: dict | None = None, **kw) -> dict | list:
        return self.request("POST", path, params=params, body=body, **kw)

    def delete(self, path: str, params: dict | None = None, **kw) -> dict | list:
        return self.request("DELETE", path, params=params, **kw)


class ExchangeAPIError(Exception):
    def __init__(self, status: int, body: str, url: str):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(f"HTTP {status} from {url}: {body[:200]}")


class ExchangeConnectionError(Exception):
    def __init__(self, reason: str, url: str):
        self.reason = reason
        self.url = url
        super().__init__(f"Connection error to {url}: {reason}")


class ExchangeRateLimitError(ExchangeAPIError):
    """Raised when exchange returns HTTP 429 (rate limit exceeded)."""

    def __init__(self, url: str, retry_after: float = 0.0):
        self.retry_after = retry_after
        super().__init__(429, f"Rate limited. Retry after {retry_after:.1f}s", url)


def hmac_sha256_sign(secret: str, message: str) -> str:
    """HMAC-SHA256 signature."""
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def timestamp_ms() -> int:
    """Current timestamp in milliseconds."""
    return int(time.time() * 1000)
