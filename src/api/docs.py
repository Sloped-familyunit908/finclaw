"""
OpenAPI/Swagger documentation generator for FinClaw REST API.
"""

from __future__ import annotations

import json
from typing import Any


class APIDocGenerator:
    """Generate OpenAPI 3.0 spec and Swagger UI for FinClaw API."""

    def __init__(self, title: str = "FinClaw API", version: str = "5.1.0"):
        self.title = title
        self.version = version

    def generate_openapi_spec(self) -> dict:
        """Generate OpenAPI 3.0 specification."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "FinClaw — AI-Powered Financial Intelligence Engine REST API",
                "license": {"name": "MIT"},
            },
            "servers": [{"url": "/api/v1", "description": "API v1"}],
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health check",
                        "operationId": "healthCheck",
                        "responses": {"200": {"description": "Server status"}},
                    }
                },
                "/exchanges": {
                    "get": {
                        "summary": "List available exchanges",
                        "operationId": "listExchanges",
                        "responses": {"200": {"description": "List of exchanges"}},
                    }
                },
                "/quote/{exchange}/{symbol}": {
                    "get": {
                        "summary": "Get quote for a symbol",
                        "operationId": "getQuote",
                        "parameters": [
                            {"name": "exchange", "in": "path", "required": True, "schema": {"type": "string"}},
                            {"name": "symbol", "in": "path", "required": True, "schema": {"type": "string"}},
                        ],
                        "responses": {"200": {"description": "Quote data"}},
                    }
                },
                "/history/{exchange}/{symbol}": {
                    "get": {
                        "summary": "Get OHLCV history",
                        "operationId": "getHistory",
                        "parameters": [
                            {"name": "exchange", "in": "path", "required": True, "schema": {"type": "string"}},
                            {"name": "symbol", "in": "path", "required": True, "schema": {"type": "string"}},
                            {"name": "timeframe", "in": "query", "schema": {"type": "string", "default": "1d"}},
                            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 100}},
                        ],
                        "responses": {"200": {"description": "OHLCV candles"}},
                    }
                },
                "/strategies": {
                    "get": {
                        "summary": "List available strategies",
                        "operationId": "listStrategies",
                        "responses": {"200": {"description": "List of strategies"}},
                    }
                },
                "/backtest": {
                    "post": {
                        "summary": "Run a backtest",
                        "operationId": "runBacktest",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "symbol": {"type": "string"},
                                            "strategy": {"type": "string"},
                                            "start": {"type": "string", "format": "date"},
                                            "end": {"type": "string", "format": "date"},
                                            "capital": {"type": "number", "default": 10000},
                                        },
                                        "required": ["symbol", "strategy"],
                                    }
                                }
                            },
                        },
                        "responses": {"200": {"description": "Backtest results"}},
                    }
                },
                "/portfolio": {
                    "get": {
                        "summary": "Get portfolio status",
                        "operationId": "getPortfolio",
                        "responses": {"200": {"description": "Portfolio data"}},
                    }
                },
                "/alerts": {
                    "get": {
                        "summary": "List alerts",
                        "operationId": "listAlerts",
                        "responses": {"200": {"description": "List of alerts"}},
                    },
                    "post": {
                        "summary": "Create an alert",
                        "operationId": "createAlert",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "symbol": {"type": "string"},
                                            "condition": {"type": "string", "enum": ["above", "below"]},
                                            "price": {"type": "number"},
                                        },
                                        "required": ["symbol", "condition", "price"],
                                    }
                                }
                            },
                        },
                        "responses": {"201": {"description": "Alert created"}},
                    },
                },
                "/paper/portfolio": {
                    "get": {
                        "summary": "Get paper trading portfolio",
                        "operationId": "getPaperPortfolio",
                        "responses": {
                            "200": {"description": "Paper trading portfolio with positions, cash, and P&L"},
                        },
                    }
                },
                "/paper/trades": {
                    "get": {
                        "summary": "Get paper trading trade history",
                        "operationId": "getPaperTrades",
                        "parameters": [
                            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                        ],
                        "responses": {
                            "200": {"description": "List of executed paper trades"},
                        },
                    }
                },
                "/paper/order": {
                    "post": {
                        "summary": "Place a paper trading order",
                        "operationId": "placePaperOrder",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "symbol": {"type": "string", "description": "Ticker symbol"},
                                            "side": {"type": "string", "enum": ["buy", "sell"]},
                                            "quantity": {"type": "number", "description": "Number of shares/units"},
                                            "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                                            "limit_price": {"type": "number", "description": "Limit price (required for limit orders)"},
                                        },
                                        "required": ["symbol", "side", "quantity"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {"description": "Order result with fill details"},
                            "400": {"description": "Invalid order parameters"},
                        },
                    }
                },
                "/indicators": {
                    "get": {
                        "summary": "List available technical indicators",
                        "operationId": "listIndicators",
                        "responses": {
                            "200": {"description": "List of supported technical indicators with parameters"},
                        },
                    }
                },
                "/risk/metrics": {
                    "post": {
                        "summary": "Calculate risk metrics for a return series",
                        "operationId": "calculateRiskMetrics",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "returns": {
                                                "type": "array",
                                                "items": {"type": "number"},
                                                "description": "Array of daily returns",
                                            },
                                            "confidence": {"type": "number", "default": 0.95},
                                            "risk_free_rate": {"type": "number", "default": 0.0},
                                        },
                                        "required": ["returns"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {"description": "Risk metrics including VaR, Sharpe, Sortino, max drawdown"},
                        },
                    }
                },
                "/mcp/tools": {
                    "get": {
                        "summary": "List available MCP tools",
                        "operationId": "listMCPTools",
                        "responses": {
                            "200": {"description": "List of MCP server tools and their schemas"},
                        },
                    }
                },
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    },
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                    },
                }
            },
            "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
        }

    def serve_docs_html(self) -> str:
        """Generate Swagger UI HTML page."""
        spec_json = json.dumps(self.generate_openapi_spec())
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{self.title} — Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({{
      spec: {spec_json},
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: "StandaloneLayout"
    }});
  </script>
</body>
</html>"""
