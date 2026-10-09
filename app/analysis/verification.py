from decimal import Decimal

def verify_total(expected: Decimal, observed: Decimal) -> dict[str, object]:
    passed = expected == observed
    return {"status": "passed" if passed else "failed",
            "expected": str(expected), "observed": str(observed),
            "difference": str(observed - expected)}
