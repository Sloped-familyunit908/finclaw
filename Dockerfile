# ── Stage 1: Builder — install dependencies ──────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install \
    yfinance aiohttp numpy pyyaml scipy

# ── Stage 2: Runtime — minimal final image ──────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r finclaw && useradd -r -g finclaw -d /app -s /sbin/nologin finclaw

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY strategies/ ./strategies/
COPY agents/ ./agents/
COPY scripts/finclaw.py scripts/main.py scripts/mcp_server.py ./scripts/
COPY examples/finclaw.yml ./

# Create data directory
RUN mkdir -p /app/data && chown -R finclaw:finclaw /app

# Switch to non-root user
USER finclaw

# Expose port for API server
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health')" || exit 1

# Default command
CMD ["python", "-m", "src.api.server"]
