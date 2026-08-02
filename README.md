# budget-mcp

MCP server for budget tooling, built on the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

Currently a bare scaffold: one placeholder tool, `ping`, which returns `"pong"`.
No real budget functionality yet — this exists to confirm the server plumbing
and the Claude Desktop connection work end-to-end before building anything real.

## Project layout

```
budget-mcp/
├── pyproject.toml
├── src/
│   └── budget_mcp/
│       ├── __init__.py
│       └── server.py     # MCPServer instance + tools
└── .venv/                # local virtualenv (gitignored)
```

## Requirements

- Python 3.10+ (this project was set up with Python 3.12 via Homebrew:
  `brew install python@3.12`)

## Setup

```bash
cd budget-mcp
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -e .
```

> **macOS + iCloud Drive gotcha:** if `~/Desktop` is synced via iCloud Drive,
> the editable install's `_editable_impl_budget_mcp.pth` file in
> `.venv/lib/python3.12/site-packages/` can end up with the macOS "hidden"
> file flag set, which makes Python 3.12 skip it — `import budget_mcp` will
> fail with `ModuleNotFoundError` even though the install "succeeded". If
> that happens, run:
> ```bash
> chflags nohidden .venv/lib/python3.12/site-packages/_editable_impl_budget_mcp.pth
> ```
> This is why the Claude Desktop config below points directly at
> `server.py` by path rather than relying on the installed package/entry
> point — it sidesteps the issue entirely for running the server.

## Running locally

Run the server directly (it speaks MCP over stdio):

```bash
.venv/bin/python src/budget_mcp/server.py
```

It will sit waiting for an MCP client to talk to it over stdin/stdout — that's
expected, it's not meant to be run interactively.

To poke at it with the official inspector UI instead:

```bash
.venv/bin/mcp dev src/budget_mcp/server.py
```

## Connecting to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and add
an `mcpServers` entry:

```json
{
  "mcpServers": {
    "budget-mcp": {
      "command": "/Users/hamza/Desktop/projects/budget-mcp/.venv/bin/python",
      "args": [
        "/Users/hamza/Desktop/projects/budget-mcp/src/budget_mcp/server.py"
      ]
    }
  }
}
```

Then fully quit and reopen Claude Desktop. In a new conversation, the `ping`
tool should be available (look for the tools/hammer icon) — ask Claude to
call it and confirm it returns `"pong"`.

## Notes

- Uses MCP Python SDK **v2** (`mcp.server.MCPServer`, formerly `FastMCP` in
  v1.x). Requires `mcp>=1.2.0` per `pyproject.toml`, but what's actually
  installed here is the current 2.x line.
- Once the plumbing is confirmed working end-to-end, real tools replace/join
  `ping` in `src/budget_mcp/server.py`.
