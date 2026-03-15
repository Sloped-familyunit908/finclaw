"""
FinClaw - Price Data Pipeline
Fetches real-time and historical price data from free APIs.
Primary: CoinGecko (free, no key, works globally)
Fallback: Binance (may be restricted in some regions)
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Optional
from ..agents.base import MarketData


COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map common symbols to CoinGecko IDs
SYMBOL_TO_COINGECKO = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "ARB": "arbitrum",
    "OP": "optimism",
}


async def get_current_prices(symbols: list[str]) -> dict[str, dict]:
    """Get current prices for multiple symbols"""
    ids = ",".join(SYMBOL_TO_COINGECKO.get(s, s.lower()) for s in symbols)
    
    async with aiohttp.ClientSession() as session:
        url = f"{COINGECKO_BASE}/simple/price"
        params = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
            "include_market_cap": "true",
        }
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def get_market_data_detailed(symbol: str) -> dict:
    """Get detailed market data for a single asset"""
    coin_id = SYMBOL_TO_COINGECKO.get(symbol, symbol.lower())
    
    async with aiohttp.ClientSession() as session:
        url = f"{COINGECKO_BASE}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def get_historical_prices(symbol: str, days: int = 200) -> list[dict]:
    """Get historical daily prices"""
    coin_id = SYMBOL_TO_COINGECKO.get(symbol, symbol.lower())
    
    async with aiohttp.ClientSession() as session:
        url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": str(days),
            "interval": "daily",
        }
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            
            prices = []
            for i, (ts, price) in enumerate(data.get("prices", [])):
                volume = data["total_volumes"][i][1] if i < len(data.get("total_volumes", [])) else 0
                prices.append({
                    "timestamp": datetime.fromtimestamp(ts / 1000),
                    "close": price,
                    "volume": volume,
                })
            return prices


def compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Compute RSI from closing prices"""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_sma(closes: list[float], period: int) -> Optional[float]:
    """Compute Simple Moving Average"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def compute_ema(closes: list[float], period: int) -> Optional[float]:
    """Compute Exponential Moving Average"""
    if len(closes) < period:
        return None

    multiplier = 2 / (period + 1)
    ema = sum(closes[:period]) / period

    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def compute_macd(closes: list[float]) -> tuple[Optional[float], Optional[float]]:
    """Compute MACD and Signal line"""
    if len(closes) < 26:
        return None, None
    
    ema12 = compute_ema(closes, 12)
    ema26 = compute_ema(closes, 26)

    if ema12 is None or ema26 is None:
        return None, None

    macd = ema12 - ema26
    
    # Compute MACD values for signal line
    macd_values = []
    for i in range(26, len(closes)):
        e12 = compute_ema(closes[:i+1], 12)
        e26 = compute_ema(closes[:i+1], 26)
        if e12 and e26:
            macd_values.append(e12 - e26)
    
    signal = compute_ema(macd_values, 9) if len(macd_values) >= 9 else None
    
    return macd, signal


def compute_bollinger_bands(closes: list[float], period: int = 20, std_dev: float = 2.0):
    """Compute Bollinger Bands"""
    sma = compute_sma(closes, period)
    if sma is None:
        return None, None

    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5

    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)

    return upper, lower


async def build_market_data(symbol: str) -> MarketData:
    """
    Build a complete MarketData object with all technical indicators.
    Uses CoinGecko free API.
    """
    # Fetch current data and historical data in parallel
    detail_task = get_market_data_detailed(symbol)
    history_task = get_historical_prices(symbol, days=210)
    
    detail, history = await asyncio.gather(detail_task, history_task)
    
    # Extract current data
    market = detail.get("market_data", {})
    current_price = market.get("current_price", {}).get("usd", 0)
    
    # Historical closes
    closes = [h["close"] for h in history]
    
    # Get historical reference prices
    price_24h = market.get("current_price", {}).get("usd", current_price)
    change_24h = market.get("price_change_percentage_24h", 0) / 100
    price_24h_ago = current_price / (1 + change_24h) if change_24h != -1 else current_price
    
    price_7d = closes[-8] if len(closes) >= 8 else closes[0] if closes else current_price
    price_30d = closes[-31] if len(closes) >= 31 else closes[0] if closes else current_price
    
    # Compute technical indicators
    rsi = compute_rsi(closes, 14) if len(closes) > 14 else None
    sma_20 = compute_sma(closes, 20)
    sma_50 = compute_sma(closes, 50)
    sma_200 = compute_sma(closes, 200)
    macd, macd_signal = compute_macd(closes)
    bb_upper, bb_lower = compute_bollinger_bands(closes, 20)
    
    return MarketData(
        asset=symbol,
        current_price=current_price,
        price_24h_ago=price_24h_ago,
        price_7d_ago=price_7d,
        price_30d_ago=price_30d,
        volume_24h=market.get("total_volume", {}).get("usd", 0),
        market_cap=market.get("market_cap", {}).get("usd", None),
        high_24h=market.get("high_24h", {}).get("usd", None),
        low_24h=market.get("low_24h", {}).get("usd", None),
        rsi_14=rsi,
        macd=macd,
        macd_signal=macd_signal,
        sma_20=sma_20,
        sma_50=sma_50,
        sma_200=sma_200,
        bollinger_upper=bb_upper,
        bollinger_lower=bb_lower,
    )
