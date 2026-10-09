from decimal import Decimal
from typing import Iterable

def safe_sum(values: Iterable[int | float | str | Decimal | None]) -> Decimal:
    total = Decimal("0")
    for value in values:
        if value is not None:
            total += Decimal(str(value))
    return total
