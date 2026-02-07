"""Value Objects for the domain layer.

These are immutable objects that represent domain concepts
and can be used across different layers without creating dependencies.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class BookCreateData:
    """Value object for book creation data."""

    title: str
    authors: list[int]

    def __post_init__(self):
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        if not self.authors:
            raise ValueError("At least one author is required")
        if any(author_id <= 0 for author_id in self.authors):
            raise ValueError("All author IDs must be positive integers")


@dataclass(frozen=True)
class BookUpdateData:
    """Value object for book update data."""

    title: str | None = None
    authors: list[int] | None = None

    def __post_init__(self):
        if self.title is not None and (not self.title or not self.title.strip()):
            raise ValueError("Title cannot be empty when provided")
        if self.authors is not None and not self.authors:
            raise ValueError("Authors list cannot be empty when provided")
        if self.authors is not None and any(
            author_id <= 0 for author_id in self.authors
        ):
            raise ValueError("All author IDs must be positive integers")


@dataclass(frozen=True)
class AuthorCreateData:
    """Value object for author creation data."""

    first_name: str
    last_name: str
    birth_date: date | None = None
    death_date: date | None = None
    nationality: str | None = None
    bio: str | None = None
    photo_url: str | None = None

    def __post_init__(self):
        if not self.first_name or not self.first_name.strip():
            raise ValueError("First name cannot be empty")
        if not self.last_name or not self.last_name.strip():
            raise ValueError("Last name cannot be empty")
        if self.birth_date and self.death_date and self.birth_date > self.death_date:
            raise ValueError("Death date cannot be before birth date")


@dataclass(frozen=True)
class AuthorUpdateData:
    """Value object for author update data."""

    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    death_date: date | None = None
    nationality: str | None = None
    bio: str | None = None
    photo_url: str | None = None

    def __post_init__(self):
        if self.first_name is not None and (
            not self.first_name or not self.first_name.strip()
        ):
            raise ValueError("First name cannot be empty when provided")
        if self.last_name is not None and (
            not self.last_name or not self.last_name.strip()
        ):
            raise ValueError("Last name cannot be empty when provided")
        if self.birth_date and self.death_date and self.birth_date > self.death_date:
            raise ValueError("Death date cannot be before birth date")


@dataclass(frozen=True)
class PaginationParams:
    """Value object for pagination parameters."""

    page: int
    size: int

    def __post_init__(self):
        if self.page < 1:
            raise ValueError("Page number must be >= 1")
        if self.size < 1 or self.size > 100:
            raise ValueError("Page size must be between 1 and 100")

    @property
    def skip(self) -> int:
        """Calculate skip/offset value for database queries."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Get the limit value for database queries."""
        return self.size


@dataclass(frozen=True)
class PaginationMeta:
    """Value object for pagination metadata."""

    total: int
    page: int
    size: int
    count: int

    @property
    def last_page(self) -> int:
        """Calculate the last page number."""
        return (self.total + self.size - 1) // self.size if self.total > 0 else 1

    @property
    def next_page(self) -> int | None:
        """Get the next page number if available."""
        return self.page + 1 if self.page < self.last_page else None

    @property
    def previous_page(self) -> int | None:
        """Get the previous page number if available."""
        return self.page - 1 if self.page > 1 else None


@dataclass(frozen=True)
class PaginatedResult(Generic[T]):
    """Generic value object for paginated results."""

    data: list[T]
    meta: PaginationMeta

    def to_primitive(self, item_converter: Callable[[Any], Any] | None = None) -> dict:
        """Convert PaginatedResult to a JSON-serializable primitive dict.

        Args:
            item_converter: optional callable to convert each item to a primitive
                (e.g. entity -> dict). If None, items are used as-is and must
                already be JSON-serializable.

        Returns:
            dict with keys 'data' (list) and 'meta' (dict)
        """
        if item_converter:
            data = [item_converter(i) for i in self.data]
        else:
            data = list(self.data)

        return {
            "data": data,
            "meta": {
                "total": self.meta.total,
                "page": self.meta.page,
                "size": self.meta.size,
                "count": self.meta.count,
            },
        }

    @classmethod
    def from_primitive(
        cls, primitive: dict, item_converter: Callable[[Any], T] | None = None
    ) -> "PaginatedResult[T]":
        """Recreate a PaginatedResult from a primitive dict (the inverse of to_primitive).

        Args:
            primitive: dict with keys 'data' and 'meta'
            item_converter: optional callable to convert each primitive item to
                a domain item (e.g. dict -> entity). If None, items are used as-is.

        Returns:
            PaginatedResult with converted items and PaginationMeta
        """
        items = primitive.get("data", [])
        if item_converter:
            items = [item_converter(i) for i in items]

        meta = primitive.get("meta", {})
        pagination_meta = PaginationMeta(
            total=meta.get("total", 0),
            page=meta.get("page", 1),
            size=meta.get("size", len(items) if items is not None else 0),
            count=meta.get("count", len(items) if items is not None else 0),
        )

        return cls(data=items, meta=pagination_meta)


@dataclass(frozen=True)
class StoreCreateData:
    """Value object for store creation data."""

    name: str
    location: str | None = None

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")


@dataclass(frozen=True)
class StoreUpdateData:
    """Value object for store update data."""

    name: str | None = None
    location: str | None = None
