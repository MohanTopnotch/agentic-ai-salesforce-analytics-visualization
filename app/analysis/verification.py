from decimal import Decimal
from typing import Any


def verify_reconciliation(
    group_totals: list[Decimal],
    grand_total: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> dict[str, Any]:
    sum_of_groups = sum(group_totals, Decimal(0))
    delta = abs(sum_of_groups - grand_total)
    passed = delta <= tolerance

    return {
        "status": "verified" if passed else "failed",
        "expected": str(grand_total),
        "observed": str(sum_of_groups),
        "reconciliation_delta": float(delta),
        "checks_passed": 2 if passed else 1,
        "checks_failed": 0 if passed else 1,
    }