# Deployment

FinClaw supports Docker deployment for running the API server, MCP server, or scheduled tasks in a containerized environment.

---

## Docker

### Quick Start

```bash
# Build the image
docker build -t finclaw .

# Run the API server
docker run -p 8080:8080 finclaw

# Run with environment variables
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=sk-... \
  -e TELEGRAM_BOT_TOKEN=... \
  finclaw
```

### Dockerfile

FinClaw ships with a production-ready Dockerfile:

- **Base image:** `python:3.12-slim` for minimal size
- **Non-root user:** Runs as `finclaw` user for security
- **Health check:** Built-in HTTP health check on `/api/v1/health`
- **Exposed port:** `8080` for the API server

### Docker Compose

The included `docker-compose.yml` provides two services:

```bash
docker-compose up -d
```

| Service | Description | Port |
|---------|-------------|------|
| `finclaw` | CLI/task runner with persistent data volume | — |
| `finclaw-api` | REST API server with health check | 8080 |

**Features:**

- Volume mount for persistent data (`./data:/app/data`)
- Environment variable passthrough for API keys
- Restart policy (`unless-stopped`)
- Resource limits (memory and CPU)
- Health checks with interval/timeout configuration

### Configuration

Environment variables for Docker:

| Variable | Description | Default |
|----------|-------------|---------|
| `FINCLAW_PORT` | API server port | `8080` |
| `FINCLAW_HOST` | Bind address | `0.0.0.0` |
| `FINCLAW_WORKERS` | Number of worker processes | `2` |
| `FINCLAW_LOG_LEVEL` | Log level | `info` |
| `OPENAI_API_KEY` | OpenAI API key (for AI features) | — |
| `ANTHROPIC_API_KEY` | Anthropic API key (for AI features) | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL | — |

---

## DeploymentConfig

Use the `DeploymentConfig` class to manage deployment settings programmatically:

```python
from src.deploy import DeploymentConfig

# From environment variables
config = DeploymentConfig.from_env()
print(config.port)     # 8080
print(config.workers)  # 2

# Custom configuration
config = DeploymentConfig(
    port=9090,
    workers=4,
    host="0.0.0.0",
    log_level="warning",
)
assert config.validate()

# Generate .env file
env_content = config.to_env_string()
with open(".env", "w") as f:
    f.write(env_content)
```

---

## Production Recommendations

1. **Use a reverse proxy** — Put Nginx or Traefik in front of the API server
2. **Set resource limits** — Use Docker's `--memory` and `--cpus` flags
3. **Mount volumes** — Persist cache and data with `-v ./data:/app/data`
4. **Use secrets** — Don't bake API keys into images; use environment variables or Docker secrets
5. **Health checks** — The built-in health endpoint at `/api/v1/health` is monitored automatically
6. **Logging** — Set `FINCLAW_LOG_LEVEL=warning` in production to reduce noise

---

## CI/CD

The `.github/workflows/release.yml` workflow automatically builds and publishes to PyPI on version tags:

```bash
git tag v5.1.0
git push origin v5.1.0
# → Triggers build + PyPI publish
```

For Docker image publishing, add a step to your CI:

```yaml
- name: Build and push Docker image
  run: |
    docker build -t ghcr.io/neuzhou/finclaw:${{ github.ref_name }} .
    docker push ghcr.io/neuzhou/finclaw:${{ github.ref_name }}
```
