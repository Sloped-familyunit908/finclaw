# Market Filter Validation Report

**Generated:** 2026-03-20

**Index:** sh.000001 (上证指数)
**Period:** 2024-03-01 to 2026-03-20
**Scanner:** cn_scanner v3 (score >= 6)
**Hold:** 1 day (first-day analysis)

## Baseline (No Filter)

| Metric | Value |
|--------|-------|
| Total Trades | 47866 |
| First-Day Loss Rate | 50.0% |
| Avg First-Day Return | 0.165% |
| Win Rate | 50.0% |
| Best Trade | +20.05% |
| Worst Trade | -20.01% |

## Filter Comparison

| Filter Config | Trades | Loss Rate | Δ Loss Rate | Avg Return | Win Rate |
|--------------|--------|-----------|-------------|------------|----------|
| No Filter (baseline) | 47866 | 50.0% | — | 0.165% | 50.0% |
| MA5/20 (default) | 35144 | 51.0% | -0.9pp | 0.149% | 49.0% |
| MA3/10 (aggressive) | 35532 | 51.1% | -1.1pp | 0.133% | 48.9% |
| MA5/10 (tight) | 33521 | 51.4% | -1.4pp | 0.131% | 48.6% |
| MA10/30 (smooth) ⭐ | 35463 | 50.6% | -0.5pp | 0.168% | 49.4% |

## Best Filter: MA10/30 (smooth)

- Loss rate improvement: **-0.5pp**
- Trades filtered out: 12403 (26%)
- This means the filter blocked approximately 26% of trades
  while reducing first-day losses by -0.5 percentage points.

## Methodology

1. Walk-forward simulation over the full data period
2. Each day, run cn_scanner v3 scoring on all stocks with local data
3. When score >= 6 (BUY signal), record entry at close, exit next day close
4. MarketFilter checks index (sh.000001) conditions on the entry day
5. Compare loss rates with and without the market filter

## Conclusion

The market filter did not show significant improvement in this dataset.
Consider adjusting parameters or using a different index/signal combination.
