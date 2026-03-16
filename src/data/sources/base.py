"""Base classes for data sources and sinks."""

from abc import ABC, abstractmethod
from typing import Any


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def fetch(self, symbols: list[str], start: str, end: str) -> dict[str, list[dict]]:
        """
        Fetch data for given symbols in date range.
        Returns {symbol: [rows]} where each row is a dict with at least 'date' and 'close'.
        """
        ...

    def validate(self) -> bool:
        """Check if source is accessible."""
        return True


class DataSink(ABC):
    """Abstract base class for data sinks."""

    @abstractmethod
    def write(self, symbol: str, data: list[dict]) -> int:
        """Write data rows for a symbol. Returns number of rows written."""
        ...

    @abstractmethod
    def read(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        """Read data back from sink."""
        ...

    def close(self) -> None:
        """Cleanup resources."""
        pass
