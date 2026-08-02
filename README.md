# budget-mcp

MCP server for budget tooling, built on the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Project layout

```
budget-mcp/
├── pyproject.toml
├── budget.db              # SQLite db, created by init_db.py (gitignored)
├── src/
│   └── budget_mcp/
│       ├── __init__.py
│       ├── server.py      # MCPServer instance + tools
│       ├── db.py          # schema DDL + connection helper
│       ├── init_db.py     # resets budget.db and seeds example rows
│       ├── money.py       # dollars <-> integer-cents conversion
│       ├── dates.py       # date validation + period resolution
│       ├── categorizer.py # LLM-based transaction categorizer
│       └── eval_categorizer.py  # accuracy check against a labeled set
├── tests/
│   ├── conftest.py         # puts src/ on sys.path for test collection
│   └── test_tools.py       # end-to-end tool tests, see "Tests" below
└── .venv/                 # local virtualenv (gitignored)
```

## Requirements

- Python 3.10+ (this project was set up with Python 3.12 via Homebrew:
  `brew install python@3.12`)

## Setup

```bash
cd budget-mcp
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
PYTHONPATH=src .venv/bin/python -m budget_mcp.init_db   # creates + seeds budget.db
```

> **macOS + iCloud Drive gotcha:** if `~/Desktop` is synced via iCloud Drive,
> the editable install's `_editable_impl_budget_mcp.pth` file in
> `.venv/lib/python3.12/site-packages/` can end up with the macOS "hidden"
> file flag set, which makes Python 3.12 skip it — a bare `import budget_mcp`
> (e.g. in a REPL or test) will fail with `ModuleNotFoundError` even though
> the install "succeeded". If that happens, run:
> ```bash
> chflags nohidden .venv/lib/python3.12/site-packages/_editable_impl_budget_mcp.pth
> ```
> This doesn't affect running the server or the init script below — both are
> invoked with `PYTHONPATH=src`, which sidesteps the editable-install
> mechanism entirely.

`categorize_transaction` calls the Anthropic API, so it needs a key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Add the same variable to the `env` block in the Claude Desktop config below so
it's available when Claude Desktop launches the server.

## Database

Three tables (see `src/budget_mcp/db.py` for the full DDL):

- `budgets(category PK, monthly_limit)`
- `transactions(id, date, amount, category -> budgets.category, source, note)`
- `savings_goals(id, name, target_amount, current_amount, account_type)`

All money columns are **integer cents** (e.g. `50000` == $500.00) to avoid
float rounding — SQLite has no real `DECIMAL` type. `transactions.amount` is
signed: negative = expense, positive = income.

Re-run `PYTHONPATH=src .venv/bin/python -m budget_mcp.init_db` any time to
wipe `budget.db` and reset it to the seed data.

## Tools

- **`ping()`** — placeholder, returns `"pong"`.
- **`add_transaction(date, amount, category, source, note=None)`** — inserts
  a transaction and returns it plus the category's running total for that
  transaction's calendar month. `amount` is dollars (e.g. `-45.67`); `date`
  must be `YYYY-MM-DD`; `category` must already exist in `budgets`. Rejects
  bad dates, zero/non-finite/sub-cent amounts, unknown categories, and empty
  `source` with a clear error message (no stack traces).
- **`get_spending_summary(period, group_by, start_date=None, end_date=None)`**
  — sums expense transactions (`amount < 0`) over `period` (`"this_month"`,
  `"last_month"`, or `"custom"` with `start_date`/`end_date`), grouped by
  `"category"` or `"source"`, and returns each group's total plus % of total
  spend. Rejects unknown `period`/`group_by` values and missing/invalid
  custom-range dates.
- **`categorize_transaction(description)`** — classifies a raw statement line
  (e.g. `"TESCO STORES 3421 LONDON"`) into one of `rent`, `food`, `transport`,
  `savings`, `business_expense`, `entertainment`, `other`, via a Claude Haiku
  4.5 call with structured JSON output (`category`, `confidence`, `reasoning`).
  The returned category is checked against the fixed list before being
  returned — an invalid category from the model surfaces as an error rather
  than being trusted. Requires `ANTHROPIC_API_KEY` (see Setup above).

## Tests

```bash
.venv/bin/pytest tests/ -v
```

Each test spawns a real server subprocess and drives it through the actual
MCP protocol (same path Claude Desktop uses), against a fresh throwaway
SQLite db (via `BUDGET_MCP_DB_PATH`) — your real `budget.db` is never
touched. Covers both tools' happy paths (including that running totals and
spend percentages come out exact, not float-drifted) and every validation
rejection (bad dates, zero/non-finite/sub-cent amounts, unknown categories,
empty source, bad `period`/`group_by`, missing custom-range dates).

`categorize_transaction` isn't in this suite — LLM output isn't deterministic,
so it doesn't belong in a pass/fail unit test. Instead, check its accuracy
against 15 hand-labeled realistic statement lines:

```bash
PYTHONPATH=src .venv/bin/python -m budget_mcp.eval_categorizer
```

This calls the live API (needs `ANTHROPIC_API_KEY`) and prints a pass/fail
per example plus overall accuracy.

## Running locally

Run the server directly (it speaks MCP over stdio):

```bash
PYTHONPATH=src .venv/bin/python -m budget_mcp.server
```

It will sit waiting for an MCP client to talk to it over stdin/stdout — that's
expected, it's not meant to be run interactively.

To poke at it with the official inspector UI instead:

```bash
PYTHONPATH=src .venv/bin/mcp dev src/budget_mcp/server.py
```

## Connecting to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and add
an `mcpServers` entry:

```json
{
  "mcpServers": {
    "budget-mcp": {
      "command": "/Users/hamza/Desktop/projects/budget-mcp/.venv/bin/python",
      "args": ["-m", "budget_mcp.server"],
      "env": {
        "PYTHONPATH": "/Users/hamza/Desktop/projects/budget-mcp/src",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Then fully quit and reopen Claude Desktop. In a new conversation, the tools
should be available (look for the tools/hammer icon) — try asking Claude to
call `ping`, then to add a transaction or get a spending summary.

## Notes

- Uses MCP Python SDK **v2** (`mcp.server.MCPServer`, formerly `FastMCP` in
  v1.x). Requires `mcp>=1.2.0` per `pyproject.toml`, but what's actually
  installed here is the current 2.x line.
- Tool validation errors are raised as
  `mcp.server.mcpserver.exceptions.ToolError`, which the framework returns
  to the client as a plain error message — never a Python traceback.
