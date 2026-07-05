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


class PermissionDeniedError(DomainError):
    pass


class PlanLimitExceededError(DomainError):
    pass
