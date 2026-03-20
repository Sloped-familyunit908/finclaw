"""
FinClaw Crypto Trading Bot
==========================
RSI-based spot trading strategy for Binance.
Uses ccxt for exchange connectivity.
"""

import ccxt
import numpy as np
from datetime import datetime, timezone
from typing import Optional
import json
import os
import logging

logger = logging.getLogger("finclaw.crypto")


class CryptoTradingBot:
    """RSI-based crypto trading bot using ccxt."""

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: str = "",
        secret: str = "",
        sandbox: bool = True,
        config_path: str = "crypto_config.json",
    ):
        """
        Args:
            exchange_id: Exchange name (binance, etc.)
            api_key: API key
            secret: API secret
            sandbox: Use testnet if True
            config_path: Path to save/load state
        """
        self.exchange_id = exchange_id
        self.sandbox = sandbox
        self.config_path = config_path

        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        config: dict = {
            "enableRateLimit": True,
        }
        if api_key:
            config["apiKey"] = api_key
        if secret:
            config["secret"] = secret

        self.exchange: ccxt.Exchange = exchange_class(config)

        if sandbox:
            try:
                self.exchange.set_sandbox_mode(True)
            except ccxt.NotSupported:
                logger.warning(
                    "%s does not support sandbox mode, running in dry-run",
                    exchange_id,
                )

        # In-memory simulated portfolio for sandbox / dry-run
        self._sim_portfolio: dict[str, float] = {"USDT": 10_000.0}
        self._sim_trades: list[dict] = []
        self._trade_counter = 0

    # ------------------------------------------------------------------
    # RSI
    # ------------------------------------------------------------------

    def calculate_rsi(self, closes: list[float], period: int = 14) -> float:
        """Calculate RSI from close prices.

        Uses the classic Wilder smoothing (exponential moving average of
        gains and losses).  Returns 50.0 when there is not enough data.
        """
        if len(closes) < period + 1:
            return 50.0

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1.0 + rs)

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def get_signal(self, symbol: str = "BTC/USDT") -> dict:
        """Get trading signal for a symbol.

        Returns
        -------
        dict
            ``{signal, rsi, price, confidence}``

        Rules
        -----
        - RSI < 25 → ``strong_buy``   (confidence 0.9)
        - RSI < 30 → ``buy``          (confidence 0.7)
        - RSI > 80 → ``strong_sell``  (confidence 0.9)
        - RSI > 70 → ``sell``         (confidence 0.7)
        - otherwise → ``hold``        (confidence 0.5)
        """
        ohlcv = self.exchange.fetch_ohlcv(symbol, "1d", limit=50)
        closes = [candle[4] for candle in ohlcv]
        rsi = self.calculate_rsi(closes)
        price = closes[-1]

        if rsi < 25:
            signal, confidence = "strong_buy", 0.9
        elif rsi < 30:
            signal, confidence = "buy", 0.7
        elif rsi > 80:
            signal, confidence = "strong_sell", 0.9
        elif rsi > 70:
            signal, confidence = "sell", 0.7
        else:
            signal, confidence = "hold", 0.5

        return {
            "signal": signal,
            "rsi": round(rsi, 2),
            "price": price,
            "confidence": confidence,
            "symbol": symbol,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------

    def execute_trade(self, symbol: str, side: str, amount_usd: float) -> dict:
        """Execute a trade on the exchange.

        If *sandbox* is ``True`` the trade is simulated in memory;
        otherwise a real market order is placed via ccxt.

        Returns
        -------
        dict
            ``{order_id, symbol, side, amount, price, status}``
        """
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got '{side}'")
        if amount_usd <= 0:
            raise ValueError("amount_usd must be positive")

        if self.sandbox:
            return self._simulate_trade(symbol, side, amount_usd)

        # Live execution
        ticker = self.exchange.fetch_ticker(symbol)
        price = ticker["last"]
        amount = amount_usd / price
        order = self.exchange.create_market_order(symbol, side, amount)
        return {
            "order_id": order["id"],
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "status": order.get("status", "filled"),
        }

    def _simulate_trade(self, symbol: str, side: str, amount_usd: float) -> dict:
        """Simulate a trade in the in-memory portfolio."""
        base, quote = symbol.split("/")

        # Use last known price or a placeholder
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker["last"]
        except Exception:
            price = amount_usd  # fallback

        amount = amount_usd / price
        self._trade_counter += 1

        if side == "buy":
            self._sim_portfolio[quote] = self._sim_portfolio.get(quote, 0) - amount_usd
            self._sim_portfolio[base] = self._sim_portfolio.get(base, 0) + amount
        else:
            self._sim_portfolio[base] = self._sim_portfolio.get(base, 0) - amount
            self._sim_portfolio[quote] = self._sim_portfolio.get(quote, 0) + amount_usd

        trade = {
            "order_id": f"sim-{self._trade_counter}",
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "status": "simulated",
        }
        self._sim_trades.append(trade)
        logger.info("Simulated %s %s %.6f @ %.2f", side, symbol, amount, price)
        return trade

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def get_portfolio(self) -> dict:
        """Get current portfolio balances.

        In sandbox mode returns the simulated portfolio; otherwise
        fetches the real balance from the exchange.
        """
        if self.sandbox:
            return {k: v for k, v in self._sim_portfolio.items() if v != 0}

        balance = self.exchange.fetch_balance()
        return {
            asset: info["total"]
            for asset, info in balance.get("total", {}).items()
            if isinstance(info, (int, float)) and info > 0
        }

    # ------------------------------------------------------------------
    # Daily strategy run
    # ------------------------------------------------------------------

    def daily_run(
        self,
        symbols: list[str] | None = None,
        max_position_usd: float = 200,
    ) -> list[dict]:
        """Run the daily strategy loop.

        For each symbol: get signal → decide action → execute if needed.

        Returns list of actions taken.
        """
        if symbols is None:
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

        actions: list[dict] = []
        for symbol in symbols:
            try:
                sig = self.get_signal(symbol)
            except Exception as exc:
                logger.error("Failed to get signal for %s: %s", symbol, exc)
                actions.append({"symbol": symbol, "action": "error", "error": str(exc)})
                continue

            action = "hold"
            amount_usd = 0.0

            if sig["signal"] == "strong_buy":
                action = "buy"
                amount_usd = min(max_position_usd * 2, max_position_usd * 2)
            elif sig["signal"] == "buy":
                action = "buy"
                amount_usd = max_position_usd
            elif sig["signal"] == "strong_sell":
                action = "sell"
                amount_usd = max_position_usd * 2
            elif sig["signal"] == "sell":
                action = "sell"
                amount_usd = max_position_usd

            entry: dict = {
                "symbol": symbol,
                "action": action,
                "signal": sig["signal"],
                "rsi": sig["rsi"],
                "price": sig["price"],
                "confidence": sig["confidence"],
            }

            if action != "hold":
                try:
                    trade = self.execute_trade(symbol, action, amount_usd)
                    entry["trade"] = trade
                except Exception as exc:
                    logger.error("Trade failed for %s: %s", symbol, exc)
                    entry["error"] = str(exc)

            actions.append(entry)

        return actions

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> str:
        """Generate a text report of current positions and simulated P&L."""
        lines = [
            "=" * 50,
            "FinClaw Crypto Trading Report",
            f"Generated: {datetime.now(tz=timezone.utc).isoformat()}",
            f"Exchange:  {self.exchange_id} ({'sandbox' if self.sandbox else 'live'})",
            "=" * 50,
            "",
            "Portfolio:",
        ]

        portfolio = self.get_portfolio()
        if not portfolio:
            lines.append("  (empty)")
        else:
            for asset, amount in sorted(portfolio.items()):
                lines.append(f"  {asset}: {amount:.6f}")

        lines.append("")
        lines.append(f"Recent trades: {len(self._sim_trades)}")
        for t in self._sim_trades[-10:]:
            lines.append(
                f"  [{t['order_id']}] {t['side'].upper()} {t['symbol']} "
                f"{t['amount']:.6f} @ {t['price']:.2f}"
            )

        return "\n".join(lines)
