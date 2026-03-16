"""
MCP Config Generator — produce JSON configs for Claude Desktop, Cursor, OpenClaw, etc.
"""

from __future__ import annotations

import json
import sys


class MCPConfigGenerator:
    """Generate MCP client configuration snippets."""

    @staticmethod
    def _python_cmd() -> str:
        return sys.executable or "python"

    @staticmethod
    def claude_desktop() -> dict:
        return {
            "mcpServers": {
                "finclaw": {
                    "command": MCPConfigGenerator._python_cmd(),
                    "args": ["-m", "src.mcp", "serve"],
                    "env": {},
                }
            }
        }

    @staticmethod
    def cursor() -> dict:
        return {
            "mcpServers": {
                "finclaw": {
                    "command": MCPConfigGenerator._python_cmd(),
                    "args": ["-m", "src.mcp", "serve"],
                }
            }
        }

    @staticmethod
    def openclaw() -> dict:
        return {
            "mcp": [
                {
                    "name": "finclaw",
                    "transport": "stdio",
                    "command": MCPConfigGenerator._python_cmd(),
                    "args": ["-m", "src.mcp", "serve"],
                }
            ]
        }

    @staticmethod
    def vscode() -> dict:
        return {
            "mcp": {
                "servers": {
                    "finclaw": {
                        "type": "stdio",
                        "command": MCPConfigGenerator._python_cmd(),
                        "args": ["-m", "src.mcp", "serve"],
                    }
                }
            }
        }

    @staticmethod
    def generic() -> dict:
        return {
            "command": MCPConfigGenerator._python_cmd(),
            "args": ["-m", "src.mcp", "serve"],
            "transport": "stdio",
        }

    @classmethod
    def for_client(cls, client: str) -> dict:
        clients = {
            "claude": cls.claude_desktop,
            "cursor": cls.cursor,
            "openclaw": cls.openclaw,
            "vscode": cls.vscode,
            "generic": cls.generic,
        }
        fn = clients.get(client.lower())
        if fn is None:
            raise ValueError(f"Unknown client: {client}. Available: {', '.join(clients)}")
        return fn()

    @classmethod
    def print_config(cls, client: str) -> None:
        config = cls.for_client(client)
        print(json.dumps(config, indent=2))
