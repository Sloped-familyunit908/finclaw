"""
Crypto Sentiment Analysis
Fear & Greed Index, social volume, and funding-based sentiment signals.
"""

import hashlib
from dataclasses import dataclass


class CryptoSentiment:
    """Crypto market sentiment analysis from multiple sources."""

    def __init__(self, seed: int = 42):
        self._seed = seed

    def _deterministic_hash(self, key: str) -> str:
        return hashlib.sha256(f"{self._seed}:{key}".encode()).hexdigest()

    def _pseudo_random(self, key: str, idx: int = 0) -> float:
        h = self._deterministic_hash(f"{key}:{idx}")
        return int(h[:8], 16) / 0xFFFFFFFF

    def fear_greed_index(self) -> dict:
        """Get the current Crypto Fear & Greed Index (Alternative.me style).

        Returns:
            dict with value (0-100), classification, timestamp, trend.
        """
        r = self._pseudo_random("fgi")
        value = int(r * 100)

        if value <= 20:
            classification = 'Extreme Fear'
        elif value <= 40:
            classification = 'Fear'
        elif value <= 60:
            classification = 'Neutral'
        elif value <= 80:
            classification = 'Greed'
        else:
            classification = 'Extreme Greed'

        # Yesterday's value for trend
        r_prev = self._pseudo_random("fgi_prev")
        prev_value = int(r_prev * 100)
        trend = 'improving' if value > prev_value else 'declining' if value < prev_value else 'stable'

        return {
            'value': value,
            'classification': classification,
            'previous_value': prev_value,
            'trend': trend,
            'timestamp': 1700000000,
        }

    def social_volume(self, token: str) -> dict:
        """Get social media volume and sentiment for a token.

        Args:
            token: token symbol (e.g. 'BTC', 'ETH', 'SOL').

        Returns:
            dict with mentions_24h, mentions_7d, change_pct, sentiment_score, dominant_sentiment.
        """
        token = token.upper()
        r1 = self._pseudo_random(f"social:{token}", 0)
        r2 = self._pseudo_random(f"social:{token}", 1)
        r3 = self._pseudo_random(f"social:{token}", 2)

        # Base mentions scale with token popularity
        base_mentions = {'BTC': 50000, 'ETH': 35000, 'SOL': 20000, 'DOGE': 15000}
        base = base_mentions.get(token, 5000)

        mentions_24h = int(base * (0.5 + r1))
        mentions_7d = mentions_24h * 7 + int(r2 * base * 2)
        change_pct = round((r1 - 0.5) * 60, 2)  # -30% to +30%

        # Sentiment score -1 to 1
        sentiment_score = round(r3 * 2 - 1, 3)
        if sentiment_score > 0.3:
            dominant = 'bullish'
        elif sentiment_score < -0.3:
            dominant = 'bearish'
        else:
            dominant = 'neutral'

        return {
            'token': token,
            'mentions_24h': mentions_24h,
            'mentions_7d': mentions_7d,
            'change_pct': change_pct,
            'sentiment_score': sentiment_score,
            'dominant_sentiment': dominant,
        }

    def funding_sentiment(self, symbol: str) -> str:
        """Derive market sentiment from funding rates.

        Args:
            symbol: trading pair (e.g. 'BTC/USDT').

        Returns:
            'bullish', 'bearish', or 'neutral'.
        """
        symbol = symbol.upper()
        r = self._pseudo_random(f"fsent:{symbol}")

        # Simulate funding rate
        rate = (r - 0.5) * 0.002

        if rate > 0.0003:
            return 'bullish'  # longs paying shorts, market is overleveraged long
        elif rate < -0.0003:
            return 'bearish'
        else:
            return 'neutral'

    def composite_sentiment(self, token: str) -> dict:
        """Get a composite sentiment score combining multiple signals.

        Args:
            token: token symbol.

        Returns:
            dict with overall score, components, and recommendation.
        """
        fgi = self.fear_greed_index()
        social = self.social_volume(token)
        funding = self.funding_sentiment(f"{token}/USDT")

        # Weight the signals
        fgi_normalized = (fgi['value'] - 50) / 50  # -1 to 1
        social_score = social['sentiment_score']
        funding_score = {'bullish': 0.5, 'bearish': -0.5, 'neutral': 0.0}[funding]

        composite = round(fgi_normalized * 0.3 + social_score * 0.4 + funding_score * 0.3, 3)

        if composite > 0.25:
            recommendation = 'bullish'
        elif composite < -0.25:
            recommendation = 'bearish'
        else:
            recommendation = 'neutral'

        return {
            'token': token,
            'composite_score': composite,
            'recommendation': recommendation,
            'components': {
                'fear_greed': fgi['value'],
                'social_sentiment': social_score,
                'funding_sentiment': funding,
            },
        }
