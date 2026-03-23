# Factor Gap Analysis: Finclaw vs Qlib Alpha158

## Overview

Qlib Alpha158 is Microsoft's standard feature set for stock prediction, containing **158 features** across:
- **9 KBAR features** (candlestick ratios)
- **4 price features** (normalized OHLCV)
- **145 rolling features** (29 categories × 5 windows: 5d, 10d, 20d, 30d, 60d)

Our factor library has **~175 custom factor files** plus **~40 built-in weight-based indicators** in `auto_evolve.py`. Many of our factors are more sophisticated than Alpha158's (e.g., candlestick patterns, institutional flow proxies, regime detection), but we have gaps in the systematic rolling-window factor coverage that Alpha158 provides.

## Coverage Matrix

| Alpha158 Category | Description | Our Coverage | Status |
|---|---|---|---|
| **KMID** | `(close-open)/open` | No exact equivalent | ❌ MISSING |
| **KLEN** | `(high-low)/open` | `intraday_range.py` (partial) | ⚠️ PARTIAL |
| **KMID2** | `(close-open)/(high-low)` | No equivalent | ❌ MISSING |
| **KUP** | `(high-max(open,close))/open` | `upper_shadow_ratio.py` (partial) | ⚠️ PARTIAL |
| **KUP2** | `(high-max(open,close))/(high-low)` | No equivalent | ❌ MISSING |
| **KLOW** | `(min(open,close)-low)/open` | `lower_shadow_ratio.py` (partial) | ⚠️ PARTIAL |
| **KLOW2** | `(min(open,close)-low)/(high-low)` | No equivalent | ❌ MISSING |
| **KSFT** | `(2*close-high-low)/open` | No equivalent | ❌ MISSING |
| **KSFT2** | `(2*close-high-low)/(high-low)` | No equivalent | ❌ MISSING |
| **ROC** | Rate of change (5/10/20/30/60d) | `momentum_3d`, `momentum_10d`, `w_roc` | ⚠️ PARTIAL (missing 20/30/60d) |
| **MA** | Moving average ratio (5/10/20/30/60d) | `ma5_distance`, `ma20_distance` | ⚠️ PARTIAL (missing ratio form) |
| **STD** | Std deviation ratio (5/10/20/30/60d) | `realized_vol_10d`, `realized_vol_30d` | ⚠️ PARTIAL |
| **BETA** | Rolling slope/beta (5/10/20/30/60d) | `w_beta` in auto_evolve | ⚠️ PARTIAL (not factor files) |
| **RSQR** | Rolling R-squared (5/10/20/30/60d) | `w_r_squared` in auto_evolve | ⚠️ PARTIAL |
| **RESI** | Rolling residual (5/10/20/30/60d) | `w_residual` in auto_evolve | ⚠️ PARTIAL |
| **MAX** | Rolling max(high)/close (5/10/20/30/60d) | `new_high_20d`, `new_high_60d` | ⚠️ PARTIAL (different formulation) |
| **MIN** | Rolling min(low)/close (5/10/20/30/60d) | `new_low_20d`, `new_low_60d` | ⚠️ PARTIAL |
| **QTLU** | 80th percentile ratio (5/10/20/30/60d) | `w_quantile_upper` in auto_evolve | ⚠️ PARTIAL |
| **QTLD** | 20th percentile ratio (5/10/20/30/60d) | `w_quantile_lower` in auto_evolve | ⚠️ PARTIAL |
| **RANK** | Rolling rank/percentile (5/10/20/30/60d) | `cumulative_return_rank` (different) | ❌ MISSING |
| **RSV** | Relative Strength Value (5/10/20/30/60d) | `closing_strength` (5d avg only) | ⚠️ PARTIAL |
| **IMAX** | Index of max in window (5/10/20/30/60d) | `w_aroon` in auto_evolve (partial) | ⚠️ PARTIAL |
| **IMIN** | Index of min in window (5/10/20/30/60d) | `w_aroon` in auto_evolve (partial) | ⚠️ PARTIAL |
| **IMXD** | Distance between max/min indices | No equivalent | ❌ MISSING |
| **CORR** | Price-volume correlation (5/10/20/30/60d) | `alpha_volume_return_corr` (20d only) | ⚠️ PARTIAL |
| **CORD** | Return-volume correlation delta | No equivalent | ❌ MISSING |
| **CNTP** | Positive day count ratio (5/10/20/30/60d) | `positive_days_ratio_10d/30d` | ⚠️ PARTIAL |
| **CNTN** | Negative day count ratio (5/10/20/30/60d) | No exact equivalent | ❌ MISSING |
| **CNTD** | Count difference (CNTP - CNTN) | No equivalent | ❌ MISSING |
| **SUMP** | Sum positive returns ratio | No equivalent | ❌ MISSING |
| **SUMN** | Sum negative returns ratio | No equivalent | ❌ MISSING |
| **SUMD** | Sum returns difference ratio | No equivalent | ❌ MISSING |
| **VMA** | Volume moving average ratio (5/10/20/30/60d) | `volume_trend` (different) | ❌ MISSING |
| **VSTD** | Volume std deviation ratio (5/10/20/30/60d) | No equivalent | ❌ MISSING |
| **WVMA** | Weighted volume-price volatility | No equivalent | ❌ MISSING |
| **VSUMP** | Volume sum positive ratio | No equivalent | ❌ MISSING |
| **VSUMN** | Volume sum negative ratio | No equivalent | ❌ MISSING |
| **VSUMD** | Volume sum difference ratio | No equivalent | ❌ MISSING |

## Missing Factors — Priority Ranking

### 🔴 High Priority (Unique signal, no partial coverage)

| # | Factor | Why Important |
|---|---|---|
| 1 | **KMID** `(close-open)/open` | Core candlestick feature, captures intraday direction strength |
| 2 | **KSFT** `(2*close-high-low)/open` | Price shift within candle, reveals buying/selling pressure |
| 3 | **SUMP/SUMN/SUMD** | RSI-like decomposition of gains vs losses — fundamental momentum signal |
| 4 | **CNTD** | Net positive vs negative day count — simple but powerful momentum |
| 5 | **CORD** | Return-volume change correlation — detects smart money activity |
| 6 | **VMA** | Volume mean reversion — key for volume regime detection |
| 7 | **VSTD** | Volume volatility — predicts breakouts and institutional activity |
| 8 | **WVMA** | Volume-weighted price change volatility — combines two key dimensions |
| 9 | **IMXD** | Time distance between extremes — momentum/reversal timing signal |
| 10 | **RANK** | Rolling price percentile — Qlib's key relative-strength measure |

### 🟡 Medium Priority (Have partial coverage, need Qlib-compatible formulation)

| # | Factor | Why Important |
|---|---|---|
| 11 | **KMID2** `(close-open)/(high-low)` | Candle body relative to range — conviction measure |
| 12 | **KUP2/KLOW2** | Shadow ratios normalized by range |
| 13 | **KSFT2** | Shift normalized by range |
| 14 | **CNTN** | Negative day count (complement of CNTP) |
| 15 | **VSUMP/VSUMN/VSUMD** | Volume-RSI decomposition |

### 🟢 Lower Priority (Have weighted indicators, just need factor files)

| # | Factor | Notes |
|---|---|---|
| 16+ | Multi-window BETA/RSQR/RESI | Already in auto_evolve weights |
| 16+ | Multi-window QTLU/QTLD | Already in auto_evolve weights |
| 16+ | Multi-window IMAX/IMIN | Already in auto_evolve as Aroon |

## Summary

- **Total Alpha158 categories:** 29 rolling + 9 KBAR = 38 conceptual categories
- **Fully covered:** ~5 (ROC partial, MA partial, STD partial, CORR partial, CNTP partial)
- **Partially covered:** ~15 (have weights or different formulations)
- **Completely missing:** ~18 categories
- **Estimated missing factor-level features:** ~90 out of 158

## Recommendation

Implement the top 10 missing factors from the High Priority list. These add entirely new signal types that our library doesn't cover at all, and they are well-proven in Qlib's research pipeline.
