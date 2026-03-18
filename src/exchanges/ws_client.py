"""
WebSocket base client with auto-reconnect, heartbeat, and event callbacks.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], Any]
ErrorHandler = Callable[[Exception], Any]


class WebSocketClient:
    """Base WebSocket client with reconnection and event system."""

    def __init__(
        self,
        url: str,
        on_message: MessageHandler | None = None,
        on_error: ErrorHandler | None = None,
        reconnect: bool = True,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0,
        ping_interval: float = 20.0,
    ):
        self.url = url
        self._on_message = on_message
        self._on_error = on_error or self._default_error_handler
        self.reconnect = reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.ping_interval = ping_interval

        self.callbacks: dict[str, list[Callable]] = {}
        self._ws = None
        self._connected = False
        self._running = False
        self._reconnect_count = 0
        self._subscriptions: list[dict] = []
        self._last_message_time: float = 0
        self._recv_task: asyncio.Task | None = None

    # --- Connection lifecycle ---

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        try:
            import websockets
        except ImportError:
            raise ImportError("Install websockets: pip install websockets")

        self._running = True
        self._reconnect_count = 0
        await self._do_connect()

    async def _do_connect(self) -> None:
        import websockets

        try:
            self._ws = await websockets.connect(self.url, ping_interval=self.ping_interval)
            self._connected = True
            self._reconnect_count = 0
            logger.info("WebSocket connected: %s", self.url)
            self._emit("connected", {"url": self.url})

            # Resubscribe after reconnect
            for sub in self._subscriptions:
                await self._send_subscribe(sub["channel"], sub["symbol"], sub.get("params", {}))

            self._recv_task = asyncio.create_task(self._recv_loop())
        except Exception as e:
            logger.error("WebSocket connect failed: %s", e)
            self._connected = False
            self._on_error(e)
            if self._running and self.reconnect:
                await self._try_reconnect()

    async def _recv_loop(self) -> None:
        """Receive messages in a loop."""
        try:
            async for raw in self._ws:
                self._last_message_time = time.time()
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    data = {"raw": raw}

                if self._on_message:
                    self._on_message(data)
                self._emit("message", data)
        except Exception as e:
            if self._running:
                logger.warning("WebSocket recv error: %s", e)
                self._connected = False
                self._on_error(e)
                self._emit("disconnected", {"reason": str(e)})
                if self.reconnect:
                    await self._try_reconnect()

    async def _try_reconnect(self) -> None:
        """Attempt reconnection with exponential backoff."""
        while self._running and self._reconnect_count < self.max_reconnect_attempts:
            self._reconnect_count += 1
            delay = self.reconnect_delay * (2 ** (self._reconnect_count - 1))
            logger.info("Reconnecting in %.1fs (attempt %d/%d)", delay, self._reconnect_count, self.max_reconnect_attempts)
            self._emit("reconnecting", {"attempt": self._reconnect_count})
            await asyncio.sleep(delay)
            if not self._running:
                break
            try:
                await self._do_connect()
                return
            except Exception:
                continue
        if self._running:
            logger.error("Max reconnect attempts reached")
            self._emit("max_reconnect", {})

    # --- Subscribe / Unsubscribe ---

    async def subscribe(self, channel: str, symbol: str, **params) -> None:
        """Subscribe to a channel for a symbol."""
        sub = {"channel": channel, "symbol": symbol, "params": params}
        if sub not in self._subscriptions:
            self._subscriptions.append(sub)
        if self._connected:
            await self._send_subscribe(channel, symbol, params)

    async def unsubscribe(self, channel: str, symbol: str) -> None:
        """Unsubscribe from a channel."""
        self._subscriptions = [s for s in self._subscriptions if not (s["channel"] == channel and s["symbol"] == symbol)]
        if self._connected:
            await self._send_unsubscribe(channel, symbol)

    async def _send_subscribe(self, channel: str, symbol: str, params: dict) -> None:
        """Override in subclasses to send exchange-specific subscribe message."""
        raise NotImplementedError

    async def _send_unsubscribe(self, channel: str, symbol: str) -> None:
        """Override in subclasses to send exchange-specific unsubscribe message."""
        raise NotImplementedError

    async def send(self, data: dict | str) -> None:
        """Send a message to the server."""
        if not self._connected or not self._ws:
            raise ConnectionError("WebSocket not connected")
        msg = json.dumps(data) if isinstance(data, dict) else data
        await self._ws.send(msg)

    # --- Close ---

    async def close(self) -> None:
        """Gracefully close the connection."""
        self._running = False
        self._connected = False
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.warning("Error closing WebSocket connection: %s", e)
        self._emit("closed", {})
        logger.info("WebSocket closed")

    # --- Event system ---

    def on(self, event: str, callback: Callable) -> None:
        """Register an event callback."""
        self.callbacks.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable | None = None) -> None:
        """Remove event callback(s)."""
        if callback:
            self.callbacks.get(event, []).remove(callback)
        else:
            self.callbacks.pop(event, None)

    def _emit(self, event: str, data: Any) -> None:
        """Emit an event to registered callbacks."""
        for cb in self.callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error("Callback error for %s: %s", event, e)

    # --- Properties ---

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def subscriptions(self) -> list[dict]:
        return list(self._subscriptions)

    @property
    def last_message_time(self) -> float:
        return self._last_message_time

    @staticmethod
    def _default_error_handler(e: Exception) -> None:
        logger.error("WebSocket error: %s", e)
