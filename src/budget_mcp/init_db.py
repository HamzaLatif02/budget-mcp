from budget_mcp.db import DB_PATH, SCHEMA_SQL, get_connection

# Amounts are integer cents (e.g. 50000 == $500.00).
SEED_BUDGETS = [
    ("groceries", 50_000),
    ("rent", 180_000),
    ("entertainment", 15_000),
]

SEED_TRANSACTIONS = [
    ("2026-07-15", -6_218, "groceries", "checking", "Trader Joe's"),
    ("2026-08-01", -180_000, "rent", "checking", "August rent"),
]

SEED_SAVINGS_GOALS = [
    ("Emergency Fund", 1_000_000, 325_000, "high-yield savings"),
    ("Vacation", 300_000, 90_000, "brokerage"),
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
