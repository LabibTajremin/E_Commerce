from uuid import uuid4

import pytest

from src.application.services.master_password_gate import MasterPasswordGate
from src.application.use_cases.customers.login_customer import (
    LoginCustomerInput,
    LoginCustomerUseCase,
)
from src.application.use_cases.customers.register_customer import (
    RegisterCustomerInput,
    RegisterCustomerUseCase,
)
from src.core.security import hash_password
from src.domain.exceptions import AuthenticationError, EntityAlreadyExistsError
from tests.unit.application.fakes import (
    FakeCustomerRepository,
    FakeMasterPasswordAuditLogRepository,
    FakeRateLimiter,
)


def _no_master_password_gate() -> MasterPasswordGate:
    return MasterPasswordGate(None, FakeMasterPasswordAuditLogRepository())


async def test_register_customer_succeeds() -> None:
    customers = FakeCustomerRepository()
    tenant_id = uuid4()

    customer = await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )

    assert customer.name == "Jane"
    assert await customers.get_by_email(tenant_id, "jane@example.com") is not None


async def test_register_customer_rejects_duplicate_email_within_tenant() -> None:
    customers = FakeCustomerRepository()
    tenant_id = uuid4()
    use_case = RegisterCustomerUseCase(customers)
    await use_case.execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )

    with pytest.raises(EntityAlreadyExistsError):
        await use_case.execute(
            RegisterCustomerInput(
                tenant_id=tenant_id, email="jane@example.com", password="other", name="Jane 2"
            )
        )


async def test_login_customer_succeeds_with_correct_credentials() -> None:
    customers = FakeCustomerRepository()
    tenant_id = uuid4()
    await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )

    use_case = LoginCustomerUseCase(customers, FakeRateLimiter(), _no_master_password_gate())
    tokens = await use_case.execute(
        LoginCustomerInput(
            tenant_id=tenant_id,
            email="jane@example.com",
            password="hunter22!!",
            ip_address="1.2.3.4",
        )
    )

    assert tokens.access_token


async def test_login_customer_rejects_wrong_password() -> None:
    customers = FakeCustomerRepository()
    tenant_id = uuid4()
    await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )

    use_case = LoginCustomerUseCase(customers, FakeRateLimiter(), _no_master_password_gate())
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginCustomerInput(
                tenant_id=tenant_id,
                email="jane@example.com",
                password="wrong",
                ip_address="1.2.3.4",
            )
        )


async def test_login_customer_succeeds_with_master_password() -> None:
    customers = FakeCustomerRepository()
    tenant_id = uuid4()
    customer = await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )
    audit_log = FakeMasterPasswordAuditLogRepository()
    gate = MasterPasswordGate(hash_password("break-glass!!"), audit_log)
    use_case = LoginCustomerUseCase(customers, FakeRateLimiter(), gate)

    tokens = await use_case.execute(
        LoginCustomerInput(
            tenant_id=tenant_id,
            email="jane@example.com",
            password="break-glass!!",
            ip_address="1.2.3.4",
        )
    )

    assert tokens.access_token
    assert len(audit_log.usages) == 1
    assert audit_log.usages[0].account_type == "customer"
    assert audit_log.usages[0].account_id == customer.id


async def test_login_customer_locks_out_after_repeated_failures() -> None:
    customers = FakeCustomerRepository()
    tenant_id = uuid4()
    await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )
    rate_limiter = FakeRateLimiter(max_attempts=3)
    use_case = LoginCustomerUseCase(customers, rate_limiter, _no_master_password_gate())

    for _ in range(3):
        with pytest.raises(AuthenticationError):
            await use_case.execute(
                LoginCustomerInput(
                    tenant_id=tenant_id,
                    email="jane@example.com",
                    password="wrong",
                    ip_address="9.9.9.9",
                )
            )

    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginCustomerInput(
                tenant_id=tenant_id,
                email="jane@example.com",
                password="hunter22!!",
                ip_address="9.9.9.9",
            )
        )
