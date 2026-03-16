"""
HTTP helper — thin wrapper around urllib for exchange API calls.
No heavy dependencies. Supports JSON, query params, and HMAC signing.
"""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class HttpClient:
    """Lightweight HTTP client using stdlib urllib."""

    def __init__(self, base_url: str, headers: dict | None = None, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.default_headers = headers or {}
        self.timeout = timeout

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

        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise ExchangeAPIError(e.code, body_text, url) from e
        except urllib.error.URLError as e:
            raise ExchangeConnectionError(str(e.reason), url) from e

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


def hmac_sha256_sign(secret: str, message: str) -> str:
    """HMAC-SHA256 signature."""
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def timestamp_ms() -> int:
    """Current timestamp in milliseconds."""
    return int(time.time() * 1000)
