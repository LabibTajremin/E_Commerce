import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class Slug:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not _SLUG_RE.match(self.value):
            raise ValueError(f"Invalid slug: {self.value!r}")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_text(cls, text: str) -> "Slug":
        normalized = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return cls(normalized or "item")
