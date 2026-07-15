from uuid import uuid4

from src.application.services.master_password_gate import MasterPasswordGate
from src.core.security import hash_password
from tests.unit.application.fakes import FakeMasterPasswordAuditLogRepository


def test_matches_returns_false_when_disabled() -> None:
    gate = MasterPasswordGate(None, FakeMasterPasswordAuditLogRepository())

    assert gate.matches("anything") is False


def test_matches_returns_true_for_correct_password() -> None:
    gate = MasterPasswordGate(
        hash_password("s3cret-master!!"), FakeMasterPasswordAuditLogRepository()
    )

    assert gate.matches("s3cret-master!!") is True


def test_matches_returns_false_for_wrong_password() -> None:
    gate = MasterPasswordGate(
        hash_password("s3cret-master!!"), FakeMasterPasswordAuditLogRepository()
    )

    assert gate.matches("wrong") is False


async def test_record_usage_appends_to_audit_log() -> None:
    audit_log = FakeMasterPasswordAuditLogRepository()
    gate = MasterPasswordGate(hash_password("s3cret-master!!"), audit_log)
    account_id = uuid4()
    tenant_id = uuid4()

    await gate.record_usage(
        account_type="admin_user",
        account_id=account_id,
        account_email="owner@acme.com",
        tenant_id=tenant_id,
        ip_address="203.0.113.5",
    )

    assert len(audit_log.usages) == 1
    usage = audit_log.usages[0]
    assert usage.account_type == "admin_user"
    assert usage.account_id == account_id
    assert usage.account_email == "owner@acme.com"
    assert usage.tenant_id == tenant_id
    assert usage.ip_address == "203.0.113.5"
