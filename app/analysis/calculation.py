from collections.abc import Iterable
from decimal import Decimal
from typing import Any


def safe_sum(
    values: Iterable[int | float | str | Decimal | None],
) -> Decimal:
    total = Decimal(0)

    for value in values:
        if value is None:
            continue
        try:
            total += Decimal(str(value))
        except (ValueError, TypeError, ArithmeticError):
            continue

    return total


def calculate_closed_won_revenue(
    opportunities: list[dict[str, Any]],
) -> Decimal:
    return safe_sum(
        opportunity.get("Amount")
        for opportunity in opportunities
        if opportunity.get("StageName") == "Closed Won"
    )


def calculate_lead_conversion_rate(
    leads: list[dict[str, Any]],
) -> float:
    if not leads:
        return 0.0

    converted = sum(
        1
        for lead in leads
        if lead.get("IsConverted") is True
        or lead.get("Status") == "Closed - Converted"
    )

    return round(converted / len(leads) * 100, 2)


def calculate_yoy_growth(
    current_val: float,
    prior_val: float,
) -> float | None:
    if prior_val == 0:
        return None

    return round((current_val - prior_val) / prior_val * 100, 2)