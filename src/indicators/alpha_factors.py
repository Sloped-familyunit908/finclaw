"""
Alpha Factors inspired by Microsoft Qlib Alpha158.

Pure NumPy implementation for OHLCV data.  Every function accepts raw
``np.ndarray`` vectors and returns arrays of the same length, with the
first ``window - 1`` elements filled with ``np.nan``.

Reference
---------
- Qlib Alpha158 loader:
  https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py
- Investopedia — Linear Regression Indicator:
  https://www.investopedia.com/terms/l/linearregressionindicatorlri.asp
- Investopedia — Aroon Indicator:
  https://www.investopedia.com/terms/a/aroon.asp
"""

from __future__ import annotations

import numpy as np


# ── helpers ──────────────────────────────────────────────────────────

def _rolling_linear_regression(y: np.ndarray, window: int):
    """Vectorised rolling OLS of *y* against [0, 1, …, window-1].

    Returns (slope, r_squared) arrays, both of length ``len(y)``,
    with the first ``window - 1`` elements set to ``np.nan``.

    Uses the analytical closed-form for simple linear regression
    rather than calling ``np.polyfit`` on every window (O(n) overall).

    Formulas (x = 0 … w-1):
        x̄  = (w-1)/2
        Σx² = w*(w-1)*(2w-1)/6
        Var(x) = Σx²/w - x̄²  = w² - 1)/12

        slope  = Cov(x, y) / Var(x)
        r²     = Cov(x, y)² / (Var(x) * Var(y))
    """
    n = len(y)
    slope = np.full(n, np.nan)
    rsq = np.full(n, np.nan)

    if n < window or window < 2:
        return slope, rsq

    w = window
    # Pre-compute constants for x = 0 … w-1
    x_bar = (w - 1) / 2.0
    # Var(x) = (w² - 1) / 12
    var_x = (w * w - 1) / 12.0
    # sum_x = w * (w - 1) / 2
    sum_x = w * (w - 1) / 2.0
    # sum_x2 = w * (w - 1) * (2w - 1) / 6
    sum_x2 = w * (w - 1) * (2 * w - 1) / 6.0

    # x_indices weights: x_i = i  for i in [0, w)
    # Cov(x, y) = (1/w) * Σ x_i * y_i  -  x̄ * ȳ
    #           = (1/w) * (Σ i * y_i)  -  x̄ * ȳ
    # We need rolling Σ y_i  and  rolling Σ i * y_i.

    # Build weighted array: weight[j] = j  for positions inside window.
    # For the first full window [0, w):
    #   Σ i * y[i]  (i = 0 … w-1)
    # When window slides by one, the new window covers y[k-w+1 … k]:
    #   mapped x = 0 … w-1  ⇒  x_i  corresponds to  y[k - w + 1 + i]
    #   Σ x_i * y[k-w+1+i]  =  Σ_{j=k-w+1}^{k}  (j - (k-w+1)) * y[j]
    #                        =  Σ j*y[j] for j in window  - (k-w+1) * Σ y[j]
    # ... but that still needs rolling Σ j*y[j].

    # cumulative sums for O(1) per-window queries
    cum_y = np.zeros(n + 1)
    cum_y[1:] = np.cumsum(y)

    # Weighted cumsum:  W[j] = j * y[j]
    idx = np.arange(n, dtype=np.float64)
    cum_wy = np.zeros(n + 1)
    cum_wy[1:] = np.cumsum(idx * y)

    # Also need rolling sum of y² for Var(y)
    cum_y2 = np.zeros(n + 1)
    cum_y2[1:] = np.cumsum(y * y)

    for k in range(w - 1, n):
        start = k - w + 1
        # Σ y  in window
        s_y = cum_y[k + 1] - cum_y[start]
        # Σ j * y[j]  in window  (j = global index)
        s_wy = cum_wy[k + 1] - cum_wy[start]
        # Map to local x: Σ x_i * y_i = Σ (j - start) * y[j] = s_wy - start * s_y
        s_xy_local = s_wy - start * s_y

        y_bar = s_y / w
        cov_xy = s_xy_local / w - x_bar * y_bar  # Cov(x, y)

        slope[k] = cov_xy / var_x

        # Var(y)
        s_y2 = cum_y2[k + 1] - cum_y2[start]
        var_y = s_y2 / w - y_bar * y_bar

        if var_y < 1e-30:
            # Constant series ⇒ perfect fit but zero slope
            rsq[k] = 1.0 if abs(cov_xy) < 1e-15 else 0.0
        else:
            rsq[k] = (cov_xy * cov_xy) / (var_x * var_y)

    return slope, rsq


# ── public API ───────────────────────────────────────────────────────

def beta(close: np.ndarray, window: int = 20) -> np.ndarray:
    """BETA — normalised linear-regression slope of close prices.

    Measures trend *strength* more precisely than moving averages.

    * Positive → uptrend, negative → downtrend.
    * Magnitude indicates how steeply the price is moving per bar,
      normalised by the current price so the value is unit-free.

    Qlib formula::

        Slope($close, d) / $close

    Parameters
    ----------
    close : np.ndarray
        1-D array of closing prices.
    window : int, default 20
        Rolling look-back window.

    Returns
    -------
    np.ndarray
        Same length as *close*; first ``window - 1`` values are ``nan``.

    References
    ----------
    - Qlib Alpha158 — ``BETA`` factor.
    - Investopedia: *Linear Regression Indicator*
      https://www.investopedia.com/terms/l/linearregressionindicatorlri.asp
    """
    close = np.asarray(close, dtype=np.float64)
    if close.size == 0:
        return np.array([], dtype=np.float64)

    slope, _ = _rolling_linear_regression(close, window)

    # Normalise by close; guard against zero close
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(close != 0, slope / close, np.nan)

    # Ensure leading NaNs
    result[: window - 1] = np.nan
    return result


def rsqr(close: np.ndarray, window: int = 20) -> np.ndarray:
    """RSQR — R-squared of the rolling linear regression on close.

    Measures how *linear* (clear) the trend is.

    * R² > 0.7 → clear, tradeable trend (good for trend-following).
    * R² < 0.3 → choppy / mean-reverting (avoid trend strategies).

    Qlib formula::

        Rsquare($close, d)

    Parameters
    ----------
    close : np.ndarray
        1-D array of closing prices.
    window : int, default 20
        Rolling look-back window.

    Returns
    -------
    np.ndarray
        Values in [0, 1]; first ``window - 1`` values are ``nan``.

    References
    ----------
    - Qlib Alpha158 — ``RSQR`` factor.
    - Investopedia: *R-Squared*
      https://www.investopedia.com/terms/r/r-squared.asp
    """
    close = np.asarray(close, dtype=np.float64)
    if close.size == 0:
        return np.array([], dtype=np.float64)

    _, rsq = _rolling_linear_regression(close, window)
    # Clamp to [0, 1] to handle floating-point overshoot
    rsq = np.clip(rsq, 0.0, 1.0)
    return rsq


def corr_price_volume(
    close: np.ndarray,
    volume: np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """CORR — rolling Pearson correlation between close and log-volume.

    * Positive correlation → price and volume move together (healthy trend).
    * Negative correlation → divergence (potential reversal signal).

    Qlib formula::

        Corr($close, Log($volume + 1), d)

    Parameters
    ----------
    close : np.ndarray
        1-D array of closing prices.
    volume : np.ndarray
        1-D array of volumes (non-negative).
    window : int, default 20
        Rolling look-back window.

    Returns
    -------
    np.ndarray
        Values in [-1, 1]; first ``window - 1`` values are ``nan``.

    References
    ----------
    - Qlib Alpha158 — ``CORR`` factor.
    - Investopedia: *Correlation Coefficient*
      https://www.investopedia.com/terms/c/correlationcoefficient.asp
    """
    close = np.asarray(close, dtype=np.float64)
    volume = np.asarray(volume, dtype=np.float64)

    if close.size == 0:
        return np.array([], dtype=np.float64)

    n = len(close)
    result = np.full(n, np.nan)

    if n < window or window < 2:
        return result

    log_vol = np.log(volume + 1.0)

    # Cumulative sums for O(1)-per-window Pearson r
    cum_x = np.zeros(n + 1)
    cum_y = np.zeros(n + 1)
    cum_x2 = np.zeros(n + 1)
    cum_y2 = np.zeros(n + 1)
    cum_xy = np.zeros(n + 1)
    cum_x[1:] = np.cumsum(close)
    cum_y[1:] = np.cumsum(log_vol)
    cum_x2[1:] = np.cumsum(close * close)
    cum_y2[1:] = np.cumsum(log_vol * log_vol)
    cum_xy[1:] = np.cumsum(close * log_vol)

    w = window
    for k in range(w - 1, n):
        s = k - w + 1
        sx = cum_x[k + 1] - cum_x[s]
        sy = cum_y[k + 1] - cum_y[s]
        sx2 = cum_x2[k + 1] - cum_x2[s]
        sy2 = cum_y2[k + 1] - cum_y2[s]
        sxy = cum_xy[k + 1] - cum_xy[s]

        # Pearson: r = (n*Σxy - Σx*Σy) / sqrt((n*Σx² - (Σx)²) * (n*Σy² - (Σy)²))
        num = w * sxy - sx * sy
        denom_x = w * sx2 - sx * sx
        denom_y = w * sy2 - sy * sy

        if denom_x < 1e-30 or denom_y < 1e-30:
            result[k] = 0.0  # constant series → undefined, default 0
        else:
            result[k] = num / np.sqrt(denom_x * denom_y)

    # Clamp to [-1, 1] to handle fp overshoot
    result = np.clip(result, -1.0, 1.0)
    return result


def aroon(
    high: np.ndarray,
    low: np.ndarray,
    window: int = 25,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Aroon Indicator — days since highest high / lowest low.

    Derived from Qlib's ``IdxMax`` / ``IdxMin`` factors (IMAX, IMIN).

    * ``aroon_up > 70``  → strong uptrend.
    * ``aroon_down > 70`` → strong downtrend.

    Qlib formulas::

        IdxMax($high, d) / d   →  aroon_up  = 100 * (1 - IdxMax/d)
        IdxMin($low,  d) / d   →  aroon_down = 100 * (1 - IdxMin/d)

    Parameters
    ----------
    high : np.ndarray
        1-D array of high prices.
    low : np.ndarray
        1-D array of low prices.
    window : int, default 25
        Look-back period.

    Returns
    -------
    (aroon_up, aroon_down, aroon_oscillator) : tuple[np.ndarray, …]
        Each of length ``len(high)``; first ``window - 1`` values are ``nan``.
        ``aroon_oscillator = aroon_up - aroon_down``.

    References
    ----------
    - Qlib Alpha158 — ``IMAX``, ``IMIN`` factors.
    - Investopedia: *Aroon Indicator*
      https://www.investopedia.com/terms/a/aroon.asp
    """
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)

    n = len(high)
    up = np.full(n, np.nan)
    down = np.full(n, np.nan)
    osc = np.full(n, np.nan)

    if n == 0:
        return up, down, osc

    for k in range(window - 1, n):
        s = k - window + 1
        win_h = high[s: k + 1]
        win_l = low[s: k + 1]

        # Days since highest high (0 = today, window-1 = oldest)
        idx_max = int(np.argmax(win_h[::-1]))  # last occurrence → reverse argmax
        idx_max = window - 1 - idx_max          # convert back
        days_since_high = (window - 1) - idx_max

        idx_min = int(np.argmin(win_l[::-1]))
        idx_min = window - 1 - idx_min
        days_since_low = (window - 1) - idx_min

        up[k] = 100.0 * (window - days_since_high) / window
        down[k] = 100.0 * (window - days_since_low) / window

    osc = up - down
    return up, down, osc


def trend_quality(close: np.ndarray, window: int = 20) -> np.ndarray:
    """Trend Quality — a composite of BETA × RSQR.

    Combines trend *direction* (BETA) with trend *clarity* (RSQR)
    into a single actionable score:

    * ``score > 0`` and ``RSQR > 0.5`` → clear uptrend.
    * ``score < 0`` and ``RSQR > 0.5`` → clear downtrend.
    * ``|score| ≈ 0`` → no trend or unclear trend.

    This is a novel combination **not in** Qlib Alpha158.

    Parameters
    ----------
    close : np.ndarray
        1-D array of closing prices.
    window : int, default 20
        Rolling look-back window.

    Returns
    -------
    np.ndarray
        ``beta(close, window) * rsqr(close, window)``;
        first ``window - 1`` values are ``nan``.
    """
    b = beta(close, window)
    r = rsqr(close, window)
    return b * r
