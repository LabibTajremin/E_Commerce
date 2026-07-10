from dataclasses import dataclass
from uuid import UUID

from src.application.dto.auth import TokenPair
from src.core.security import create_token, verify_password
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.customer_repository import CustomerRepository


@dataclass(frozen=True, slots=True)
class LoginCustomerInput:
    tenant_id: UUID
    email: str
    password: str


class LoginCustomerUseCase:
    def __init__(self, customer_repository: CustomerRepository) -> None:
        self._customers = customer_repository

    async def execute(self, data: LoginCustomerInput) -> TokenPair:
        customer = await self._customers.get_by_email(data.tenant_id, data.email)
        if customer is None or not verify_password(data.password, customer.hashed_password):
            raise AuthenticationError("Invalid credentials")

        access_token, _ = create_token(
            subject=customer.id, tenant_id=customer.tenant_id, token_type="access", role="customer"
        )
        refresh_token, _ = create_token(
            subject=customer.id, tenant_id=customer.tenant_id, token_type="refresh", role="customer"
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
