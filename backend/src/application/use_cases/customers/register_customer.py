from dataclasses import dataclass
from uuid import UUID

from src.core.security import hash_password
from src.domain.entities.customer import Customer
from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.value_objects.email import Email


@dataclass(frozen=True, slots=True)
class RegisterCustomerInput:
    tenant_id: UUID
    email: str
    password: str
    name: str


class RegisterCustomerUseCase:
    def __init__(self, customer_repository: CustomerRepository) -> None:
        self._customers = customer_repository

    async def execute(self, data: RegisterCustomerInput) -> Customer:
        email = Email(data.email)
        if await self._customers.get_by_email(data.tenant_id, str(email)) is not None:
            raise EntityAlreadyExistsError("Customer", str(email))

        customer = Customer(
            tenant_id=data.tenant_id,
            email=email,
            hashed_password=hash_password(data.password),
            name=data.name,
        )
        return await self._customers.add(customer)
