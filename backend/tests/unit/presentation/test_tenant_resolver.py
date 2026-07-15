import pytest

from src.presentation.middleware.tenant_resolver import extract_subdomain


@pytest.mark.parametrize(
    ("host", "base_domain", "expected"),
    [
        ("acme.localhost:3000", "localhost", "acme"),
        ("acme.yourplatform.com", "yourplatform.com", "acme"),
        ("localhost:3000", "localhost", None),
        ("yourplatform.com", "yourplatform.com", None),
        ("evilyourplatform.com", "yourplatform.com", None),
        ("acme.sub.yourplatform.com", "yourplatform.com", "acme.sub"),
    ],
)
def test_extract_subdomain(host: str, base_domain: str, expected: str | None) -> None:
    assert extract_subdomain(host, base_domain) == expected
