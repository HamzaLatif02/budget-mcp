from datetime import timedelta

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from budget_mcp.db import get_connection
from budget_mcp.dates import month_bounds, resolve_period, validate_iso_date
from budget_mcp.money import cents_to_dollars, dollars_to_cents

mcp = MCPServer("budget-mcp")

VALID_GROUP_BY = {"category", "source"}


@mcp.tool()
def ping() -> str:
    """Placeholder tool to verify the server is wired up correctly."""
    return "pong"


@mcp.tool()
def add_transaction(
    date: str,
    amount: float,
    category: str,
    source: str,
    note: str | None = None,
) -> dict:
    """Insert a transaction and return it plus the category's running total for its month.

    date: ISO 8601 'YYYY-MM-DD'.
    amount: dollars, signed (negative = expense, positive = income), precise to the cent.
    category: must already exist in the budgets table.
    """
    try:
        txn_date = validate_iso_date(date, "date")
        amount_cents = dollars_to_cents(amount)
    except ValueError as e:
        raise ToolError(str(e)) from e

    if not source or not source.strip():
        raise ToolError("source is required and cannot be empty")
    source = source.strip()

    conn = get_connection()
    try:
        valid_categories = {row[0] for row in conn.execute("SELECT category FROM budgets")}
        if category not in valid_categories:
            raise ToolError(
                f"Unknown category {category!r}. Valid categories: {', '.join(sorted(valid_categories))}"
            )

        cur = conn.execute(
            "INSERT INTO transactions (date, amount, category, source, note) VALUES (?, ?, ?, ?, ?)",
            (date, amount_cents, category, source, note),
        )
        conn.commit()
        new_id = cur.lastrowid

        month_start, month_end = month_bounds(txn_date)
        total_cents = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions "
            "WHERE category = ? AND date >= ? AND date < ?",
            (category, month_start.isoformat(), month_end.isoformat()),
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "transaction": {
            "id": new_id,
            "date": date,
            "amount_dollars": cents_to_dollars(amount_cents),
            "category": category,
            "source": source,
            "note": note,
        },
        "category_month": txn_date.strftime("%Y-%m"),
        "category_running_total_dollars": cents_to_dollars(total_cents),
    }


@mcp.tool()
def get_spending_summary(
    period: str,
    group_by: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Summarize expense transactions (amount < 0) over a period, grouped by category or source.

    period: 'this_month', 'last_month', or 'custom' (requires start_date and end_date).
    group_by: 'category' or 'source'.
    start_date/end_date: ISO 8601 'YYYY-MM-DD', inclusive, only used when period='custom'.
    """
    if group_by not in VALID_GROUP_BY:
        raise ToolError(f"group_by must be one of {sorted(VALID_GROUP_BY)}, got: {group_by!r}")

    try:
        range_start, range_end_exclusive = resolve_period(period, start_date, end_date)
    except ValueError as e:
        raise ToolError(str(e)) from e

    conn = get_connection()
    try:
        rows = conn.execute(
            f"SELECT {group_by}, SUM(amount), COUNT(*) FROM transactions "
            f"WHERE amount < 0 AND date >= ? AND date < ? "
            f"GROUP BY {group_by} ORDER BY SUM(amount) ASC",
            (range_start.isoformat(), range_end_exclusive.isoformat()),
        ).fetchall()
    finally:
        conn.close()

    total_spend_cents = sum(-amount_sum for _, amount_sum, _ in rows)
    groups = []
    for label, amount_sum, count in rows:
        magnitude_cents = -amount_sum
        percent = (magnitude_cents / total_spend_cents * 100) if total_spend_cents else 0.0
        groups.append(
            {
                group_by: label,
                "total_dollars": cents_to_dollars(magnitude_cents),
                "transaction_count": count,
                "percent_of_total": round(percent, 2),
            }
        )

    return {
        "period": {
            "start": range_start.isoformat(),
            "end": (range_end_exclusive - timedelta(days=1)).isoformat(),
        },
        "group_by": group_by,
        "total_spend_dollars": cents_to_dollars(total_spend_cents),
        "groups": groups,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
