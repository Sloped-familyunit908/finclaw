# FinClaw ML - Machine Learning Integration
"""Machine learning models, feature engineering, and alpha generation."""

from .features import FeatureEngine
from .models import LinearRegression, MAPredictor, RegimeClassifier, EnsembleModel
from .sentiment import SimpleSentiment
from .alpha import AlphaModel, Signal
from .pipeline import WalkForwardPipeline
from .ensemble import EnsembleModel as AdvancedEnsembleModel
from .feature_store import FeatureStore

__all__ = [
    "FeatureEngine",
    "LinearRegression",
    "MAPredictor",
    "RegimeClassifier",
    "EnsembleModel",
    "SimpleSentiment",
    "AlphaModel",
    "Signal",
    "WalkForwardPipeline",
    "AdvancedEnsembleModel",
    "FeatureStore",
]
