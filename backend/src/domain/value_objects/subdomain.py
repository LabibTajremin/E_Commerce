import re
from dataclasses import dataclass

_SUBDOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_RESERVED = {"www", "api", "admin", "app", "platform", "mail", "ftp"}


@dataclass(frozen=True, slots=True)
class Subdomain:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 63 or not _SUBDOMAIN_RE.match(self.value):
            raise ValueError(f"Invalid subdomain: {self.value!r}")
        if self.value in _RESERVED:
            raise ValueError(f"Subdomain is reserved: {self.value!r}")

    def __str__(self) -> str:
        return self.value
