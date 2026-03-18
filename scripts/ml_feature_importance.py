#!/usr/bin/env python3
"""
ML Feature Importance Analyzer
===============================
Train the ML stock scorer and display which features matter most.

Usage:
    python scripts/ml_feature_importance.py [--version v1|v2] [--bars 300] [--seed 42]
"""
from __future__ import annotations

import argparse
import sys
import os

import numpy as np

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_synthetic_data(n_bars: int = 500, seed: int = 42):
    """Generate realistic synthetic OHLCV data for testing."""
    rng = np.random.RandomState(seed)
    # Random walk with trend and mean-reversion
    returns = rng.randn(n_bars) * 0.02  # 2% daily vol
    close = 100 * np.exp(np.cumsum(returns))
    # Realistic OHLC
    high = close * (1 + np.abs(rng.randn(n_bars)) * 0.01)
    low = close * (1 - np.abs(rng.randn(n_bars)) * 0.01)
    open_ = np.copy(close)
    open_[1:] = close[:-1] * (1 + rng.randn(n_bars - 1) * 0.005)
    volume = (rng.lognormal(10, 1, n_bars) * 1000).astype(np.float64)
    return open_, high, low, close, volume


def main():
    parser = argparse.ArgumentParser(description="ML Feature Importance Analyzer")
    parser.add_argument("--version", default="v2", choices=["v1", "v2"],
                        help="ML version (default: v2)")
    parser.add_argument("--bars", type=int, default=500,
                        help="Number of synthetic bars (default: 500)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--train-bars", type=int, default=None,
                        help="Training window size (default: 120 for v1, 250 for v2)")
    parser.add_argument("--predict-bars", type=int, default=None,
                        help="Prediction window size (default: 20 for v1, 5 for v2)")
    args = parser.parse_args()

    from src.cn_ml_scorer import (
        MLStockScorer, compute_features_series, get_feature_names,
        get_num_features,
    )

    print(f"\n{'=' * 60}")
    print(f"  ML Feature Importance Analysis")
    print(f"  Version: {args.version} | Bars: {args.bars} | Seed: {args.seed}")
    print(f"{'=' * 60}\n")

    # Generate data
    print("  [1/4] Generating synthetic OHLCV data...")
    open_, high, low, close, volume = generate_synthetic_data(args.bars, args.seed)
    print(f"         {args.bars} bars generated, price range: "
          f"${close.min():.2f} - ${close.max():.2f}")

    # Compute features
    print(f"  [2/4] Computing {args.version} features...")
    features = compute_features_series(close, volume, open_, high, low, version=args.version)
    if features is None:
        print("  ERROR: Failed to compute features (data too short)")
        return 1
    n_features = features.shape[1]
    expected = get_num_features(args.version)
    print(f"         {n_features} features computed (expected: {expected})")
    assert n_features == expected, f"Feature count mismatch: {n_features} != {expected}"

    # Train with walk-forward
    train_bars = args.train_bars or (250 if args.version == "v2" else 120)
    predict_bars = args.predict_bars or (5 if args.version == "v2" else 20)
    print(f"  [3/4] Walk-forward training (train={train_bars}, predict={predict_bars})...")

    scorer = MLStockScorer(
        train_bars=train_bars,
        predict_bars=predict_bars,
        forward_days=5,
        version=args.version,
        expanding_window=(args.version == "v2"),
    )
    probs = scorer.train_and_predict(
        features, close,
        high=high if args.version == "v2" else None,
        low=low if args.version == "v2" else None,
        verbose=True,
    )

    valid_probs = probs[~np.isnan(probs)]
    print(f"         {len(valid_probs)} predictions generated "
          f"(avg prob: {np.mean(valid_probs):.3f})")

    # Feature importances
    print(f"  [4/4] Extracting feature importances...\n")
    importances = scorer.get_feature_importances()
    if importances is None:
        print("  WARNING: No feature importances available")
        return 0

    # Sort by importance
    sorted_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    print(f"  {'Rank':<6}{'Feature':<25}{'Importance':<12}{'Bar'}")
    print(f"  {'-' * 55}")
    max_imp = sorted_features[0][1] if sorted_features else 1.0
    for rank, (name, imp) in enumerate(sorted_features, 1):
        bar_len = int(imp / max_imp * 30) if max_imp > 0 else 0
        bar = '█' * bar_len
        print(f"  {rank:<6}{name:<25}{imp:<12.4f}{bar}")

    print(f"\n  Total features: {len(sorted_features)}")
    top_5_sum = sum(imp for _, imp in sorted_features[:5])
    total_sum = sum(imp for _, imp in sorted_features)
    if total_sum > 0:
        print(f"  Top-5 features explain {top_5_sum / total_sum * 100:.1f}% of importance")

    print(f"\n{'=' * 60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
