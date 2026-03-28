"""
FinClaw Crypto Live Runner
============================
Live/dry-run trading runner for crypto markets.

Modes:
  - dry_run (default): fetches real prices, simulates trades with virtual balance.
  - live: places real orders via ccxt (requires API keys).

Safety first — dry-run by default, multiple risk controls, emergency stop file.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("finclaw.crypto.live_runner")

# ccxt is optional; guard import
try:
    import ccxt  # type: ignore
    HAS_CCXT = True
except ImportError:
    ccxt = None  # type: ignore
    HAS_CCXT = False

from .telegram_notifier import TelegramNotifier

# Import full evolution scoring engine (42+ factors)
from src.evolution.auto_evolve import (
    score_stock, StrategyDNA,
    compute_rsi, compute_linear_regression, compute_volume_ratio,
    compute_macd, compute_bollinger_bands, compute_kdj,
    compute_obv_trend, compute_ma_alignment,
    compute_atr, compute_roc, compute_williams_r, compute_cci,
    compute_mfi, compute_donchian_position, compute_aroon,
    compute_price_volume_corr,
    compute_candle_patterns, compute_support_resistance,
    compute_volume_profile,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_INITIAL_BALANCE = 10_000.0  # USDT
DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_MAX_POSITION_SIZE_PCT = 20.0   # was 10.0 — allow bigger positions for crypto
DEFAULT_MAX_EXPOSURE_PCT = 90.0         # was 50.0 — use most of the capital
DEFAULT_DAILY_LOSS_LIMIT_PCT = -5.0
STOP_FILE_NAME = "STOP_TRADING"
DEFAULT_DNA_PATH = "evolution_results/best_ever.json"
DEFAULT_TRADE_LOG_PATH = "data/crypto/live_trades.json"


# ---------------------------------------------------------------------------
# Position data
# ---------------------------------------------------------------------------

class Position:
    """Represents a single open position."""

    __slots__ = ("symbol", "entry_price", "qty", "entry_time", "side")

    def __init__(self, symbol: str, entry_price: float, qty: float, entry_time: str, side: str = "long"):
        self.symbol = symbol
        self.entry_price = entry_price
        self.qty = qty
        self.entry_time = entry_time
        self.side = side

    def unrealised_pnl(self, current_price: float) -> float:
        if self.side == "long":
            return (current_price - self.entry_price) * self.qty
        return (self.entry_price - current_price) * self.qty

    def unrealised_pnl_pct(self, current_price: float) -> float:
        cost = self.entry_price * self.qty
        if cost == 0:
            return 0.0
        return (self.unrealised_pnl(current_price) / cost) * 100

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "qty": self.qty,
            "entry_time": self.entry_time,
            "side": self.side,
        }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

class CryptoLiveRunner:
    """Live trading runner for crypto — dry-run or live mode."""

    def __init__(
        self,
        exchange: str = "binance",
        mode: str = "dry_run",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        symbols: Optional[list[str]] = None,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        initial_balance: float = DEFAULT_INITIAL_BALANCE,
        interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
        max_position_size_pct: float = DEFAULT_MAX_POSITION_SIZE_PCT,
        max_exposure_pct: float = DEFAULT_MAX_EXPOSURE_PCT,
        daily_loss_limit_pct: float = DEFAULT_DAILY_LOSS_LIMIT_PCT,
        dna_path: str = DEFAULT_DNA_PATH,
        trade_log_path: str = DEFAULT_TRADE_LOG_PATH,
        project_root: Optional[str] = None,
    ):
        self.exchange_id = exchange
        self.mode = mode
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbols = symbols or ["BTC/USDT"]
        self.interval_minutes = interval_minutes

        # Risk params
        self.max_position_size_pct = max_position_size_pct
        self.max_exposure_pct = max_exposure_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct

        # Paths
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.dna_path = self.project_root / dna_path
        self.trade_log_path = self.project_root / trade_log_path
        self.stop_file = self.project_root / STOP_FILE_NAME

        # Portfolio state
        self.cash: float = initial_balance
        self.initial_balance = initial_balance
        self.positions: dict[str, Position] = {}  # symbol -> Position
        self.trade_log: list[dict] = []
        self.daily_pnl: float = 0.0
        self.daily_start_value: float = initial_balance
        self._day_date: Optional[str] = None

        # DNS / strategy config
        self.dna: dict[str, Any] = {}
        self._cli_overrides: dict[str, Any] = {}  # CLI args always win over DNA

        # Exchange connection (lazy)
        self._exchange: Any = None

        # Telegram notifier
        self.notifier: Optional[TelegramNotifier] = None
        if telegram_token and telegram_chat_id:
            self.notifier = TelegramNotifier(telegram_token, telegram_chat_id)

        # Control
        self._running = False
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_exchange(self) -> Any:
        """Create ccxt exchange instance."""
        if not HAS_CCXT:
            raise ImportError(
                "ccxt is required. Install with: pip install ccxt"
            )

        exchange_class = getattr(ccxt, self.exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unsupported exchange: {self.exchange_id}")

        config: dict[str, Any] = {"enableRateLimit": True}
        if self.api_key:
            config["apiKey"] = self.api_key
        if self.api_secret:
            config["secret"] = self.api_secret

        return exchange_class(config)

    def load_dna(self) -> dict[str, Any]:
        """Load evolution DNA from best_ever.json."""
        if not self.dna_path.exists():
            logger.warning("DNA file not found: %s — using defaults", self.dna_path)
            self.dna = self._default_dna()
            self.dna.update(self._cli_overrides)
            return self.dna

        try:
            with open(self.dna_path, "r") as f:
                data = json.load(f)
            self.dna = data.get("dna", data)
            logger.info("Loaded DNA from %s", self.dna_path)
        except Exception as exc:
            logger.error("Failed to load DNA: %s", exc)
            self.dna = self._default_dna()

        # Crypto: allow more positions than DNA default (which was optimized for fewer coins)
        if self.dna.get("max_positions", 2) < 5:
            self.dna["max_positions"] = max(5, len(self.symbols) // 3)
            logger.info("Adjusted max_positions to %d for %d symbols", self.dna["max_positions"], len(self.symbols))

        # CLI overrides always win
        self.dna.update(self._cli_overrides)
        return self.dna

    def set_cli_overrides(self, overrides: dict[str, Any]) -> None:
        """Set CLI overrides that persist across load_dna() calls."""
        self._cli_overrides.update(overrides)
        self.dna.update(overrides)

    @staticmethod
    def _default_dna() -> dict[str, Any]:
        return {
            "min_score": 5,
            "rsi_buy_threshold": 30.0,
            "rsi_sell_threshold": 70.0,
            "stop_loss_pct": 5.0,
            "take_profit_pct": 10.0,
            "max_positions": 3,
        }

    # ------------------------------------------------------------------
    # Price fetching
    # ------------------------------------------------------------------

    def fetch_price(self, symbol: str) -> Optional[float]:
        """Fetch the latest price for *symbol* from the exchange."""
        try:
            if self._exchange is None:
                self._exchange = self._init_exchange()
            ticker = self._exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception as exc:
            logger.error("Failed to fetch price for %s: %s", symbol, exc)
            return None

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> list[list]:
        """Fetch OHLCV candles."""
        try:
            if self._exchange is None:
                self._exchange = self._init_exchange()
            return self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as exc:
            logger.error("Failed to fetch OHLCV for %s: %s", symbol, exc)
            return []

    # ------------------------------------------------------------------
    # Signal scoring — full evolution engine (42+ factors)
    # ------------------------------------------------------------------

    def _build_indicators(self, ohlcv: list[list]) -> dict:
        """Build the full indicators dict that score_stock() expects.

        Args:
            ohlcv: list of [timestamp, open, high, low, close, volume]

        Returns:
            Dict with all pre-computed indicator arrays keyed as score_stock expects.
        """
        opens = [c[1] for c in ohlcv]
        highs = [c[2] for c in ohlcv]
        lows = [c[3] for c in ohlcv]
        closes = [c[4] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]

        # Ensure consistent length
        min_len = min(len(opens), len(highs), len(lows), len(closes), len(volumes))
        opens = opens[:min_len]
        highs = highs[:min_len]
        lows = lows[:min_len]
        closes = closes[:min_len]
        volumes = volumes[:min_len]

        # Core indicators
        rsi_arr = compute_rsi(closes)
        r2_arr, slope_arr = compute_linear_regression(closes)
        vol_ratio_arr = compute_volume_ratio(volumes)

        # v2 indicators
        macd_line, macd_signal, macd_hist = compute_macd(closes)
        bb_upper, bb_middle, bb_lower, _bb_width = compute_bollinger_bands(closes)
        kdj_k, kdj_d, kdj_j = compute_kdj(highs, lows, closes)
        obv = compute_obv_trend(closes, volumes)
        ma_align = compute_ma_alignment(closes)

        # v3 extended technical indicators
        atr_pct = compute_atr(highs, lows, closes)
        roc_arr = compute_roc(closes)
        williams_r_arr = compute_williams_r(highs, lows, closes)
        cci_arr = compute_cci(closes, highs, lows)
        mfi_arr = compute_mfi(highs, lows, closes, volumes)
        donchian_pos_arr = compute_donchian_position(highs, lows, closes)
        aroon_arr = compute_aroon(closes)
        pv_corr_arr = compute_price_volume_corr(closes, volumes)

        return {
            "rsi": rsi_arr,
            "r2": r2_arr,
            "slope": slope_arr,
            "volume_ratio": vol_ratio_arr,
            "close": closes,
            "open": opens,
            "high": highs,
            "low": lows,
            "volume": volumes,
            # v2 indicators
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "bb_upper": bb_upper,
            "bb_middle": bb_middle,
            "bb_lower": bb_lower,
            "kdj_k": kdj_k,
            "kdj_d": kdj_d,
            "kdj_j": kdj_j,
            "obv_trend": obv,
            "ma_alignment": ma_align,
            # v3 extended indicators
            "atr_pct": atr_pct,
            "roc": roc_arr,
            "williams_r": williams_r_arr,
            "cci": cci_arr,
            "mfi": mfi_arr,
            "donchian_pos": donchian_pos_arr,
            "aroon": aroon_arr,
            "pv_corr": pv_corr_arr,
            # No fundamentals for crypto
            "fundamentals": {},
        }

    def _build_strategy_dna(self) -> StrategyDNA:
        """Convert the flat self.dna dict into a StrategyDNA dataclass.

        Handles custom_weights from the DNA (factor weights from evolution).
        """
        return StrategyDNA.from_dict(self.dna)

    def compute_score(self, symbol: str, ohlcv: list[list]) -> float:
        """Compute a 0-10 signal score using the full 42+ factor evolution engine.

        Uses the same score_stock() function as the backtest evolution engine,
        ensuring consistency between backtest and live trading.
        """
        if len(ohlcv) < 50:
            return 5.0  # neutral — need enough bars for reliable indicators

        try:
            indicators = self._build_indicators(ohlcv)
            strategy_dna = self._build_strategy_dna()
            idx = len(indicators["close"]) - 1
            score = score_stock(idx=idx, indicators=indicators, dna=strategy_dna)
            return max(0.0, min(10.0, score))
        except Exception as exc:
            logger.warning("Full scoring failed for %s, returning neutral: %s", symbol, exc)
            return 5.0

    def compute_score_simplified(self, symbol: str, ohlcv: list[list]) -> float:
        """Legacy simplified 4-factor scoring (kept for reference/fallback).

        Uses RSI, volume, and price momentum as core signals, weighted by DNA.
        """
        if len(ohlcv) < 20:
            return 5.0  # neutral

        closes = [c[4] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]

        score = 5.0  # start neutral

        # RSI component
        rsi = self._calc_rsi(closes)
        rsi_buy = self.dna.get("rsi_buy_threshold", 30.0)
        rsi_sell = self.dna.get("rsi_sell_threshold", 70.0)

        if rsi is not None:
            if rsi < rsi_buy:
                score += 2.0 * (1 - rsi / rsi_buy)
            elif rsi > rsi_sell:
                score -= 2.0 * ((rsi - rsi_sell) / (100 - rsi_sell))
            else:
                score += 0.5

        # Momentum (ROC)
        if len(closes) >= 10:
            roc = (closes[-1] - closes[-10]) / closes[-10] * 100 if closes[-10] else 0
            w_roc = self.dna.get("w_roc", 0.02)
            score += roc * w_roc * 10

        # Volume surge
        if len(volumes) >= 20 and volumes[-1] > 0:
            avg_vol = sum(volumes[-20:]) / 20
            vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
            vol_min = self.dna.get("volume_ratio_min", 1.2)
            if vol_ratio > vol_min:
                w_vol = self.dna.get("w_volume", 0.01)
                score += (vol_ratio - vol_min) * w_vol * 20

        # Price trend (SMA crossover)
        if len(closes) >= 50:
            sma20 = sum(closes[-20:]) / 20
            sma50 = sum(closes[-50:]) / 50
            if sma20 > sma50:
                w_trend = self.dna.get("w_trend", 0.01)
                score += w_trend * 30
            else:
                w_trend = self.dna.get("w_trend", 0.01)
                score -= w_trend * 15

        return max(0.0, min(10.0, score))

    @staticmethod
    def _calc_rsi(closes: list[float], period: int = 14) -> Optional[float]:
        """Classic Wilder RSI."""
        if len(closes) < period + 1:
            return None

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0.0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0.0 for d in deltas[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        for d in deltas[period:]:
            if d > 0:
                avg_gain = (avg_gain * (period - 1) + d) / period
                avg_loss = (avg_loss * (period - 1)) / period
            else:
                avg_gain = (avg_gain * (period - 1)) / period
                avg_loss = (avg_loss * (period - 1) + abs(d)) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(self, prices: Optional[dict[str, float]] = None) -> dict[str, dict]:
        """Generate buy/sell signals for all symbols.

        Returns dict of symbol -> {action, score, price}.

        If *prices* is provided it's used directly (useful for testing);
        otherwise prices are fetched from the exchange.
        """
        signals: dict[str, dict] = {}
        min_score = self.dna.get("min_score", 5)
        rsi_sell = self.dna.get("rsi_sell_threshold", 70.0)
        stop_loss = self.dna.get("stop_loss_pct", 5.0)
        take_profit = self.dna.get("take_profit_pct", 10.0)

        for symbol in self.symbols:
            if prices and symbol in prices:
                price = prices[symbol]
            else:
                price = self.fetch_price(symbol)

            if price is None:
                continue

            # Check existing positions for stop-loss / take-profit
            if symbol in self.positions:
                pos = self.positions[symbol]
                pnl_pct = pos.unrealised_pnl_pct(price)

                if pnl_pct <= -stop_loss:
                    signals[symbol] = {
                        "action": "SELL",
                        "reason": "stop_loss",
                        "score": 0.0,
                        "price": price,
                        "pnl_pct": pnl_pct,
                    }
                    continue
                elif pnl_pct >= take_profit:
                    signals[symbol] = {
                        "action": "SELL",
                        "reason": "take_profit",
                        "score": 10.0,
                        "price": price,
                        "pnl_pct": pnl_pct,
                    }
                    continue

            # Fetch OHLCV for scoring
            ohlcv = self.fetch_ohlcv(symbol) if not prices else []
            score = self.compute_score(symbol, ohlcv) if ohlcv else 5.0

            # Fallback: if we hold a position but have no OHLCV, use price-based scoring
            if symbol in self.positions and not ohlcv and price is not None:
                pos = self.positions[symbol]
                pnl_pct = pos.unrealised_pnl_pct(price)
                # Map PnL% to a score adjustment: losing → lower score
                score = max(0.0, min(10.0, 5.0 + pnl_pct * 0.3))

            if symbol in self.positions:
                # Sell signal if score drops below threshold
                if score < min_score - 2:
                    pos = self.positions[symbol]
                    signals[symbol] = {
                        "action": "SELL",
                        "reason": "score_drop",
                        "score": score,
                        "price": price,
                        "pnl_pct": pos.unrealised_pnl_pct(price),
                    }
            else:
                # Buy signal if score exceeds threshold
                if score >= min_score:
                    signals[symbol] = {
                        "action": "BUY",
                        "reason": "score_high",
                        "score": score,
                        "price": price,
                    }

        return signals

    # ------------------------------------------------------------------
    # Risk management
    # ------------------------------------------------------------------

    def check_stop_file(self) -> bool:
        """Check if the emergency stop file exists."""
        return self.stop_file.exists()

    def portfolio_value(self, prices: Optional[dict[str, float]] = None) -> float:
        """Calculate total portfolio value (cash + unrealised positions)."""
        value = self.cash
        for symbol, pos in self.positions.items():
            if prices and symbol in prices:
                price = prices[symbol]
            else:
                price = self.fetch_price(symbol)
                if price is None:
                    price = pos.entry_price  # fallback

            value += pos.qty * price
        return value

    def current_exposure_pct(self, prices: Optional[dict[str, float]] = None) -> float:
        """Current total exposure as % of portfolio value."""
        pv = self.portfolio_value(prices)
        if pv == 0:
            return 0.0
        invested = sum(
            pos.qty * (prices.get(sym, pos.entry_price) if prices else pos.entry_price)
            for sym, pos in self.positions.items()
        )
        return (invested / pv) * 100

    def check_daily_loss_limit(self, prices: Optional[dict[str, float]] = None) -> bool:
        """Return True if daily loss limit has been breached."""
        current = self.portfolio_value(prices)
        if self.daily_start_value == 0:
            return False
        daily_pnl_pct = ((current - self.daily_start_value) / self.daily_start_value) * 100
        return daily_pnl_pct <= self.daily_loss_limit_pct

    def _reset_daily_if_needed(self, prices: Optional[dict[str, float]] = None) -> None:
        """Reset daily P&L tracking at the start of a new day (UTC)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._day_date != today:
            self._day_date = today
            self.daily_start_value = self.portfolio_value(prices)
            self.daily_pnl = 0.0

    def max_position_value(self, prices: Optional[dict[str, float]] = None) -> float:
        """Maximum single position value based on risk config."""
        return self.portfolio_value(prices) * (self.max_position_size_pct / 100)

    def can_open_position(self, prices: Optional[dict[str, float]] = None) -> bool:
        """Check if we can open a new position given risk constraints."""
        max_positions = self.dna.get("max_positions", 3)
        if len(self.positions) >= max_positions:
            return False
        if self.current_exposure_pct(prices) >= self.max_exposure_pct:
            return False
        return True

    # Stored prices from the current cycle for risk checks
    _cycle_prices: Optional[dict[str, float]] = None

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------

    def execute_buy(self, symbol: str, price: float, score: float) -> Optional[dict]:
        """Execute (or simulate) a buy order.

        Returns trade record dict or None.
        """
        # Use cycle prices for risk checks (includes current price)
        risk_prices = dict(self._cycle_prices or {})
        risk_prices[symbol] = price
        if not self.can_open_position(risk_prices):
            logger.info("Cannot open position: risk limits")
            return None

        if symbol in self.positions:
            logger.info("Already holding %s", symbol)
            return None

        max_val = self.max_position_value(risk_prices)

        # Dynamic position sizing: stronger signals get bigger positions
        score_factor = max(0.5, min(1.5, score / 7.0))  # score 5=0.71x, 7=1.0x, 10=1.43x
        position_value = max_val * score_factor
        position_value = min(position_value, self.cash * 0.95)  # never use 100% of remaining cash
        qty = position_value / price if price > 0 else 0

        if qty <= 0 or position_value > self.cash:
            qty = self.cash * 0.95 / price if price > 0 else 0  # use 95% of remaining cash
            if qty <= 0:
                logger.info("Insufficient cash for %s", symbol)
                return None

        cost = qty * price

        if self.mode == "live":
            # Place real order
            try:
                if self._exchange is None:
                    self._exchange = self._init_exchange()
                order = self._exchange.create_market_buy_order(symbol, qty)
                logger.info("LIVE BUY order placed: %s", order.get("id"))
            except Exception as exc:
                logger.error("LIVE BUY failed for %s: %s", symbol, exc)
                return None

        # Update state
        now_str = datetime.now(timezone.utc).isoformat()
        self.cash -= cost
        self.positions[symbol] = Position(symbol, price, qty, now_str, "long")

        trade = {
            "action": "BUY",
            "symbol": symbol,
            "price": price,
            "qty": qty,
            "cost": cost,
            "score": score,
            "time": now_str,
            "mode": self.mode,
        }
        self.trade_log.append(trade)
        self._save_trade_log()

        logger.info("BUY %s @ %.2f | Qty: %.6g | Cost: $%.2f", symbol, price, qty, cost)

        if self.notifier:
            self.notifier.notify_trade("BUY", symbol, price, qty, score=score)

        return trade

    def execute_sell(self, symbol: str, price: float, score: float = 0.0) -> Optional[dict]:
        """Execute (or simulate) a sell order.

        Returns trade record dict or None.
        """
        if symbol not in self.positions:
            logger.info("No position to sell for %s", symbol)
            return None

        pos = self.positions[symbol]
        qty = pos.qty
        pnl = pos.unrealised_pnl(price)
        pnl_pct = pos.unrealised_pnl_pct(price)
        revenue = qty * price

        if self.mode == "live":
            try:
                if self._exchange is None:
                    self._exchange = self._init_exchange()
                order = self._exchange.create_market_sell_order(symbol, qty)
                logger.info("LIVE SELL order placed: %s", order.get("id"))
            except Exception as exc:
                logger.error("LIVE SELL failed for %s: %s", symbol, exc)
                return None

        # Update state
        now_str = datetime.now(timezone.utc).isoformat()
        self.cash += revenue
        self.daily_pnl += pnl
        del self.positions[symbol]

        trade = {
            "action": "SELL",
            "symbol": symbol,
            "price": price,
            "qty": qty,
            "revenue": revenue,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "score": score,
            "time": now_str,
            "mode": self.mode,
        }
        self.trade_log.append(trade)
        self._save_trade_log()

        logger.info(
            "SELL %s @ %.2f | Qty: %.6g | PnL: $%.2f (%.1f%%)",
            symbol, price, qty, pnl, pnl_pct,
        )

        if self.notifier:
            self.notifier.notify_trade("SELL", symbol, price, qty, pnl=pnl, pnl_pct=pnl_pct)

        return trade

    # ------------------------------------------------------------------
    # Trade log persistence
    # ------------------------------------------------------------------

    def _save_trade_log(self) -> None:
        """Persist trade log to JSON."""
        try:
            self.trade_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.trade_log_path, "w") as f:
                json.dump(self.trade_log, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save trade log: %s", exc)

    def load_trade_log(self) -> list[dict]:
        """Load existing trade log."""
        if self.trade_log_path.exists():
            try:
                with open(self.trade_log_path) as f:
                    self.trade_log = json.load(f)
            except Exception:
                self.trade_log = []
        return self.trade_log

    def _reconstruct_positions(self) -> None:
        """Rebuild positions and cash from trade log after a restart.

        Replays all trades sequentially to reconstruct the current state,
        so that a restart doesn't open duplicate positions.
        """
        self.positions = {}
        self.cash = self.initial_balance

        for trade in self.trade_log:
            symbol = trade["symbol"]
            action = trade["action"]

            if action == "BUY":
                price = trade["price"]
                qty = trade["qty"]
                cost = trade.get("cost", price * qty)
                entry_time = trade.get("time", "")
                self.cash -= cost
                if symbol in self.positions:
                    # Average into existing position
                    pos = self.positions[symbol]
                    total_qty = pos.qty + qty
                    avg_price = (pos.entry_price * pos.qty + price * qty) / total_qty
                    pos.entry_price = avg_price
                    pos.qty = total_qty
                else:
                    self.positions[symbol] = Position(
                        symbol, price, qty, entry_time, "long"
                    )
            elif action == "SELL":
                qty = trade["qty"]
                revenue = trade.get("revenue", trade["price"] * qty)
                self.cash += revenue
                if symbol in self.positions:
                    del self.positions[symbol]

        if self.positions:
            logger.info(
                "Reconstructed %d positions from trade log: %s (cash: $%.2f)",
                len(self.positions),
                list(self.positions.keys()),
                self.cash,
            )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run_cycle(self, prices: Optional[dict[str, float]] = None) -> None:
        """Run a single trading cycle: generate signals and execute."""
        self._cycle_prices = prices
        self._reset_daily_if_needed(prices)

        # Check risk limits
        if self.check_stop_file():
            logger.warning("STOP_TRADING file detected — halting")
            if self.notifier:
                self.notifier.notify_emergency_stop("STOP_TRADING flag file detected")
            self._running = False
            return

        if self.check_daily_loss_limit(prices):
            logger.warning("Daily loss limit breached — halting")
            if self.notifier:
                pv = self.portfolio_value(prices)
                daily_pct = ((pv - self.daily_start_value) / self.daily_start_value) * 100
                self.notifier.notify_risk_alert(
                    f"Daily loss limit breached ({daily_pct:.1f}%). Trading halted."
                )
            self._running = False
            return

        # Generate and act on signals
        signals = self.generate_signals(prices)

        for symbol, sig in signals.items():
            if sig["action"] == "SELL":
                self.execute_sell(symbol, sig["price"], sig.get("score", 0))
            elif sig["action"] == "BUY":
                self.execute_buy(symbol, sig["price"], sig.get("score", 5))

    def start(self) -> None:
        """Start the live trading loop (blocking)."""
        logger.info(
            "Starting CryptoLiveRunner: mode=%s exchange=%s symbols=%s interval=%dm",
            self.mode, self.exchange_id, self.symbols, self.interval_minutes,
        )

        self.load_dna()
        self.load_trade_log()
        self._reconstruct_positions()
        self._running = True
        self._stop_event.clear()

        if self.notifier:
            self.notifier.notify_startup(self.mode, self.symbols, self.exchange_id)

        try:
            while self._running and not self._stop_event.is_set():
                try:
                    self._run_cycle()
                except Exception as exc:
                    logger.error("Cycle error: %s", exc)

                # Wait for next cycle (check stop every 10s)
                remaining = self.interval_minutes * 60
                while remaining > 0 and self._running and not self._stop_event.is_set():
                    wait = min(remaining, 10)
                    self._stop_event.wait(wait)
                    remaining -= wait

                    # Re-check stop file during wait
                    if self.check_stop_file():
                        logger.warning("STOP_TRADING detected during wait")
                        self._running = False
                        break

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt — stopping")
        finally:
            self._running = False
            logger.info("CryptoLiveRunner stopped")

    def stop(self) -> None:
        """Stop the runner gracefully."""
        logger.info("Stop requested")
        self._running = False
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return self._running


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for ``python -m src.crypto.live_runner``."""
    import argparse

    parser = argparse.ArgumentParser(description="FinClaw Crypto Live Runner")
    parser.add_argument("--mode", default="dry_run", choices=["dry_run", "live"])
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbols", default="BTC/USDT",
                        help="Comma-separated symbol list")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_MINUTES,
                        help="Minutes between cycles")
    parser.add_argument("--balance", type=float, default=DEFAULT_INITIAL_BALANCE)
    parser.add_argument("--dna-path", default=DEFAULT_DNA_PATH)
    parser.add_argument("--trade-log", default=DEFAULT_TRADE_LOG_PATH)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-secret", default=None)
    parser.add_argument("--telegram-token", default=os.environ.get("TELEGRAM_BOT_TOKEN"))
    parser.add_argument("--telegram-chat-id", default=os.environ.get("TELEGRAM_CHAT_ID"))
    args = parser.parse_args()

    # Configure logging to stderr
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    runner = CryptoLiveRunner(
        exchange=args.exchange,
        mode=args.mode,
        api_key=args.api_key,
        api_secret=args.api_secret,
        symbols=symbols,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat_id,
        initial_balance=args.balance,
        interval_minutes=args.interval,
        dna_path=args.dna_path,
        trade_log_path=args.trade_log,
    )

    runner.start()


if __name__ == "__main__":
    main()
