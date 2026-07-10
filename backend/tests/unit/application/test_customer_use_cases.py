from uuid import uuid4

import pytest

from src.application.use_cases.customers.login_customer import (
    LoginCustomerInput,
    LoginCustomerUseCase,
)
from src.application.use_cases.customers.register_customer import (
    RegisterCustomerInput,
    RegisterCustomerUseCase,
)
from src.domain.exceptions import AuthenticationError, EntityAlreadyExistsError
from tests.unit.application.fakes import FakeCustomerRepository


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

    tokens = await LoginCustomerUseCase(customers).execute(
        LoginCustomerInput(tenant_id=tenant_id, email="jane@example.com", password="hunter22!!")
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

    with pytest.raises(AuthenticationError):
        await LoginCustomerUseCase(customers).execute(
            LoginCustomerInput(tenant_id=tenant_id, email="jane@example.com", password="wrong")
        )
