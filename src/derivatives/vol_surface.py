"""Implied volatility surface construction and visualization."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class _VolPoint:
    strike: float
    expiry: float
    implied_vol: float


class VolatilitySurface:
    """Build and query an implied volatility surface from market quotes."""

    def __init__(self) -> None:
        self._points: list[_VolPoint] = []

    def add_point(self, strike: float, expiry: float, implied_vol: float) -> None:
        """Add a market-observed implied volatility point."""
        if implied_vol <= 0:
            raise ValueError("implied_vol must be positive")
        if expiry <= 0:
            raise ValueError("expiry must be positive")
        self._points.append(_VolPoint(strike, expiry, implied_vol))

    @property
    def points(self) -> list[dict]:
        return [{"strike": p.strike, "expiry": p.expiry, "implied_vol": p.implied_vol} for p in self._points]

    def interpolate(self, strike: float, expiry: float) -> float:
        """Inverse-distance-weighted interpolation on the surface.

        Falls back to nearest point if only one data point exists.
        """
        if not self._points:
            raise ValueError("No data points in the surface")

        if len(self._points) == 1:
            return self._points[0].implied_vol

        # Normalize strike and expiry to comparable scales
        strikes = [p.strike for p in self._points]
        expiries = [p.expiry for p in self._points]
        s_range = max(strikes) - min(strikes) or 1.0
        e_range = max(expiries) - min(expiries) or 1.0

        weights = []
        for p in self._points:
            dist = math.sqrt(((strike - p.strike) / s_range) ** 2 + ((expiry - p.expiry) / e_range) ** 2)
            if dist < 1e-12:
                return p.implied_vol
            weights.append(1.0 / dist)

        total = sum(weights)
        return sum(w * p.implied_vol / total for w, p in zip(weights, self._points))

    def get_smile(self, expiry: float) -> dict:
        """Get the volatility smile for a given expiry.

        Returns dict mapping strike -> implied_vol for points at (or nearest to) the given expiry.
        """
        if not self._points:
            return {}

        # Group by expiry, find closest
        unique_expiries = sorted(set(p.expiry for p in self._points))
        closest = min(unique_expiries, key=lambda e: abs(e - expiry))
        return {p.strike: p.implied_vol for p in self._points if p.expiry == closest}

    def render_html(self, output_path: str) -> None:
        """Render a 3D volatility surface as a standalone HTML file using Plotly CDN."""
        strikes = [p.strike for p in self._points]
        expiries = [p.expiry for p in self._points]
        vols = [p.implied_vol for p in self._points]

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Volatility Surface</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head><body>
<div id="surface" style="width:100%;height:90vh;"></div>
<script>
var data = [{{
  type: 'mesh3d',
  x: {json.dumps(strikes)},
  y: {json.dumps(expiries)},
  z: {json.dumps(vols)},
  intensity: {json.dumps(vols)},
  colorscale: 'Viridis',
  opacity: 0.85
}}];
var layout = {{
  title: 'Implied Volatility Surface',
  scene: {{xaxis: {{title: 'Strike'}}, yaxis: {{title: 'Expiry (yrs)'}}, zaxis: {{title: 'IV'}}}}
}};
Plotly.newPlot('surface', data, layout);
</script></body></html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
