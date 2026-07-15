from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Address:
    line1: str
    city: str
    state: str
    postal_code: str
    country: str
    line2: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("line1", self.line1),
            ("city", self.city),
            ("state", self.state),
            ("postal_code", self.postal_code),
            ("country", self.country),
        ):
            if not value.strip():
                raise ValueError(f"Address.{field_name} cannot be empty")
