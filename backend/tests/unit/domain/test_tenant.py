import pytest

from src.domain.entities.tenant import Tenant, TenantStatus
from src.domain.value_objects.subdomain import Subdomain


def test_new_tenant_defaults_to_trial() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"))
    assert tenant.status == TenantStatus.TRIAL
    assert tenant.is_active is True


def test_suspend_marks_tenant_inactive() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"))
    tenant.suspend()
    assert tenant.status == TenantStatus.SUSPENDED
    assert tenant.is_active is False


def test_reactivate_restores_active_state() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"), status=TenantStatus.SUSPENDED)
    tenant.reactivate()
    assert tenant.status == TenantStatus.ACTIVE
    assert tenant.is_active is True


@pytest.mark.parametrize(
    "invalid_subdomain", ["", "Acme", "-acme", "acme-", "a" * 64, "www", "ac me"]
)
def test_invalid_subdomain_rejected(invalid_subdomain: str) -> None:
    with pytest.raises(ValueError):
        Subdomain(invalid_subdomain)


def test_valid_subdomain_accepted() -> None:
    assert str(Subdomain("acme-store")) == "acme-store"
