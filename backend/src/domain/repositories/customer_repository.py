from typing import Protocol
from uuid import UUID

from src.domain.entities.customer import Customer


class CustomerRepository(Protocol):
    async def get_by_id(self, tenant_id: UUID, customer_id: UUID) -> Customer | None: ...

    async def get_by_email(self, tenant_id: UUID, email: str) -> Customer | None: ...

    async def add(self, customer: Customer) -> Customer: ...

    async def update(self, customer: Customer) -> Customer: ...
