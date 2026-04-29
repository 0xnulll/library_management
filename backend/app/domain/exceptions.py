class DomainError(Exception):
    """Base class for domain-level violations."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    """Raised when a state transition is invalid (e.g. book already on loan)."""


class AuthenticationError(DomainError):
    pass


class ValidationError(DomainError):
    pass
