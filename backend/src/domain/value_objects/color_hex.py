import re
from dataclasses import dataclass

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


@dataclass(frozen=True, slots=True)
class ColorHex:
    value: str

    def __post_init__(self) -> None:
        if not _HEX_RE.match(self.value):
            raise ValueError(f"Invalid hex color: {self.value!r}")
        object.__setattr__(self, "value", self.value.lower())

    def __str__(self) -> str:
        return self.value
