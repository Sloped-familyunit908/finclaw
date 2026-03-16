"""
FinClaw Indicator Plugin Interface
Custom technical indicators as plugins.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from src.plugins.plugin_base import Plugin


class IndicatorPlugin(Plugin):
    """
    Base class for indicator plugins.

    Subclass this and implement calculate() and get_params_schema().
    """

    plugin_type: str = "indicator"

    @abstractmethod
    def calculate(self, data: list[dict[str, Any]], **params: Any) -> list[dict[str, Any]]:
        """
        Calculate indicator values from OHLCV data.

        Args:
            data: List of candle dicts with keys: timestamp, open, high, low, close, volume.
            **params: Indicator parameters.

        Returns:
            List of dicts with keys: timestamp, value, and any extra fields.
        """
        ...

    @abstractmethod
    def get_params_schema(self) -> dict[str, Any]:
        """
        Return the parameter schema for this indicator.

        Returns:
            Dict describing parameters, e.g.:
            {
                'period': {'type': 'int', 'default': 14, 'min': 1, 'max': 200, 'description': 'Lookback period'},
            }
        """
        ...

    def validate_params(self, **params: Any) -> dict[str, Any]:
        """Validate and fill defaults for parameters."""
        schema = self.get_params_schema()
        result = {}
        for key, spec in schema.items():
            value = params.get(key, spec.get("default"))
            if value is None:
                raise ValueError(f"Missing required parameter: {key}")
            if "min" in spec and value < spec["min"]:
                raise ValueError(f"{key} must be >= {spec['min']}")
            if "max" in spec and value > spec["max"]:
                raise ValueError(f"{key} must be <= {spec['max']}")
            result[key] = value
        return result
