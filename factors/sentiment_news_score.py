"""
Factor: sentiment_news_score
Description: News sentiment score from keyword-based analysis
Category: sentiment
"""

FACTOR_NAME = "sentiment_news_score"
FACTOR_DESC = "News sentiment score — keyword-based analysis of crypto/stock news headlines"
FACTOR_CATEGORY = "sentiment"


def compute(closes, highs, lows, volumes, idx):
    """
    Return the current news sentiment score (0-1).

    Reads from the daily sentiment cache (data/sentiment/).
    Falls back to 0.5 (neutral) if no cached data is available.
    """
    try:
        from src.sentiment.news_sentiment import get_current_sentiment
        score = get_current_sentiment("overall")
        return max(0.0, min(1.0, float(score)))
    except Exception:
        return 0.5
