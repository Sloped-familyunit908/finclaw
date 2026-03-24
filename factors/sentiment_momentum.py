"""
Factor: sentiment_momentum
Description: News sentiment change trend — is sentiment improving or worsening
Category: sentiment
"""

FACTOR_NAME = "sentiment_momentum"
FACTOR_DESC = "Sentiment momentum — measures whether news sentiment is improving or deteriorating over recent days"
FACTOR_CATEGORY = "sentiment"


def compute(closes, highs, lows, volumes, idx):
    """
    Return the sentiment momentum score (0-1).

    > 0.5 means sentiment is improving (bullish signal)
    < 0.5 means sentiment is worsening (bearish signal)
    = 0.5 means stable or no data

    Reads from the daily sentiment cache history (data/sentiment/).
    Falls back to 0.5 (neutral) if no cached data is available.
    """
    try:
        from src.sentiment.news_sentiment import get_sentiment_momentum
        score = get_sentiment_momentum("overall", days=7)
        return max(0.0, min(1.0, float(score)))
    except Exception:
        return 0.5
