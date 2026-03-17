"""Tests for Issue #3: API documentation completeness.

Tests that API documentation is complete, accurate, and up-to-date:
- OpenAPI spec contains all endpoints
- All endpoints have proper request/response schemas
- Swagger UI HTML is generated correctly
- API reference covers all modules
- Documentation examples are valid
"""

import json

import pytest

from src.api.docs import APIDocGenerator


class TestAPIDocGeneratorBasic:
    def test_generate_spec_returns_dict(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        assert isinstance(spec, dict)
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

    def test_spec_version_matches(self):
        gen = APIDocGenerator(version="5.1.0")
        spec = gen.generate_openapi_spec()
        assert spec["info"]["version"] == "5.1.0"

    def test_spec_custom_title(self):
        gen = APIDocGenerator(title="My API")
        spec = gen.generate_openapi_spec()
        assert spec["info"]["title"] == "My API"

    def test_openapi_version_3(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        assert spec["openapi"].startswith("3.0")


class TestAPIDocEndpointCoverage:
    """Verify all REST API endpoints are documented in the OpenAPI spec."""

    def setup_method(self):
        self.gen = APIDocGenerator()
        self.spec = self.gen.generate_openapi_spec()
        self.paths = self.spec["paths"]

    def test_health_endpoint(self):
        assert "/health" in self.paths
        assert "get" in self.paths["/health"]

    def test_exchanges_endpoint(self):
        assert "/exchanges" in self.paths
        assert "get" in self.paths["/exchanges"]

    def test_quote_endpoint(self):
        assert "/quote/{exchange}/{symbol}" in self.paths
        assert "get" in self.paths["/quote/{exchange}/{symbol}"]

    def test_history_endpoint(self):
        assert "/history/{exchange}/{symbol}" in self.paths
        assert "get" in self.paths["/history/{exchange}/{symbol}"]

    def test_strategies_endpoint(self):
        assert "/strategies" in self.paths
        assert "get" in self.paths["/strategies"]

    def test_backtest_endpoint(self):
        assert "/backtest" in self.paths
        assert "post" in self.paths["/backtest"]

    def test_portfolio_endpoint(self):
        assert "/portfolio" in self.paths
        assert "get" in self.paths["/portfolio"]

    def test_alerts_get_endpoint(self):
        assert "/alerts" in self.paths
        assert "get" in self.paths["/alerts"]

    def test_alerts_post_endpoint(self):
        assert "/alerts" in self.paths
        assert "post" in self.paths["/alerts"]

    # New endpoints that should be documented
    def test_paper_trading_endpoint(self):
        assert "/paper/portfolio" in self.paths
        assert "get" in self.paths["/paper/portfolio"]

    def test_paper_trades_endpoint(self):
        assert "/paper/trades" in self.paths
        assert "get" in self.paths["/paper/trades"]

    def test_paper_order_endpoint(self):
        assert "/paper/order" in self.paths
        assert "post" in self.paths["/paper/order"]

    def test_indicators_endpoint(self):
        assert "/indicators" in self.paths
        assert "get" in self.paths["/indicators"]

    def test_risk_metrics_endpoint(self):
        assert "/risk/metrics" in self.paths
        assert "post" in self.paths["/risk/metrics"]

    def test_mcp_endpoint(self):
        assert "/mcp/tools" in self.paths
        assert "get" in self.paths["/mcp/tools"]


class TestAPIDocSchemas:
    """Verify request/response schemas are present and correct."""

    def setup_method(self):
        self.gen = APIDocGenerator()
        self.spec = self.gen.generate_openapi_spec()
        self.paths = self.spec["paths"]

    def test_backtest_has_request_body(self):
        backtest = self.paths["/backtest"]["post"]
        assert "requestBody" in backtest
        content = backtest["requestBody"]["content"]
        assert "application/json" in content
        schema = content["application/json"]["schema"]
        assert "properties" in schema
        assert "symbol" in schema["properties"]

    def test_quote_has_parameters(self):
        quote = self.paths["/quote/{exchange}/{symbol}"]["get"]
        assert "parameters" in quote
        param_names = [p["name"] for p in quote["parameters"]]
        assert "exchange" in param_names
        assert "symbol" in param_names

    def test_history_has_query_params(self):
        history = self.paths["/history/{exchange}/{symbol}"]["get"]
        assert "parameters" in history
        param_names = [p["name"] for p in history["parameters"]]
        assert "timeframe" in param_names
        assert "limit" in param_names

    def test_alerts_post_has_schema(self):
        alerts = self.paths["/alerts"]["post"]
        assert "requestBody" in alerts
        content = alerts["requestBody"]["content"]
        schema = content["application/json"]["schema"]
        assert "symbol" in schema["properties"]
        assert "condition" in schema["properties"]
        assert "price" in schema["properties"]

    def test_paper_order_has_schema(self):
        order = self.paths["/paper/order"]["post"]
        assert "requestBody" in order
        content = order["requestBody"]["content"]
        schema = content["application/json"]["schema"]
        assert "symbol" in schema["properties"]
        assert "side" in schema["properties"]
        assert "quantity" in schema["properties"]

    def test_risk_metrics_has_schema(self):
        risk = self.paths["/risk/metrics"]["post"]
        assert "requestBody" in risk
        content = risk["requestBody"]["content"]
        schema = content["application/json"]["schema"]
        assert "returns" in schema["properties"]


class TestAPIDocSecurity:
    def test_security_schemes_defined(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        assert "securitySchemes" in spec["components"]
        schemes = spec["components"]["securitySchemes"]
        assert "ApiKeyAuth" in schemes
        assert "BearerAuth" in schemes

    def test_global_security_defined(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        assert "security" in spec


class TestSwaggerUIHtml:
    def test_html_contains_swagger_ui(self):
        gen = APIDocGenerator()
        html = gen.serve_docs_html()
        assert "swagger-ui" in html
        assert "<html" in html
        assert "SwaggerUIBundle" in html

    def test_html_contains_spec(self):
        gen = APIDocGenerator()
        html = gen.serve_docs_html()
        # The spec should be embedded as JSON
        assert '"openapi"' in html
        assert '"paths"' in html

    def test_html_contains_title(self):
        gen = APIDocGenerator(title="TestAPI")
        html = gen.serve_docs_html()
        assert "TestAPI" in html


class TestOpenAPISpecValidity:
    """Validate the OpenAPI spec structure."""

    def test_spec_is_valid_json(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        # Should round-trip through JSON
        json_str = json.dumps(spec)
        parsed = json.loads(json_str)
        assert parsed == spec

    def test_all_paths_have_responses(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        for path, methods in spec["paths"].items():
            for method, details in methods.items():
                assert "responses" in details, f"{method.upper()} {path} missing responses"

    def test_all_path_params_declared(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        import re
        for path, methods in spec["paths"].items():
            # Find path parameters like {exchange}
            path_params = re.findall(r"\{(\w+)\}", path)
            for method, details in methods.items():
                if path_params:
                    declared = [p["name"] for p in details.get("parameters", []) if p["in"] == "path"]
                    for pp in path_params:
                        assert pp in declared, f"{method.upper()} {path}: path param '{pp}' not declared"

    def test_operation_ids_unique(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        op_ids = []
        for path, methods in spec["paths"].items():
            for method, details in methods.items():
                if "operationId" in details:
                    op_ids.append(details["operationId"])
        assert len(op_ids) == len(set(op_ids)), "Duplicate operationIds found"

    def test_all_endpoints_have_summary(self):
        gen = APIDocGenerator()
        spec = gen.generate_openapi_spec()
        for path, methods in spec["paths"].items():
            for method, details in methods.items():
                assert "summary" in details, f"{method.upper()} {path} missing summary"
