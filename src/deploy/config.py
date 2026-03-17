"""
Deployment Configuration
========================
Manages deployment settings for FinClaw in containerized environments.
Reads configuration from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class DeploymentConfig:
    """Configuration for deploying FinClaw.

    Can be populated from environment variables via `from_env()`,
    or constructed directly with keyword arguments.
    """

    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 1
    log_level: str = "info"
    data_dir: str = "/app/data"
    cors_origin: str = "*"
    auth_enabled: bool = False
    api_key: str = ""
    max_requests: int = 100
    rate_limit_window: int = 60

    @classmethod
    def from_env(cls) -> "DeploymentConfig":
        """Create config from environment variables.

        Recognized env vars:
            FINCLAW_HOST, FINCLAW_PORT, FINCLAW_WORKERS,
            FINCLAW_LOG_LEVEL, FINCLAW_DATA_DIR, FINCLAW_CORS_ORIGIN,
            FINCLAW_AUTH_ENABLED, FINCLAW_API_KEY,
            FINCLAW_MAX_REQUESTS, FINCLAW_RATE_LIMIT_WINDOW
        """
        return cls(
            host=os.environ.get("FINCLAW_HOST", "0.0.0.0"),
            port=int(os.environ.get("FINCLAW_PORT", "8080")),
            workers=int(os.environ.get("FINCLAW_WORKERS", "1")),
            log_level=os.environ.get("FINCLAW_LOG_LEVEL", "info"),
            data_dir=os.environ.get("FINCLAW_DATA_DIR", "/app/data"),
            cors_origin=os.environ.get("FINCLAW_CORS_ORIGIN", "*"),
            auth_enabled=os.environ.get("FINCLAW_AUTH_ENABLED", "").lower() in ("1", "true", "yes"),
            api_key=os.environ.get("FINCLAW_API_KEY", ""),
            max_requests=int(os.environ.get("FINCLAW_MAX_REQUESTS", "100")),
            rate_limit_window=int(os.environ.get("FINCLAW_RATE_LIMIT_WINDOW", "60")),
        )

    def validate(self) -> bool:
        """Validate the configuration.

        Returns:
            True if configuration is valid, False otherwise.
        """
        if not (1 <= self.port <= 65535):
            return False
        if self.workers < 1:
            return False
        if self.log_level not in ("debug", "info", "warning", "error", "critical"):
            return False
        return True

    def to_env_string(self) -> str:
        """Generate .env file content from this configuration.

        Returns:
            String suitable for writing to a .env file.
        """
        lines = [
            f"FINCLAW_HOST={self.host}",
            f"FINCLAW_PORT={self.port}",
            f"FINCLAW_WORKERS={self.workers}",
            f"FINCLAW_LOG_LEVEL={self.log_level}",
            f"FINCLAW_DATA_DIR={self.data_dir}",
            f"FINCLAW_CORS_ORIGIN={self.cors_origin}",
            f"FINCLAW_AUTH_ENABLED={'true' if self.auth_enabled else 'false'}",
            f"FINCLAW_API_KEY={self.api_key}",
            f"FINCLAW_MAX_REQUESTS={self.max_requests}",
            f"FINCLAW_RATE_LIMIT_WINDOW={self.rate_limit_window}",
        ]
        return "\n".join(lines) + "\n"
