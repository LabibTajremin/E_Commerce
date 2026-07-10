from uuid import uuid4

import pytest

from src.domain.entities.admin_user import AdminUser, AdminUserStatus
from src.domain.value_objects.email import Email


def test_new_admin_user_defaults_to_active_owner() -> None:
    user = AdminUser(tenant_id=uuid4(), email=Email("Owner@Acme.com"), hashed_password="hash")
    assert user.is_active is True
    assert str(user.email) == "owner@acme.com"


def test_disable_marks_user_inactive() -> None:
    user = AdminUser(tenant_id=uuid4(), email=Email("owner@acme.com"), hashed_password="hash")
    user.disable()
    assert user.status == AdminUserStatus.DISABLED
    assert user.is_active is False


@pytest.mark.parametrize("invalid", ["", "not-an-email", "missing@domain", "@nodomain.com"])
def test_invalid_email_rejected(invalid: str) -> None:
    with pytest.raises(ValueError):
        Email(invalid)


def test_email_is_normalized_lowercase_and_trimmed() -> None:
    assert str(Email("  Foo@BAR.com  ")) == "foo@bar.com"
