"""
Multi-Asset Data Fetcher
========================
Extend beyond stocks to crypto, forex, commodities, and indices.
Uses yfinance (free, no API key).
"""

from __future__ import annotations

from typing import Optional

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

try:
    import pandas as pd
    HAS_PD = True
except ImportError:
    HAS_PD = False


# Symbol mappings for yfinance
CRYPTO_SYMBOLS = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
    "BNB": "BNB-USD", "XRP": "XRP-USD", "ADA": "ADA-USD",
    "DOGE": "DOGE-USD", "AVAX": "AVAX-USD", "DOT": "DOT-USD",
    "MATIC": "MATIC-USD", "LINK": "LINK-USD", "UNI": "UNI-USD",
    "ATOM": "ATOM-USD", "LTC": "LTC-USD",
}

FOREX_SYMBOLS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X", "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X", "USDCNY": "USDCNY=X", "USDHKD": "USDHKD=X",
}

COMMODITY_SYMBOLS = {
    "gold": "GC=F", "silver": "SI=F", "oil": "CL=F", "crude": "CL=F",
    "natural_gas": "NG=F", "copper": "HG=F", "platinum": "PL=F",
    "palladium": "PA=F", "corn": "ZC=F", "wheat": "ZW=F",
    "soybean": "ZS=F", "cotton": "CT=F",
}

INDEX_SYMBOLS = {
    "SP500": "^GSPC", "SPX": "^GSPC", "NASDAQ": "^IXIC", "NDX": "^NDX",
    "DOW": "^DJI", "DJIA": "^DJI", "RUSSELL": "^RUT", "VIX": "^VIX",
    "FTSE": "^FTSE", "DAX": "^GDAXI", "NIKKEI": "^N225",
    "HSI": "^HSI", "SSE": "000001.SS", "KOSPI": "^KS11",
}


def _fetch_yf(symbol: str, period: str = "1y") -> "pd.DataFrame":
    """Fetch data via yfinance, return DataFrame with standard columns."""
    if not HAS_YF:
        raise ImportError("yfinance is required: pip install yfinance")

    import logging
    import warnings
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

    if df.empty:
        raise ValueError(f"No data returned for {symbol}")

    # Normalize columns
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = 0.0

    return df[["open", "high", "low", "close", "volume"]]


class MultiAssetFetcher:
    """
    Multi-asset data fetcher supporting crypto, forex, commodities, and indices.

    Usage:
        fetcher = MultiAssetFetcher()
        btc = fetcher.get_crypto("BTC")
        eur = fetcher.get_forex("EURUSD")
        gold = fetcher.get_commodity("gold")
        sp500 = fetcher.get_index("SP500")
    """

    def __init__(self, period: str = "1y"):
        self.period = period

    def get_crypto(self, symbol: str, period: Optional[str] = None) -> "pd.DataFrame":
        """
        Get cryptocurrency OHLCV data.
        symbol: e.g. "BTC", "ETH", "SOL" or full yfinance symbol "BTC-USD"
        """
        yf_sym = CRYPTO_SYMBOLS.get(symbol.upper(), f"{symbol.upper()}-USD")
        return _fetch_yf(yf_sym, period or self.period)

    def get_forex(self, pair: str, period: Optional[str] = None) -> "pd.DataFrame":
        """
        Get forex pair OHLCV data.
        pair: e.g. "EURUSD", "GBPUSD", "USDJPY"
        """
        yf_sym = FOREX_SYMBOLS.get(pair.upper(), f"{pair.upper()}=X")
        return _fetch_yf(yf_sym, period or self.period)

    def get_commodity(self, name: str, period: Optional[str] = None) -> "pd.DataFrame":
        """
        Get commodity futures OHLCV data.
        name: e.g. "gold", "silver", "oil", "copper"
        """
        yf_sym = COMMODITY_SYMBOLS.get(name.lower())
        if yf_sym is None:
            raise ValueError(
                f"Unknown commodity '{name}'. Available: {', '.join(COMMODITY_SYMBOLS.keys())}"
            )
        return _fetch_yf(yf_sym, period or self.period)

    def get_index(self, name: str, period: Optional[str] = None) -> "pd.DataFrame":
        """
        Get index OHLCV data.
        name: e.g. "SP500", "NASDAQ", "DOW", "VIX"
        """
        yf_sym = INDEX_SYMBOLS.get(name.upper())
        if yf_sym is None:
            raise ValueError(
                f"Unknown index '{name}'. Available: {', '.join(INDEX_SYMBOLS.keys())}"
            )
        return _fetch_yf(yf_sym, period or self.period)

    def get_any(self, symbol: str, asset_type: str = "stock", period: Optional[str] = None) -> "pd.DataFrame":
        """
        Universal fetcher — routes to the right method by asset_type.
        asset_type: "stock", "crypto", "forex", "commodity", "index"
        """
        dispatch = {
            "crypto": self.get_crypto,
            "forex": self.get_forex,
            "commodity": self.get_commodity,
            "index": self.get_index,
            "stock": lambda s, p=None: _fetch_yf(s, p or self.period),
        }
        fn = dispatch.get(asset_type.lower())
        if fn is None:
            raise ValueError(f"Unknown asset_type '{asset_type}'")
        return fn(symbol, period or self.period)

    @staticmethod
    def list_available() -> dict[str, list[str]]:
        """List all available symbols by asset type."""
        return {
            "crypto": sorted(CRYPTO_SYMBOLS.keys()),
            "forex": sorted(FOREX_SYMBOLS.keys()),
            "commodity": sorted(COMMODITY_SYMBOLS.keys()),
            "index": sorted(INDEX_SYMBOLS.keys()),
        }
