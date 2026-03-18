"""
FinClaw MCP Server — exposes FinClaw capabilities as MCP tools for AI agents.

Implements the Model Context Protocol (2024-11-05) over stdio JSON-RPC.
"""

from __future__ import annotations

import sys
import os

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Any

SERVER_NAME = "finclaw"
SERVER_VERSION = "5.1.0"
PROTOCOL_VERSION = "2024-11-05"


# ── Tool definitions ──────────────────────────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_quote",
        "description": "Get a real-time quote for a symbol from any supported exchange.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. AAPL, BTCUSDT, 000001.SZ"},
                "exchange": {"type": "string", "description": "Exchange adapter name (default: yahoo)", "default": "yahoo"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_history",
        "description": "Get OHLCV candle history for a symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol"},
                "exchange": {"type": "string", "default": "yahoo"},
                "timeframe": {"type": "string", "default": "1d", "description": "Candle interval: 1m,5m,1h,1d,1w"},
                "limit": {"type": "integer", "default": 50, "description": "Number of candles"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "list_exchanges",
        "description": "List all available exchange adapters grouped by type.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_backtest",
        "description": "Run a strategy backtest on given tickers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strategy": {"type": "string", "description": "Strategy name, e.g. momentum, sma_crossover"},
                "tickers": {"type": "string", "description": "Comma-separated tickers"},
                "start": {"type": "string", "description": "Start date YYYY-MM-DD", "default": "2023-01-01"},
                "end": {"type": "string", "description": "End date YYYY-MM-DD (optional)"},
                "capital": {"type": "number", "default": 100000},
            },
            "required": ["strategy", "tickers"],
        },
    },
    {
        "name": "analyze_portfolio",
        "description": "Analyze a portfolio of holdings with risk metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "holdings": {
                    "type": "array",
                    "description": "List of {symbol, shares, cost_basis} objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string"},
                            "shares": {"type": "number"},
                            "cost_basis": {"type": "number"},
                        },
                        "required": ["symbol", "shares"],
                    },
                },
            },
            "required": ["holdings"],
        },
    },
    {
        "name": "get_indicators",
        "description": "Calculate technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands) for a symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of indicator names: sma, ema, rsi, macd, bbands",
                    "default": ["sma", "rsi"],
                },
                "period": {"type": "integer", "default": 14},
                "exchange": {"type": "string", "default": "yahoo"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "screen_stocks",
        "description": "Screen stocks by technical/fundamental criteria.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "universe": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tickers to screen",
                },
                "min_price": {"type": "number"},
                "max_price": {"type": "number"},
                "min_volume": {"type": "number"},
                "rsi_below": {"type": "number", "description": "RSI below this value (oversold)"},
                "rsi_above": {"type": "number", "description": "RSI above this value (overbought)"},
            },
            "required": ["universe"],
        },
    },
    {
        "name": "get_sentiment",
        "description": "Get market sentiment analysis for a symbol using technical signals.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "exchange": {"type": "string", "default": "yahoo"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "compare_strategies",
        "description": "Compare performance of multiple strategies on the same tickers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strategies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Strategy names to compare",
                },
                "tickers": {"type": "string", "description": "Comma-separated tickers"},
                "start": {"type": "string", "default": "2023-01-01"},
                "end": {"type": "string"},
                "capital": {"type": "number", "default": 100000},
            },
            "required": ["strategies", "tickers"],
        },
    },
    {
        "name": "get_funding_rates",
        "description": "Get current funding rates for crypto perpetual futures.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Crypto symbols, e.g. ['BTCUSDT', 'ETHUSDT']",
                },
                "exchange": {"type": "string", "default": "binance"},
            },
            "required": ["symbols"],
        },
    },
]


class FinClawMCPServer:
    """MCP Server that exposes FinClaw as tools for AI agents."""

    def __init__(self):
        self._tools = {t["name"]: t for t in TOOLS}

    # ── MCP handlers ──

    def handle_initialize(self, params: dict | None = None) -> dict:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    def handle_tools_list(self) -> dict:
        return {"tools": TOOLS}

    def handle_tools_call(self, name: str, arguments: dict | None = None) -> dict:
        arguments = arguments or {}
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return _error_content(f"Unknown tool: {name}")
        try:
            result = handler(arguments)
            if isinstance(result, dict) and "isError" in result:
                return result
            return {"content": [{"type": "text", "text": _json_dumps(result)}]}
        except Exception as e:
            return _error_content(str(e))

    # ── Tool implementations ──

    def _tool_get_quote(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry
        exchange = args.get("exchange", "yahoo")
        adapter = ExchangeRegistry.get(exchange)
        return adapter.get_ticker(args["symbol"])

    def _tool_get_history(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry
        exchange = args.get("exchange", "yahoo")
        adapter = ExchangeRegistry.get(exchange)
        candles = adapter.get_ohlcv(
            args["symbol"],
            args.get("timeframe", "1d"),
            args.get("limit", 50),
        )
        return {"symbol": args["symbol"], "exchange": exchange, "count": len(candles), "candles": candles}

    def _tool_list_exchanges(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry
        result = {}
        for etype in ("crypto", "stock_us", "stock_cn"):
            names = ExchangeRegistry.list_by_type(etype)
            if names:
                result[etype] = names
        return result

    def _tool_run_backtest(self, args: dict) -> Any:
        from src.backtesting.core_engine import BacktestEngine

        tickers = [t.strip() for t in args["tickers"].split(",")]
        engine = BacktestEngine()
        results = engine.run(
            strategy=args["strategy"],
            tickers=tickers,
            start=args.get("start", "2023-01-01"),
            end=args.get("end"),
            initial_capital=args.get("capital", 100000),
        )
        return results

    def _tool_analyze_portfolio(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get("yahoo")

        holdings = args["holdings"]
        total_value = 0
        analysis = []
        for h in holdings:
            try:
                ticker = adapter.get_ticker(h["symbol"])
                price = ticker.get("last", 0)
                shares = h.get("shares", 0)
                cost = h.get("cost_basis", price)
                value = price * shares
                pnl = (price - cost) * shares
                total_value += value
                analysis.append({
                    "symbol": h["symbol"],
                    "price": price,
                    "shares": shares,
                    "value": value,
                    "cost_basis": cost,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((price / cost - 1) * 100, 2) if cost else 0,
                })
            except Exception as e:
                analysis.append({"symbol": h["symbol"], "error": str(e)})

        # weights
        for a in analysis:
            if "value" in a and total_value > 0:
                a["weight_pct"] = round(a["value"] / total_value * 100, 2)

        return {"total_value": round(total_value, 2), "holdings": analysis}

    def _tool_get_indicators(self, args: dict) -> Any:
        from src.ta.indicators import TechnicalIndicators

        symbol = args["symbol"]
        exchange = args.get("exchange", "yahoo")
        indicators = args.get("indicators", ["sma", "rsi"])
        period = args.get("period", 14)

        # Fetch data
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get(exchange)
        candles = adapter.get_ohlcv(symbol, "1d", max(200, period * 3))
        closes = [c["close"] for c in candles]

        result: dict[str, Any] = {"symbol": symbol, "period": period, "data_points": len(closes)}
        ti = TechnicalIndicators()

        for ind in indicators:
            ind_lower = ind.lower()
            try:
                if ind_lower == "sma":
                    vals = ti.sma(closes, period)
                    result["sma"] = {"period": period, "current": round(vals[-1], 4) if vals else None}
                elif ind_lower == "ema":
                    vals = ti.ema(closes, period)
                    result["ema"] = {"period": period, "current": round(vals[-1], 4) if vals else None}
                elif ind_lower == "rsi":
                    vals = ti.rsi(closes, period)
                    result["rsi"] = {"period": period, "current": round(vals[-1], 2) if vals else None}
                elif ind_lower == "macd":
                    macd_line, signal, hist = ti.macd(closes)
                    result["macd"] = {
                        "macd": round(macd_line[-1], 4) if macd_line else None,
                        "signal": round(signal[-1], 4) if signal else None,
                        "histogram": round(hist[-1], 4) if hist else None,
                    }
                elif ind_lower == "bbands":
                    upper, middle, lower = ti.bollinger_bands(closes, period)
                    result["bbands"] = {
                        "upper": round(upper[-1], 4) if upper else None,
                        "middle": round(middle[-1], 4) if middle else None,
                        "lower": round(lower[-1], 4) if lower else None,
                    }
                else:
                    result[ind_lower] = {"error": f"Unknown indicator: {ind}"}
            except Exception as e:
                result[ind_lower] = {"error": str(e)}

        return result

    def _tool_screen_stocks(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry
        from src.ta.indicators import TechnicalIndicators

        adapter = ExchangeRegistry.get("yahoo")
        ti = TechnicalIndicators()
        universe = args.get("universe", [])
        passed = []

        for sym in universe:
            try:
                ticker = adapter.get_ticker(sym)
                price = ticker.get("last", 0)
                volume = ticker.get("volume", 0)

                if args.get("min_price") and price < args["min_price"]:
                    continue
                if args.get("max_price") and price > args["max_price"]:
                    continue
                if args.get("min_volume") and volume < args["min_volume"]:
                    continue

                # RSI filter
                if args.get("rsi_below") or args.get("rsi_above"):
                    candles = adapter.get_ohlcv(sym, "1d", 100)
                    closes = [c["close"] for c in candles]
                    rsi_vals = ti.rsi(closes, 14)
                    rsi = rsi_vals[-1] if rsi_vals else 50
                    if args.get("rsi_below") and rsi >= args["rsi_below"]:
                        continue
                    if args.get("rsi_above") and rsi <= args["rsi_above"]:
                        continue
                else:
                    rsi = None

                passed.append({"symbol": sym, "price": price, "volume": volume, "rsi": rsi})
            except Exception:
                continue

        return {"screened": len(universe), "passed": len(passed), "results": passed}

    def _tool_get_sentiment(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry
        from src.ta.indicators import TechnicalIndicators

        adapter = ExchangeRegistry.get(args.get("exchange", "yahoo"))
        symbol = args["symbol"]
        candles = adapter.get_ohlcv(symbol, "1d", 200)
        closes = [c["close"] for c in candles]

        ti = TechnicalIndicators()
        rsi_vals = ti.rsi(closes, 14)
        sma_20 = ti.sma(closes, 20)
        sma_50 = ti.sma(closes, 50)
        macd_line, signal, _ = ti.macd(closes)

        rsi = rsi_vals[-1] if rsi_vals else 50
        signals = []
        score = 0

        # RSI
        if rsi < 30:
            signals.append("RSI oversold (bullish)")
            score += 2
        elif rsi > 70:
            signals.append("RSI overbought (bearish)")
            score -= 2
        else:
            signals.append(f"RSI neutral ({rsi:.0f})")

        # SMA crossover
        if sma_20 and sma_50 and sma_20[-1] > sma_50[-1]:
            signals.append("SMA20 > SMA50 (bullish)")
            score += 1
        elif sma_20 and sma_50:
            signals.append("SMA20 < SMA50 (bearish)")
            score -= 1

        # MACD
        if macd_line and signal and macd_line[-1] > signal[-1]:
            signals.append("MACD bullish crossover")
            score += 1
        elif macd_line and signal:
            signals.append("MACD bearish")
            score -= 1

        # Price vs SMA
        if sma_50 and closes[-1] > sma_50[-1]:
            signals.append("Price above SMA50 (bullish)")
            score += 1
        elif sma_50:
            signals.append("Price below SMA50 (bearish)")
            score -= 1

        if score >= 3:
            sentiment = "strongly_bullish"
        elif score >= 1:
            sentiment = "bullish"
        elif score <= -3:
            sentiment = "strongly_bearish"
        elif score <= -1:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            "symbol": symbol,
            "sentiment": sentiment,
            "score": score,
            "rsi": round(rsi, 2),
            "signals": signals,
        }

    def _tool_compare_strategies(self, args: dict) -> Any:
        from src.backtesting.core_engine import BacktestEngine

        strategies = args["strategies"]
        tickers = [t.strip() for t in args["tickers"].split(",")]
        results = {}
        engine = BacktestEngine()

        for strat in strategies:
            try:
                r = engine.run(
                    strategy=strat,
                    tickers=tickers,
                    start=args.get("start", "2023-01-01"),
                    end=args.get("end"),
                    initial_capital=args.get("capital", 100000),
                )
                results[strat] = r
            except Exception as e:
                results[strat] = {"error": str(e)}

        return {"strategies": results}

    def _tool_get_funding_rates(self, args: dict) -> Any:
        from src.exchanges.registry import ExchangeRegistry

        exchange = args.get("exchange", "binance")
        adapter = ExchangeRegistry.get(exchange)
        symbols = args.get("symbols", [])
        rates = {}

        for sym in symbols:
            try:
                if hasattr(adapter, "get_funding_rate"):
                    rate = adapter.get_funding_rate(sym)
                    rates[sym] = rate
                else:
                    rates[sym] = {"error": f"Exchange {exchange} does not support funding rates"}
            except Exception as e:
                rates[sym] = {"error": str(e)}

        return {"exchange": exchange, "funding_rates": rates}


# ── Helpers ──

def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str, ensure_ascii=False)


def _error_content(msg: str) -> dict:
    return {
        "content": [{"type": "text", "text": msg}],
        "isError": True,
    }
