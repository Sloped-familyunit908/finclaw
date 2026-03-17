FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r finclaw && useradd -r -g finclaw -d /app -s /sbin/nologin finclaw

# Install dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e ".[full]" 2>/dev/null || \
    pip install --no-cache-dir yfinance aiohttp numpy pyyaml scipy

# Copy application code
COPY src/ ./src/
COPY strategies/ ./strategies/
COPY agents/ ./agents/
COPY finclaw.py main.py mcp_server.py ./
COPY finclaw.yml ./

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
