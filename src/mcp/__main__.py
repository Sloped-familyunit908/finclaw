"""
Entry point: python -m src.mcp serve
"""

import sys


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "serve":
        print("Usage: python -m src.mcp serve", file=sys.stderr)
        sys.exit(1)

    from src.mcp.server import FinClawMCPServer
    from src.mcp.protocol import MCPProtocol

    server = FinClawMCPServer()
    protocol = MCPProtocol(server)
    try:
        protocol.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
