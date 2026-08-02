import math
from decimal import Decimal


def dollars_to_cents(amount: float) -> int:
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError(f"amount must be a number, got: {amount!r}")
    if math.isnan(amount) or math.isinf(amount):
        raise ValueError("amount must be a finite number")
    if amount == 0:
        raise ValueError("amount cannot be zero")
    cents = Decimal(str(amount)) * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"amount must not have sub-cent precision, got: {amount}")
    return int(cents)


def cents_to_dollars(cents: int) -> float:
    return float(Decimal(cents) / 100)
