"""
FinClaw Example: ML Pipeline
==============================
Feature engineering → model training → alpha signal generation.
"""

import numpy as np
from src.ml import FeatureEngine, AlphaModel, WalkForwardPipeline

# --- Synthetic data ---
np.random.seed(42)
n = 500
prices = 100 * np.cumprod(1 + np.random.normal(0.0003, 0.015, n))
volumes = np.random.uniform(1e6, 5e6, n)

# --- Feature engineering ---
fe = FeatureEngine()
X = fe.build(prices, volumes)
print(f"Feature matrix shape: {X.shape}")

# --- Alpha model ---
alpha = AlphaModel()
# Simple train/test split
split = int(len(X) * 0.7)
alpha.fit(X[:split], prices[1:split + 1])  # predict next-day price
signals = alpha.predict(X[split:])
print(f"\nGenerated {len(signals)} signals")
for s in signals[:5]:
    print(f"  {s}")

# --- Walk-Forward Pipeline ---
pipeline = WalkForwardPipeline(model=alpha, feature_engine=fe, n_splits=3)
results = pipeline.run(prices, volumes)
print(f"\nWalk-forward pipeline results: {results}")
