from polyfactory.factories import DataclassFactory

from src.domain.entities.tenant import Tenant
from src.domain.value_objects.subdomain import Subdomain


class TenantFactory(DataclassFactory[Tenant]):
    __model__ = Tenant

    @classmethod
    def subdomain(cls) -> Subdomain:
        return Subdomain(f"tenant{cls.__faker__.random_int(min=1, max=999_999)}")
