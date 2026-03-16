"""
FinClaw - Correlation Analysis
Rolling correlation, hierarchical clustering, regime detection, diversification.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class CorrelationRegime:
    label: str          # "normal" or "crisis"
    avg_correlation: float
    period_start: int   # index
    period_end: int


class CorrelationAnalyzer:
    """
    Analyze correlations between assets for portfolio construction.
    Works with return series (list of lists, one per asset).
    """

    @staticmethod
    def _mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    @staticmethod
    def _std(xs: list[float], mean: Optional[float] = None) -> float:
        if len(xs) < 2:
            return 0.0
        m = mean if mean is not None else sum(xs) / len(xs)
        var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
        return math.sqrt(var)

    @staticmethod
    def pearson(x: list[float], y: list[float]) -> float:
        """Pearson correlation between two series of equal length."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0
        mx = sum(x[:n]) / n
        my = sum(y[:n]) / n
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)
        sx = math.sqrt(sum((x[i] - mx) ** 2 for i in range(n)) / (n - 1))
        sy = math.sqrt(sum((y[i] - my) ** 2 for i in range(n)) / (n - 1))
        if sx < 1e-12 or sy < 1e-12:
            return 0.0
        return cov / (sx * sy)

    def correlation_matrix(self, returns: dict[str, list[float]]) -> dict[str, dict[str, float]]:
        """Full pairwise correlation matrix."""
        tickers = list(returns.keys())
        matrix: dict[str, dict[str, float]] = {}
        for a in tickers:
            matrix[a] = {}
            for b in tickers:
                if a == b:
                    matrix[a][b] = 1.0
                elif b in matrix and a in matrix[b]:
                    matrix[a][b] = matrix[b][a]
                else:
                    matrix[a][b] = self.pearson(returns[a], returns[b])
        return matrix

    def rolling_correlation(
        self, x: list[float], y: list[float], window: int = 60
    ) -> list[float]:
        """Rolling Pearson correlation with given window."""
        result = []
        for i in range(len(x)):
            if i < window - 1:
                result.append(float("nan"))
            else:
                result.append(self.pearson(x[i - window + 1:i + 1], y[i - window + 1:i + 1]))
        return result

    def hierarchical_cluster(
        self, returns: dict[str, list[float]]
    ) -> list[tuple[str, str, float]]:
        """
        Single-linkage hierarchical clustering based on correlation distance.
        Returns merge history: (asset_a, asset_b, distance).
        """
        matrix = self.correlation_matrix(returns)
        tickers = list(returns.keys())
        # Correlation distance: d = 1 - corr
        clusters: list[set[str]] = [{t} for t in tickers]
        merges: list[tuple[str, str, float]] = []

        while len(clusters) > 1:
            best_dist = float("inf")
            best_i, best_j = 0, 1
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    # Single linkage: min distance between any pair
                    d = min(
                        1 - matrix[a][b]
                        for a in clusters[i]
                        for b in clusters[j]
                    )
                    if d < best_dist:
                        best_dist = d
                        best_i, best_j = i, j

            label_a = ",".join(sorted(clusters[best_i]))
            label_b = ",".join(sorted(clusters[best_j]))
            merges.append((label_a, label_b, best_dist))
            clusters[best_i] = clusters[best_i] | clusters[best_j]
            clusters.pop(best_j)

        return merges

    def detect_correlation_regimes(
        self,
        returns: dict[str, list[float]],
        window: int = 60,
        crisis_threshold: float = 0.6,
    ) -> list[CorrelationRegime]:
        """
        Detect normal vs crisis regimes based on average pairwise correlation.
        Crisis = when avg correlation exceeds threshold (correlations spike).
        """
        tickers = list(returns.keys())
        if len(tickers) < 2:
            return []

        n = min(len(r) for r in returns.values())
        # Compute rolling average correlation across all pairs
        pairs = [(a, b) for i, a in enumerate(tickers) for b in tickers[i+1:]]
        rolling_avg: list[float] = []

        for t in range(n):
            if t < window - 1:
                rolling_avg.append(float("nan"))
                continue
            corrs = []
            for a, b in pairs:
                c = self.pearson(returns[a][t - window + 1:t + 1], returns[b][t - window + 1:t + 1])
                corrs.append(c)
            rolling_avg.append(sum(corrs) / len(corrs) if corrs else 0)

        # Segment into regimes
        regimes: list[CorrelationRegime] = []
        current_label = None
        start = 0
        corrs_in_regime: list[float] = []

        for i, avg in enumerate(rolling_avg):
            if math.isnan(avg):
                continue
            label = "crisis" if avg >= crisis_threshold else "normal"
            if label != current_label:
                if current_label is not None:
                    regimes.append(CorrelationRegime(
                        label=current_label,
                        avg_correlation=sum(corrs_in_regime) / len(corrs_in_regime),
                        period_start=start,
                        period_end=i - 1,
                    ))
                current_label = label
                start = i
                corrs_in_regime = [avg]
            else:
                corrs_in_regime.append(avg)

        if current_label and corrs_in_regime:
            regimes.append(CorrelationRegime(
                label=current_label,
                avg_correlation=sum(corrs_in_regime) / len(corrs_in_regime),
                period_start=start,
                period_end=n - 1,
            ))

        return regimes

    def compute(self, returns: dict[str, list[float]]) -> dict[str, dict[str, float]]:
        """Compute full correlation matrix. Alias for correlation_matrix."""
        return self.correlation_matrix(returns)

    def find_uncorrelated(self, returns: dict[str, list[float]], threshold: float = 0.3) -> list[tuple[str, str, float]]:
        """
        Find pairs of assets with absolute correlation below threshold.
        
        Returns:
            List of (asset_a, asset_b, correlation) tuples
        """
        matrix = self.correlation_matrix(returns)
        tickers = list(returns.keys())
        pairs = []
        for i, a in enumerate(tickers):
            for b in tickers[i + 1:]:
                corr = matrix[a][b]
                if abs(corr) < threshold:
                    pairs.append((a, b, corr))
        return sorted(pairs, key=lambda x: abs(x[2]))

    def render_heatmap_html(self, returns: dict[str, list[float]], output_path: str) -> str:
        """
        Render correlation matrix as an HTML heatmap file.

        Args:
            returns: Dict of ticker → return series
            output_path: File path to write HTML

        Returns:
            The output_path written
        """
        matrix = self.correlation_matrix(returns)
        tickers = list(returns.keys())

        def _color(v: float) -> str:
            # Red for positive, blue for negative correlation
            if v >= 0:
                r, g, b = 255, int(255 * (1 - v)), int(255 * (1 - v))
            else:
                r, g, b = int(255 * (1 + v)), int(255 * (1 + v)), 255
            return f'rgb({r},{g},{b})'

        rows_html = []
        for a in tickers:
            cells = ''.join(
                f'<td style="background:{_color(matrix[a][b])};text-align:center;padding:8px">{matrix[a][b]:.2f}</td>'
                for b in tickers
            )
            rows_html.append(f'<tr><th style="padding:8px">{a}</th>{cells}</tr>')

        header = ''.join(f'<th style="padding:8px">{t}</th>' for t in tickers)
        html = f"""<!DOCTYPE html>
<html><head><title>Correlation Heatmap</title></head>
<body><h2>Correlation Matrix</h2>
<table border="1" style="border-collapse:collapse;font-family:monospace">
<tr><th></th>{header}</tr>
{''.join(rows_html)}
</table></body></html>"""

        with open(output_path, 'w') as f:
            f.write(html)
        return output_path

    def diversification_ratio(self, returns: dict[str, list[float]], weights: dict[str, float]) -> float:
        """
        Diversification ratio = weighted avg vol / portfolio vol.
        > 1 means diversification benefit. Higher is better.
        """
        tickers = list(weights.keys())
        n = min(len(returns[t]) for t in tickers)
        if n < 2:
            return 1.0

        vols = {}
        for t in tickers:
            vols[t] = self._std(returns[t][:n])

        # Weighted average volatility
        w_avg_vol = sum(weights[t] * vols[t] for t in tickers)

        # Portfolio volatility
        port_returns = []
        for i in range(n):
            port_returns.append(sum(weights[t] * returns[t][i] for t in tickers))
        port_vol = self._std(port_returns)

        if port_vol < 1e-12:
            return 1.0

        return w_avg_vol / port_vol
