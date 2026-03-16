FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[all]" 2>/dev/null || pip install --no-cache-dir yfinance aiohttp numpy pyyaml scikit-learn pytest

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port for API server
EXPOSE 8080

# Default command
CMD ["python", "finclaw.py", "info"]
