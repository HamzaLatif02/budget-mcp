from budget_mcp.db import DB_PATH, SCHEMA_SQL, get_connection

SEED_BUDGETS = [
    ("groceries", 500.0),
    ("rent", 1800.0),
    ("entertainment", 150.0),
]

SEED_TRANSACTIONS = [
    ("2026-07-15", -62.18, "groceries", "checking", "Trader Joe's"),
    ("2026-08-01", -1800.00, "rent", "checking", "August rent"),
]

SEED_SAVINGS_GOALS = [
    ("Emergency Fund", 10000.0, 3250.0, "high-yield savings"),
    ("Vacation", 3000.0, 900.0, "brokerage"),
]


def main() -> None:
    DB_PATH.unlink(missing_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)

        conn.executemany(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)",
            SEED_BUDGETS,
        )
        conn.executemany(
            "INSERT INTO transactions (date, amount, category, source, note) "
            "VALUES (?, ?, ?, ?, ?)",
            SEED_TRANSACTIONS,
        )
        conn.executemany(
            "INSERT INTO savings_goals (name, target_amount, current_amount, account_type) "
            "VALUES (?, ?, ?, ?)",
            SEED_SAVINGS_GOALS,
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Initialized {DB_PATH} with schema + seed data.")


if __name__ == "__main__":
    main()
