# FinClaw ML - Machine Learning Integration
"""Machine learning models, feature engineering, and alpha generation."""

from .features import FeatureEngine
from .models import (
    LinearRegression, MAPredictor, RegimeClassifier, EnsembleModel,
    DecisionTreeClassifier, RandomForestClassifier, GradientBooster,
)
from .walk_forward import WalkForwardValidator
from .sentiment import SimpleSentiment
from .alpha import AlphaModel, Signal
from .pipeline import WalkForwardPipeline
from .ensemble import EnsembleModel as AdvancedEnsembleModel
from .feature_store import FeatureStore
from .feature_pipeline import FeaturePipeline
from .model_selection import ModelSelector
from .prediction_tracker import PredictionTracker
from .data_splitter import FinancialDataSplitter

__all__ = [
    "FeatureEngine",
    "LinearRegression",
    "MAPredictor",
    "RegimeClassifier",
    "EnsembleModel",
    "DecisionTreeClassifier",
    "RandomForestClassifier",
    "GradientBooster",
    "WalkForwardValidator",
    "SimpleSentiment",
    "AlphaModel",
    "Signal",
    "WalkForwardPipeline",
    "AdvancedEnsembleModel",
    "FeatureStore",
    "FeaturePipeline",
    "ModelSelector",
    "PredictionTracker",
    "FinancialDataSplitter",
]
