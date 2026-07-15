from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.customer import Customer
from src.domain.value_objects.address import Address
from src.domain.value_objects.email import Email
from src.infrastructure.db.models.customer import CustomerModel


class SqlAlchemyCustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: CustomerModel) -> Customer:
        return Customer(
            id=model.id,
            tenant_id=model.tenant_id,
            email=Email(model.email),
            hashed_password=model.hashed_password,
            name=model.name,
            addresses=[Address(**a) for a in model.addresses],
            created_at=model.created_at,
        )

    async def get_by_id(self, tenant_id: UUID, customer_id: UUID) -> Customer | None:
        result = await self._session.execute(
            select(CustomerModel).where(
                CustomerModel.id == customer_id, CustomerModel.tenant_id == tenant_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, tenant_id: UUID, email: str) -> Customer | None:
        result = await self._session.execute(
            select(CustomerModel).where(
                CustomerModel.tenant_id == tenant_id, CustomerModel.email == email.strip().lower()
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def add(self, customer: Customer) -> Customer:
        model = CustomerModel(
            id=customer.id,
            tenant_id=customer.tenant_id,
            email=str(customer.email),
            hashed_password=customer.hashed_password,
            name=customer.name,
            addresses=[asdict(a) for a in customer.addresses],
            created_at=customer.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, customer: Customer) -> Customer:
        result = await self._session.execute(
            select(CustomerModel).where(
                CustomerModel.id == customer.id, CustomerModel.tenant_id == customer.tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Customer not found: {customer.id}")
        model.name = customer.name
        model.addresses = [asdict(a) for a in customer.addresses]
        await self._session.flush()
        return self._to_entity(model)
