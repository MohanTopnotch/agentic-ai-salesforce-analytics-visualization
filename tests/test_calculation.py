from decimal import Decimal
from app.analysis.calculation import safe_sum
from app.analysis.verification import verify_total

def test_safe_sum_uses_decimal():
    assert safe_sum(["0.1", "0.2", None]) == Decimal("0.3")

def test_verification_passes_for_matching_totals():
    assert verify_total(Decimal("10"), Decimal("10"))["status"] == "passed"
