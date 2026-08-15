"""Domain error hierarchy (framework-independent)."""


class DomainError(Exception):
    """Base class for every error raised by the domain layer."""


class ValidationError(DomainError):
    """Raised when a value violates a domain invariant."""
