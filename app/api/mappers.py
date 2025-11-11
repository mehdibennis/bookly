"""Mappers to convert between domain and API DTOs.

These mappers serve as adapters between the domain layer and the API layer,
ensuring clean separation of concerns and preventing coupling between layers.
"""

from datetime import date
from typing import Callable, TypeVar

from app.domain.entities import AuthorEntity, BookEntity
from app.domain.value_objects import (
    AuthorCreateData,
    AuthorUpdateData,
    BookCreateData,
    BookUpdateData,
    PaginatedResult,
    PaginationParams,
)
from app.schemas.author_schema import Author, AuthorCreate, AuthorUpdate
from app.schemas.book_schema import Book, BookCreate, BookUpdate
from app.schemas.pagination import PaginatedResponse

T = TypeVar("T")
D = TypeVar("D")


def _parse_date(value: date | str | None) -> date | None:
    """Parse a date value from Pydantic DTO to domain date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


class BookMapper:
    """Mapper for book-related conversions."""

    @staticmethod
    def create_dto_to_domain(dto: BookCreate) -> BookCreateData:
        """Convert API BookCreate DTO to domain BookCreateData."""
        return BookCreateData(
            title=dto.title,
            authors=dto.authors,
        )

    @staticmethod
    def update_dto_to_domain(dto: BookUpdate) -> BookUpdateData:
        """Convert API BookUpdate DTO to domain BookUpdateData."""
        return BookUpdateData(
            title=dto.title,
            authors=dto.authors,
        )

    @staticmethod
    def entity_to_dto(entity: BookEntity) -> Book:
        """Convert domain BookEntity to API Book DTO."""
        return Book(
            id=entity.id if entity.id is not None else 0,
            title=entity.title,
            authors=entity.authors,
            authors_details=entity.authors_details,
            authors_number=entity.authors_number,
        )

    @staticmethod
    def entities_to_dtos(entities: list[BookEntity]) -> list[Book]:
        """Convert list of domain BookEntity to list of API Book DTOs."""
        return [BookMapper.entity_to_dto(entity) for entity in entities]


class AuthorMapper:
    """Mapper for author-related conversions."""

    @staticmethod
    def create_dto_to_domain(dto: AuthorCreate) -> AuthorCreateData:
        """Convert API AuthorCreate DTO to domain AuthorCreateData."""
        return AuthorCreateData(
            first_name=dto.first_name,
            last_name=dto.last_name,
            birth_date=_parse_date(dto.birth_date),
            death_date=_parse_date(dto.death_date),
            nationality=dto.nationality,
            bio=dto.bio,
            photo_url=dto.photo_url,
        )

    @staticmethod
    def update_dto_to_domain(dto: AuthorUpdate) -> AuthorUpdateData:
        """Convert API AuthorUpdate DTO to domain AuthorUpdateData."""
        return AuthorUpdateData(
            first_name=dto.first_name,
            last_name=dto.last_name,
            birth_date=_parse_date(dto.birth_date),
            death_date=_parse_date(dto.death_date),
            nationality=dto.nationality,
            bio=dto.bio,
            photo_url=dto.photo_url,
        )

    @staticmethod
    def entity_to_dto(entity: AuthorEntity) -> Author:
        """Convert domain AuthorEntity to API Author DTO."""
        return Author(
            id=entity.id if entity.id is not None else 0,
            first_name=entity.first_name,
            last_name=entity.last_name,
            birth_date=entity.birth_date,
            death_date=entity.death_date,
            nationality=entity.nationality,
            bio=entity.bio,
            photo_url=entity.photo_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def entities_to_dtos(entities: list[AuthorEntity]) -> list[Author]:
        """Convert list of domain AuthorEntity to list of API Author DTOs."""
        return [AuthorMapper.entity_to_dto(entity) for entity in entities]


class PaginationMapper:
    """Mapper for pagination-related conversions."""

    @staticmethod
    def params_from_query(page: int = 1, size: int = 10) -> PaginationParams:
        """Convert query parameters to domain PaginationParams."""
        return PaginationParams(page=page, size=size)

    @staticmethod
    def result_to_response(
        domain_result: PaginatedResult[T], mapper_func: Callable[[list[T]], list[D]]
    ) -> PaginatedResponse[D]:
        """Convert domain PaginatedResult to API PaginatedResponse.

        Args:
            domain_result: The domain paginated result
            mapper_func: Function to convert list of domain entities to list of DTOs

        Returns:
            API PaginatedResponse
        """
        from app.schemas.pagination import PaginationMeta as APIPaginationMeta

        data = mapper_func(domain_result.data)

        return PaginatedResponse(
            data=data,
            meta=APIPaginationMeta(
                total=domain_result.meta.total,
                page=domain_result.meta.page,
                size=domain_result.meta.size,
                count=domain_result.meta.count,
                last_page=domain_result.meta.last_page,
                next_page=domain_result.meta.next_page,
                previous_page=domain_result.meta.previous_page,
            ),
        )
