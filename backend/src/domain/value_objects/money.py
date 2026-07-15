from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        try:
            amount = Decimal(self.amount)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid amount: {self.amount!r}") from exc
        if amount < 0:
            raise ValueError(f"Amount cannot be negative: {amount}")
        object.__setattr__(self, "amount", amount.quantize(Decimal("0.01")))

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
