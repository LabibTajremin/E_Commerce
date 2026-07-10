class DomainError(Exception):
    """Base class for all domain-layer errors."""


class EntityNotFoundError(DomainError):
    def __init__(self, entity_name: str, identifier: object) -> None:
        self.entity_name = entity_name
        self.identifier = identifier
        super().__init__(f"{entity_name} not found: {identifier}")


class EntityAlreadyExistsError(DomainError):
    def __init__(self, entity_name: str, identifier: object) -> None:
        self.entity_name = entity_name
        self.identifier = identifier
        super().__init__(f"{entity_name} already exists: {identifier}")


class ValidationError(DomainError):
    pass


class AuthenticationError(DomainError):
    """Caller isn't (or is no longer) authenticated: bad credentials, missing,
    expired, or revoked token."""


class PermissionDeniedError(DomainError):
    """Caller is authenticated but not allowed to perform this action."""


class PlanLimitExceededError(DomainError):
    pass


class OutOfStockError(DomainError):
    def __init__(self, product_id: object, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Product {product_id} out of stock: requested {requested}, available {available}"
        )
