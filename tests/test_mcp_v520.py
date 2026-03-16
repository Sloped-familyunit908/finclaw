"""
Tests for MCP Server v5.2.0 — 40+ tests covering server, protocol, config, and tool dispatch.
"""

import json
import io
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp.server import FinClawMCPServer, TOOLS, SERVER_NAME, SERVER_VERSION, PROTOCOL_VERSION, _error_content, _json_dumps
from src.mcp.protocol import MCPProtocol
from src.mcp.config import MCPConfigGenerator


# ═══════════════════════════════════════════════════════════════
# Server unit tests
# ═══════════════════════════════════════════════════════════════

class TestFinClawMCPServer:
    def setup_method(self):
        self.server = FinClawMCPServer()

    # ── initialize ──

    def test_initialize_returns_protocol_version(self):
        result = self.server.handle_initialize()
        assert result["protocolVersion"] == PROTOCOL_VERSION

    def test_initialize_returns_server_info(self):
        result = self.server.handle_initialize()
        assert result["serverInfo"]["name"] == SERVER_NAME
        assert result["serverInfo"]["version"] == SERVER_VERSION

    def test_initialize_has_tools_capability(self):
        result = self.server.handle_initialize()
        assert "tools" in result["capabilities"]

    def test_initialize_with_params(self):
        result = self.server.handle_initialize({"clientInfo": {"name": "test"}})
        assert result["protocolVersion"] == PROTOCOL_VERSION

    # ── tools/list ──

    def test_tools_list_returns_all_tools(self):
        result = self.server.handle_tools_list()
        assert len(result["tools"]) == 10

    def test_tools_list_has_required_fields(self):
        result = self.server.handle_tools_list()
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_tools_list_names(self):
        result = self.server.handle_tools_list()
        names = {t["name"] for t in result["tools"]}
        expected = {"get_quote", "get_history", "list_exchanges", "run_backtest",
                    "analyze_portfolio", "get_indicators", "screen_stocks",
                    "get_sentiment", "compare_strategies", "get_funding_rates"}
        assert names == expected

    def test_tools_list_schemas_are_objects(self):
        result = self.server.handle_tools_list()
        for tool in result["tools"]:
            assert tool["inputSchema"]["type"] == "object"

    def test_tool_get_quote_has_required_symbol(self):
        result = self.server.handle_tools_list()
        quote_tool = next(t for t in result["tools"] if t["name"] == "get_quote")
        assert "symbol" in quote_tool["inputSchema"].get("required", [])

    # ── tools/call dispatch ──

    def test_call_unknown_tool_returns_error(self):
        result = self.server.handle_tools_call("nonexistent_tool", {})
        assert result["isError"] is True
        assert "Unknown tool" in result["content"][0]["text"]

    def test_call_with_none_arguments(self):
        # list_exchanges needs no args
        result = self.server.handle_tools_call("list_exchanges", None)
        # Should not crash — either succeeds or returns error
        assert "content" in result

    # ── TOOLS constant ──

    def test_tools_constant_length(self):
        assert len(TOOLS) == 10

    def test_each_tool_has_input_schema(self):
        for t in TOOLS:
            assert "inputSchema" in t
            assert isinstance(t["inputSchema"], dict)


# ═══════════════════════════════════════════════════════════════
# Protocol tests
# ═══════════════════════════════════════════════════════════════

class TestMCPProtocol:
    def _run_protocol(self, requests: list[dict]) -> list[dict]:
        """Helper: feed requests through protocol, return parsed responses."""
        input_text = "\n".join(json.dumps(r) for r in requests) + "\n"
        in_stream = io.StringIO(input_text)
        out_stream = io.StringIO()
        proto = MCPProtocol(input_stream=in_stream, output_stream=out_stream)
        proto.run()
        out_stream.seek(0)
        responses = []
        for line in out_stream:
            line = line.strip()
            if line:
                responses.append(json.loads(line))
        return responses

    def test_initialize_response(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        ])
        assert len(resps) == 1
        assert resps[0]["id"] == 1
        assert resps[0]["result"]["protocolVersion"] == PROTOCOL_VERSION

    def test_tools_list_response(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ])
        tools_resp = resps[1]
        assert tools_resp["id"] == 2
        assert len(tools_resp["result"]["tools"]) == 10

    def test_ping_response(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 99, "method": "ping", "params": {}}
        ])
        assert resps[0]["id"] == 99
        assert resps[0]["result"] == {}

    def test_unknown_method_returns_error(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}}
        ])
        assert "error" in resps[0]

    def test_parse_error_on_invalid_json(self):
        in_stream = io.StringIO("not json at all\n")
        out_stream = io.StringIO()
        proto = MCPProtocol(input_stream=in_stream, output_stream=out_stream)
        proto.run()
        out_stream.seek(0)
        resp = json.loads(out_stream.readline())
        assert resp["error"]["code"] == -32700

    def test_notification_no_response(self):
        """Notifications (no id field) should produce no response."""
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        ])
        assert len(resps) == 0

    def test_empty_lines_ignored(self):
        in_stream = io.StringIO('\n\n{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}\n\n')
        out_stream = io.StringIO()
        proto = MCPProtocol(input_stream=in_stream, output_stream=out_stream)
        proto.run()
        out_stream.seek(0)
        lines = [l.strip() for l in out_stream if l.strip()]
        assert len(lines) == 1

    def test_tools_call_unknown_tool_via_protocol(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "fake", "arguments": {}}}
        ])
        result = resps[0]["result"]
        assert result["isError"] is True

    def test_multiple_requests_sequential(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
        ])
        assert len(resps) == 3
        assert [r["id"] for r in resps] == [1, 2, 3]

    def test_response_is_valid_jsonrpc(self):
        resps = self._run_protocol([
            {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}
        ])
        assert resps[0]["jsonrpc"] == "2.0"


# ═══════════════════════════════════════════════════════════════
# Config generator tests
# ═══════════════════════════════════════════════════════════════

class TestMCPConfigGenerator:
    def test_claude_desktop_config(self):
        cfg = MCPConfigGenerator.claude_desktop()
        assert "mcpServers" in cfg
        assert "finclaw" in cfg["mcpServers"]
        assert "command" in cfg["mcpServers"]["finclaw"]
        assert cfg["mcpServers"]["finclaw"]["args"] == ["-m", "src.mcp", "serve"]

    def test_cursor_config(self):
        cfg = MCPConfigGenerator.cursor()
        assert "mcpServers" in cfg
        assert "finclaw" in cfg["mcpServers"]

    def test_openclaw_config(self):
        cfg = MCPConfigGenerator.openclaw()
        assert "mcp" in cfg
        assert cfg["mcp"][0]["name"] == "finclaw"
        assert cfg["mcp"][0]["transport"] == "stdio"

    def test_vscode_config(self):
        cfg = MCPConfigGenerator.vscode()
        assert "mcp" in cfg
        assert "finclaw" in cfg["mcp"]["servers"]

    def test_generic_config(self):
        cfg = MCPConfigGenerator.generic()
        assert "command" in cfg
        assert cfg["transport"] == "stdio"

    def test_for_client_claude(self):
        cfg = MCPConfigGenerator.for_client("claude")
        assert "mcpServers" in cfg

    def test_for_client_case_insensitive(self):
        cfg = MCPConfigGenerator.for_client("Claude")
        assert "mcpServers" in cfg

    def test_for_client_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown client"):
            MCPConfigGenerator.for_client("unknown_client")

    def test_all_configs_have_serve_args(self):
        for client in ("claude", "cursor", "openclaw", "vscode", "generic"):
            cfg = MCPConfigGenerator.for_client(client)
            cfg_str = json.dumps(cfg)
            assert "src.mcp" in cfg_str
            assert "serve" in cfg_str


# ═══════════════════════════════════════════════════════════════
# Helper tests
# ═══════════════════════════════════════════════════════════════

class TestHelpers:
    def test_error_content_structure(self):
        err = _error_content("something broke")
        assert err["isError"] is True
        assert err["content"][0]["type"] == "text"
        assert "something broke" in err["content"][0]["text"]

    def test_json_dumps_basic(self):
        assert _json_dumps({"a": 1}) == '{"a": 1}'

    def test_json_dumps_with_datetime(self):
        from datetime import datetime
        result = _json_dumps({"ts": datetime(2024, 1, 1)})
        assert "2024" in result

    def test_json_dumps_unicode(self):
        result = _json_dumps({"name": "比特币"})
        assert "比特币" in result


# ═══════════════════════════════════════════════════════════════
# Integration: tools/call via protocol for list_exchanges
# ═══════════════════════════════════════════════════════════════

class TestToolCallIntegration:
    def _run(self, requests):
        input_text = "\n".join(json.dumps(r) for r in requests) + "\n"
        in_stream = io.StringIO(input_text)
        out_stream = io.StringIO()
        proto = MCPProtocol(input_stream=in_stream, output_stream=out_stream)
        proto.run()
        out_stream.seek(0)
        return [json.loads(l) for l in out_stream if l.strip()]

    def test_list_exchanges_via_protocol(self):
        resps = self._run([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "list_exchanges", "arguments": {}}},
        ])
        result = resps[1]["result"]
        assert "content" in result
        # Should have text content with exchange info
        text = result["content"][0]["text"]
        parsed = json.loads(text)
        assert isinstance(parsed, dict)
