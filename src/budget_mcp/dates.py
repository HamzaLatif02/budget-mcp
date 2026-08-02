from datetime import date, timedelta


def validate_iso_date(value: str, field_name: str = "date") -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format, got: {value!r}") from e


def month_bounds(d: date) -> tuple[date, date]:
    """Return (first day of d's month, first day of the following month)."""
    start = d.replace(day=1)
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return start, end


def resolve_period(period: str, start_date: str | None, end_date: str | None) -> tuple[date, date]:
    """Return (range start, exclusive range end) for a period keyword or custom range."""
    today = date.today()
    if period == "this_month":
        return month_bounds(today)
    if period == "last_month":
        last_month_day = today.replace(day=1) - timedelta(days=1)
        return month_bounds(last_month_day)
    if period == "custom":
        if not start_date or not end_date:
            raise ValueError("period='custom' requires both start_date and end_date")
        start = validate_iso_date(start_date, "start_date")
        end = validate_iso_date(end_date, "end_date")
        if end < start:
            raise ValueError(f"end_date ({end_date}) must not be before start_date ({start_date})")
        return start, end + timedelta(days=1)
    raise ValueError(f"period must be one of 'this_month', 'last_month', 'custom', got: {period!r}")
