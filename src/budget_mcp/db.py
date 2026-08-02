import os
import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "budget.db"
DB_PATH = Path(os.environ["BUDGET_MCP_DB_PATH"]) if os.environ.get("BUDGET_MCP_DB_PATH") else _DEFAULT_DB_PATH

SCHEMA_SQL = """
-- All money columns (monthly_limit, amount, target_amount, current_amount)
-- are stored as integer cents to avoid float rounding; divide by 100 for dollars.
CREATE TABLE IF NOT EXISTS budgets (
    category      TEXT PRIMARY KEY,
    monthly_limit INTEGER NOT NULL CHECK (monthly_limit >= 0)
);

CREATE TABLE IF NOT EXISTS transactions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    date     TEXT NOT NULL,
    amount   INTEGER NOT NULL,
    category TEXT NOT NULL REFERENCES budgets(category),
    source   TEXT NOT NULL,
    note     TEXT
);

CREATE TABLE IF NOT EXISTS savings_goals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    target_amount  INTEGER NOT NULL CHECK (target_amount >= 0),
    current_amount INTEGER NOT NULL DEFAULT 0 CHECK (current_amount >= 0),
    account_type   TEXT NOT NULL
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
