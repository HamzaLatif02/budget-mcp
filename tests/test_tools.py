"""
End-to-end tests for the MCP tools, run against a real server subprocess
over the actual MCP protocol (not direct function calls) — same path
Claude Desktop uses. Each test gets its own throwaway SQLite db via
BUDGET_MCP_DB_PATH, so nothing here touches your real budget.db.

Run with:
    .venv/bin/pytest tests/ -v
"""

import asyncio
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from budget_mcp.db import SCHEMA_SQL

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

# Anchor "this month" / "last month" scenarios to real dates so the tests
# stay correct no matter when they're run.
TODAY = date.today()
THIS_MONTH = TODAY.replace(day=1)
LAST_MONTH = (THIS_MONTH - timedelta(days=1)).replace(day=1)

SEED_BUDGETS = [
    ("groceries", 50_000),   # $500.00 limit
    ("rent", 180_000),       # $1,800.00 limit
    ("entertainment", 15_000),  # $150.00 limit
    ("income", 0),           # not a spending category; limit is unused
]


def seed_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.executemany(
        "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)", SEED_BUDGETS
    )
    conn.commit()
    conn.close()


async def call_tools(db_path: Path, calls: list[tuple[str, dict]]) -> list:
    """Run a sequence of tool calls against one server instance/db and return the results."""
    params = StdioServerParameters(
        command=str(PYTHON),
        args=["-m", "budget_mcp.server"],
        env={"PYTHONPATH": str(SRC), "BUDGET_MCP_DB_PATH": str(db_path)},
    )
    results = []
    async with Client(stdio_client(params)) as client:
        for tool, args in calls:
            results.append(await client.call_tool(tool, args))
    return results


def run(db_path: Path, calls: list[tuple[str, dict]]) -> list:
    return asyncio.run(call_tools(db_path, calls))


def ok(result) -> dict:
    assert not result.is_error, f"expected success, got error: {result.content[0].text}"
    return json.loads(result.content[0].text)


def error_text(result) -> str:
    assert result.is_error, "expected an error, got a successful result"
    return result.content[0].text


@pytest.fixture
def db(tmp_path) -> Path:
    path = tmp_path / "test.db"
    seed_db(path)
    return path


# --- ping -------------------------------------------------------------


def test_ping(db):
    [result] = run(db, [("ping", {})])
    assert not result.is_error
    assert result.content[0].text == "pong"


# --- add_transaction: happy paths --------------------------------------


def test_add_expense_transaction(db):
    [result] = run(
        db,
        [
            (
                "add_transaction",
                dict(
                    date=THIS_MONTH.isoformat(),
                    amount=-62.18,
                    category="groceries",
                    source="checking",
                    note="Weekly shop",
                ),
            )
        ],
    )
    body = ok(result)
    assert body["transaction"]["amount_dollars"] == -62.18
    assert body["transaction"]["note"] == "Weekly shop"
    assert body["category_running_total_dollars"] == -62.18


def test_add_income_transaction_no_note(db):
    [result] = run(
        db,
        [
            (
                "add_transaction",
                dict(date=THIS_MONTH.isoformat(), amount=3000.00, category="income", source="checking"),
            )
        ],
    )
    body = ok(result)
    assert body["transaction"]["amount_dollars"] == 3000.00
    assert body["transaction"]["note"] is None


def test_running_total_accumulates_within_month(db):
    results = run(
        db,
        [
            ("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-62.18, category="groceries", source="checking")),
            ("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-37.82, category="groceries", source="cash")),
        ],
    )
    first, second = (ok(r) for r in results)
    assert first["category_running_total_dollars"] == -62.18
    assert second["category_running_total_dollars"] == -100.00  # accumulated, exact — no float drift


# --- add_transaction: validation ---------------------------------------


def test_add_transaction_rejects_bad_date(db):
    [result] = run(db, [("add_transaction", dict(date="08/02/2026", amount=-10, category="groceries", source="cash"))])
    assert "YYYY-MM-DD" in error_text(result)


def test_add_transaction_rejects_zero_amount(db):
    [result] = run(db, [("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=0, category="groceries", source="cash"))])
    assert "cannot be zero" in error_text(result)


def test_add_transaction_rejects_subcent_precision(db):
    [result] = run(db, [("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-10.005, category="groceries", source="cash"))])
    assert "sub-cent precision" in error_text(result)


def test_add_transaction_rejects_unknown_category(db):
    [result] = run(db, [("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-10, category="crypto", source="cash"))])
    msg = error_text(result)
    assert "Unknown category" in msg
    assert "groceries" in msg  # lists the valid options


def test_add_transaction_rejects_empty_source(db):
    [result] = run(db, [("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-10, category="groceries", source="   "))])
    assert "source" in error_text(result)


# --- get_spending_summary: happy paths ----------------------------------


def test_spending_summary_this_month_by_category(db):
    run(
        db,
        [
            ("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-1800.00, category="rent", source="checking")),
            ("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-100.00, category="groceries", source="checking")),
            ("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=3000.00, category="income", source="checking")),
        ],
    )
    [result] = run(db, [("get_spending_summary", dict(period="this_month", group_by="category"))])
    body = ok(result)

    assert body["total_spend_dollars"] == 1900.00  # income excluded from "spend"
    by_category = {g["category"]: g for g in body["groups"]}
    assert by_category["rent"]["total_dollars"] == 1800.00
    assert by_category["rent"]["percent_of_total"] == pytest.approx(94.74, abs=0.01)
    assert by_category["groceries"]["total_dollars"] == 100.00
    assert "income" not in by_category  # income isn't spending, shouldn't appear


def test_spending_summary_last_month_by_source(db):
    run(db, [("add_transaction", dict(date=LAST_MONTH.isoformat(), amount=-45.00, category="entertainment", source="cash"))])
    [result] = run(db, [("get_spending_summary", dict(period="last_month", group_by="source"))])
    body = ok(result)

    assert body["total_spend_dollars"] == 45.00
    assert body["groups"] == [
        {"source": "cash", "total_dollars": 45.00, "transaction_count": 1, "percent_of_total": 100.0}
    ]


def test_spending_summary_custom_range_spans_months(db):
    run(
        db,
        [
            ("add_transaction", dict(date=LAST_MONTH.isoformat(), amount=-45.00, category="entertainment", source="cash")),
            ("add_transaction", dict(date=THIS_MONTH.isoformat(), amount=-100.00, category="groceries", source="checking")),
        ],
    )
    [result] = run(
        db,
        [
            (
                "get_spending_summary",
                dict(period="custom", group_by="category", start_date=LAST_MONTH.isoformat(), end_date=TODAY.isoformat()),
            )
        ],
    )
    body = ok(result)
    assert body["total_spend_dollars"] == 145.00
    assert {g["category"] for g in body["groups"]} == {"entertainment", "groceries"}


# --- get_spending_summary: validation ------------------------------------


def test_spending_summary_rejects_bad_period(db):
    [result] = run(db, [("get_spending_summary", dict(period="next_month", group_by="category"))])
    assert "period must be one of" in error_text(result)


def test_spending_summary_rejects_bad_group_by(db):
    [result] = run(db, [("get_spending_summary", dict(period="this_month", group_by="account"))])
    assert "group_by must be one of" in error_text(result)


def test_spending_summary_custom_requires_dates(db):
    [result] = run(db, [("get_spending_summary", dict(period="custom", group_by="category"))])
    assert "requires both start_date and end_date" in error_text(result)
