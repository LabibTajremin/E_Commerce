from dataclasses import dataclass

from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.security import hash_password
from src.domain.entities.admin_user import AdminRole, AdminUser
from src.domain.entities.tenant import Tenant
from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.value_objects.email import Email
from src.domain.value_objects.subdomain import Subdomain


@dataclass(frozen=True, slots=True)
class RegisterTenantOwnerInput:
    tenant_name: str
    subdomain: str
    owner_email: str
    owner_password: str


@dataclass(frozen=True, slots=True)
class RegisterTenantOwnerOutput:
    tenant: Tenant
    owner: AdminUser


class RegisterTenantOwnerUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, data: RegisterTenantOwnerInput) -> RegisterTenantOwnerOutput:
        subdomain = Subdomain(data.subdomain)
        email = Email(data.owner_email)

        async with self._uow as uow:
            if await uow.tenants.get_by_subdomain(str(subdomain)) is not None:
                raise EntityAlreadyExistsError("Tenant", str(subdomain))

            tenant = await uow.tenants.add(Tenant(name=data.tenant_name, subdomain=subdomain))
            await uow.set_tenant_context(tenant.id)
            owner = await uow.admin_users.add(
                AdminUser(
                    tenant_id=tenant.id,
                    email=email,
                    hashed_password=hash_password(data.owner_password),
                    role=AdminRole.OWNER,
                )
            )
            await uow.commit()

        return RegisterTenantOwnerOutput(tenant=tenant, owner=owner)
