from decimal import Decimal

from app.analysis.calculation import (
    calculate_closed_won_revenue,
    calculate_lead_conversion_rate,
    calculate_yoy_growth,
    safe_sum,
)
from app.analysis.verification import verify_reconciliation


def test_safe_sum():
    assert safe_sum([10, "20.50", None]) == Decimal("30.50")


def test_closed_won_revenue():
    opportunities = [
        {"Amount": 100, "StageName": "Closed Won"},
        {"Amount": 50, "StageName": "Negotiation"},
        {"Amount": 200, "StageName": "Closed Won"},
    ]
    assert calculate_closed_won_revenue(opportunities) == Decimal(300)


def test_lead_conversion_rate():
    leads = [
        {"IsConverted": True},
        {"IsConverted": False},
        {"Status": "Closed - Converted"},
        {"Status": "New"},
    ]
    assert calculate_lead_conversion_rate(leads) == 50.0


def test_empty_leads():
    assert calculate_lead_conversion_rate([]) == 0.0


def test_yoy_growth():
    assert calculate_yoy_growth(120, 100) == 20.0


def test_yoy_zero_denominator():
    assert calculate_yoy_growth(120, 0) is None


def test_reconciliation_passes():
    result = verify_reconciliation(
        [Decimal(100), Decimal(200)],
        Decimal(300),
    )
    assert result["status"] == "verified"


def test_reconciliation_fails():
    result = verify_reconciliation(
        [Decimal(100), Decimal(200)],
        Decimal(310),
    )
    assert result["status"] == "failed"
