"""
API Key Authentication for FinClaw REST API.
Simple token-based auth with key generation and validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Callable


class APIAuth:
    """API key authentication manager."""

    def __init__(self, keys_file: str | None = None):
        self._keys_file = Path(keys_file) if keys_file else Path.home() / ".finclaw" / "api_keys.json"
        self._keys: dict[str, dict] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        if self._keys_file.exists():
            try:
                with open(self._keys_file) as f:
                    self._keys = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._keys = {}

    def _save_keys(self) -> None:
        self._keys_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._keys_file, "w") as f:
            json.dump(self._keys, f, indent=2)

    def generate_key(self, name: str = "default") -> str:
        """Generate a new API key."""
        raw = secrets.token_urlsafe(32)
        key = f"fc_{raw}"
        key_hash = self._hash(key)
        self._keys[key_hash] = {
            "name": name,
            "created": time.time(),
            "active": True,
        }
        self._save_keys()
        return key

    def validate_key(self, key: str) -> bool:
        """Validate an API key."""
        if not key:
            return False
        key_hash = self._hash(key)
        entry = self._keys.get(key_hash)
        return entry is not None and entry.get("active", False)

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = self._hash(key)
        if key_hash in self._keys:
            self._keys[key_hash]["active"] = False
            self._save_keys()
            return True
        return False

    def list_keys(self) -> list[dict]:
        """List all registered keys (metadata only, not the actual keys)."""
        return [{"hash": h[:12] + "...", **v} for h, v in self._keys.items()]

    @staticmethod
    def _hash(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def extract_key(headers: dict) -> str | None:
        """Extract API key from request headers."""
        auth = headers.get("Authorization", headers.get("authorization", ""))
        if auth.startswith("Bearer "):
            return auth[7:]
        return headers.get("X-API-Key", headers.get("x-api-key"))
