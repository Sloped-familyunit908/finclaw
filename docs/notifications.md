# Notifications

FinClaw supports multi-channel notifications for alerts, trade signals, and system events. All channels implement a common interface, and the **NotificationHub** routes messages to one or more channels simultaneously.

---

## Supported Channels

| Channel | Module | Auth Required | Description |
|---------|--------|---------------|-------------|
| **Console** | `console` | No | Print to terminal (default) |
| **Telegram** | `telegram` | Bot token + chat ID | Telegram bot messages |
| **Discord** | `discord` | Webhook URL | Discord webhook messages |
| **Email** | `email_channel` | SMTP credentials | Email notifications |
| **Webhook** | `webhook` | URL | Generic HTTP POST webhook |

---

## Quick Start

### Using NotificationHub

```python
from src.notifications.hub import NotificationHub
from src.notifications.console import ConsoleChannel
from src.notifications.telegram import TelegramChannel
from src.notifications.discord import DiscordChannel
from src.notifications.webhook import WebhookChannel

hub = NotificationHub()

# Register channels
hub.register_channel("console", ConsoleChannel())
hub.register_channel("telegram", TelegramChannel(
    bot_token="YOUR_BOT_TOKEN",
    chat_id="YOUR_CHAT_ID",
))
hub.register_channel("discord", DiscordChannel(
    webhook_url="https://discord.com/api/webhooks/...",
))

# Send to all channels
results = hub.send("🚀 AAPL buy signal at $185.50", level="info")
# {"console": True, "telegram": True, "discord": True}

# Send to specific channels only
results = hub.send("⚠️ Max drawdown reached", level="critical", channels=["telegram"])
```

### Notification Levels

| Level | Use Case |
|-------|----------|
| `debug` | Verbose debugging info |
| `info` | Normal signals and updates |
| `warning` | Risk warnings, unusual activity |
| `critical` | Stop-loss triggered, system errors |

---

## Channel Configuration

### Console

No configuration needed. Prints to stdout with level-based formatting.

```python
from src.notifications.console import ConsoleChannel

channel = ConsoleChannel()
channel.send("Hello from FinClaw!", level="info")
```

### Telegram

Requires a [Telegram Bot](https://core.telegram.org/bots#how-do-i-create-a-bot) token and chat ID.

```python
from src.notifications.telegram import TelegramChannel

channel = TelegramChannel(
    bot_token="123456:ABC-DEF...",
    chat_id="-1001234567890",  # Group or user chat ID
)
channel.test()  # Send a test message
```

**Environment variables:**

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### Discord

Uses Discord [webhook URLs](https://support.discord.com/hc/en-us/articles/228383668).

```python
from src.notifications.discord import DiscordChannel

channel = DiscordChannel(
    webhook_url="https://discord.com/api/webhooks/123/abc...",
)
channel.send("📈 Portfolio up +2.3% today")
```

**Environment variable:**

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

### Email

SMTP-based email notifications.

```python
from src.notifications.email_channel import EmailChannel

channel = EmailChannel(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="you@gmail.com",
    password="app-password",
    to_address="you@gmail.com",
)
channel.send("Daily portfolio report", level="info")
```

### Webhook

Generic HTTP POST to any URL. Useful for Slack, custom APIs, or automation tools.

```python
from src.notifications.webhook import WebhookChannel

channel = WebhookChannel(
    url="https://your-api.com/notifications",
    headers={"Authorization": "Bearer ..."},
)
channel.send("Trade executed: BUY 100 AAPL @ $185")
```

---

## Smart Alerts

The `SmartAlerts` module provides intelligent alert routing based on urgency and market hours:

```python
from src.notifications.smart_alerts import SmartAlerts

alerts = SmartAlerts(hub=hub)
alerts.configure(
    critical_channels=["telegram", "email"],
    info_channels=["console", "discord"],
)
```

---

## CLI Configuration

Configure notifications in `finclaw.yml`:

```yaml
notifications:
  telegram_token: "${TELEGRAM_BOT_TOKEN}"
  telegram_chat_id: "${TELEGRAM_CHAT_ID}"
  discord_webhook: "${DISCORD_WEBHOOK_URL}"
  slack_webhook: null
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    username: null
    password: null
```

---

## Writing Custom Channels

Implement the `NotificationChannel` interface:

```python
from src.notifications.base import NotificationChannel, NotificationLevel

class SlackChannel(NotificationChannel):
    @property
    def name(self) -> str:
        return "slack"

    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        # Your Slack API integration here
        ...
        return True
```

Register it:

```python
hub.register_channel("slack", SlackChannel())
```
