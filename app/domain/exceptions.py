"""Domain-level exceptions without HTTP/framework dependencies.

Services and repositories raise these. The API layer maps them to HTTP responses.
"""


class DomainException(Exception):
    """Base class for domain-related errors."""


class NotFoundException(DomainException):
    """Raised when a requested domain entity cannot be found."""


class ConflictException(DomainException):
    """Raised when a domain invariant would be violated (duplicate, etc.)."""
