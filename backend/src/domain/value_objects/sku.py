import re
from dataclasses import dataclass

_SKU_RE = re.compile(r"^[A-Z0-9](?:[A-Z0-9-]{0,48}[A-Z0-9])?$")


@dataclass(frozen=True, slots=True)
class SKU:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _SKU_RE.match(normalized):
            raise ValueError(f"Invalid SKU: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
