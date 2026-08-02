from mcp.server import MCPServer

mcp = MCPServer("budget-mcp")


@mcp.tool()
def ping() -> str:
    """Placeholder tool to verify the server is wired up correctly."""
    return "pong"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
