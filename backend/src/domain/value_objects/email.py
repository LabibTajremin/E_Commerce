import re
from dataclasses import dataclass

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValueError(f"Invalid email: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
