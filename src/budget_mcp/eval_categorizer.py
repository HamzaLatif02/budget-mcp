"""
Accuracy check for categorize_transaction against a small hand-labeled set of
realistic bank/card statement lines. This calls the live Anthropic API (needs
ANTHROPIC_API_KEY) and is not part of the deterministic pytest suite, since
LLM output isn't guaranteed reproducible.

Run with:
    PYTHONPATH=src .venv/bin/python -m budget_mcp.eval_categorizer
"""

from budget_mcp.categorizer import categorize

# (description, expected_category)
EVAL_SET = [
    ("WELLS FARGO ONLINE PMT - APARTMENT MGMT LLC", "rent"),
    ("TESCO STORES 3421 LONDON", "food"),
    ("UBER *TRIP HELP.UBER.COM", "transport"),
    ("TRANSFER TO SAVINGS ****4521", "savings"),
    ("AWS *AMAZON WEB SERVICES", "business_expense"),
    ("AMC THEATRES #1234 ONLINE", "entertainment"),
    ("VENMO PAYMENT TO J SMITH", "other"),
    ("SHELL OIL 57443021 FUEL PURCHASE", "transport"),
    ("TRADER JOE'S #112 AUSTIN TX", "food"),
    ("NETFLIX.COM", "entertainment"),
    ("ZILLOW RENTAL PAYMENT - LANDLORD DIRECT", "rent"),
    ("ACH TRANSFER TO ALLY BANK SAVINGS", "savings"),
    ("ADOBE CREATIVE CLOUD SUBSCRIPTION", "business_expense"),
    ("DOORDASH*MCDONALDS", "food"),
    ("ATM WITHDRAWAL - CHASE BANK #4471", "other"),
]


def main() -> None:
    correct = 0
    for description, expected in EVAL_SET:
        result = categorize(description)
        got = result["category"]
        ok = got == expected
        correct += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {description!r}")
        print(f"       expected={expected} got={got} confidence={result['confidence']:.2f}")
        print(f"       reasoning: {result['reasoning']}")

    total = len(EVAL_SET)
    print(f"\n{correct}/{total} correct ({correct / total:.0%})")


if __name__ == "__main__":
    main()
