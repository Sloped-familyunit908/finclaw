"""Generic REST API data source."""

import json
import urllib.request
from .base import DataSource


class APISource(DataSource):
    """Fetch data from a REST API endpoint.

    The API should return JSON array of objects with date/close fields.
    URL template supports {symbol}, {start}, {end} placeholders.
    """

    def __init__(self, url_template: str, headers: dict | None = None,
                 response_key: str | None = None, timeout: int = 30):
        self.url_template = url_template
        self.headers = headers or {}
        self.response_key = response_key  # JSON key containing the data array
        self.timeout = timeout

    def fetch(self, symbols: list[str], start: str, end: str) -> dict[str, list[dict]]:
        result = {}
        for symbol in symbols:
            url = self.url_template.format(symbol=symbol, start=start, end=end)
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode())
                if self.response_key:
                    data = data.get(self.response_key, [])
                result[symbol] = data if isinstance(data, list) else []
            except Exception:
                result[symbol] = []
        return result

    def validate(self) -> bool:
        return bool(self.url_template)
