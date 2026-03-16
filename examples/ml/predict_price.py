"""
FinClaw: ML Price Prediction
==============================
Use machine learning to predict next-day price direction.

Prerequisites:
    pip install finclaw-ai[ml]  # Installs scikit-learn, etc.

Usage:
    python predict_price.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.ml import PricePredictor

fc = FinClaw()

# Create a predictor with built-in feature engineering
predictor = PricePredictor(
    symbol="AAPL",
    features=[
        "sma_10", "sma_30", "rsi_14", "macd",
        "bollinger_band_width", "volume_sma_ratio",
        "atr_14", "obv", "day_of_week",
    ],
    target="direction_1d",  # Predict next-day up/down
    model="random_forest",  # Options: random_forest, xgboost, lightgbm
)

# Train on historical data
train_result = predictor.train(
    start="2020-01-01",
    end="2024-06-30",
    test_split=0.2,
)

print("=== Model Training Results ===")
print(f"Accuracy:        {train_result['accuracy']:.1f}%")
print(f"Precision:       {train_result['precision']:.1f}%")
print(f"Recall:          {train_result['recall']:.1f}%")
print(f"F1 Score:        {train_result['f1']:.3f}")

# Show feature importance
print(f"\n=== Feature Importance ===")
for feat, imp in train_result["feature_importance"][:5]:
    print(f"  {feat:<25} {imp:.3f}")

# Make a prediction for tomorrow
prediction = predictor.predict()
print(f"\n=== Tomorrow's Prediction ===")
print(f"Direction:       {'📈 UP' if prediction['direction'] == 'up' else '📉 DOWN'}")
print(f"Confidence:      {prediction['confidence']:.1f}%")
print(f"Expected Move:   {prediction['expected_move']:+.2f}%")
