"""Test helpers for creating service instances with proper dependencies."""

from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.value_objects import BookCreateData, BookUpdateData, AuthorCreateData, AuthorUpdateData
from app.repositories.book_repository import BookRepository
from app.schemas.book_schema import BookCreate, BookUpdate
from app.schemas.author_schema import AuthorCreate, AuthorUpdate
from app.services.book_service import BookService
from tests.mocks.cache_service import MockCacheService


def create_book_service_with_deps(session):
    """Create a BookService with all required dependencies for testing."""
    repo = BookRepository(session)
    uow = SqlAlchemyUnitOfWork(session)
    cache = MockCacheService()
    return repo, BookService(repo, uow, cache)


async def create_book_service_async(session):
    """Async version of create_book_service_with_deps."""
    return create_book_service_with_deps(session)


def api_dto_to_domain_create(book_dto: BookCreate) -> BookCreateData:
    """Convert API DTO to domain value object for creation."""
    return BookCreateData(
        title=book_dto.title,
        authors=book_dto.authors
    )


def api_dto_to_domain_update(book_dto: BookUpdate) -> BookUpdateData:
    """Convert API DTO to domain value object for update."""
    return BookUpdateData(
        title=book_dto.title,
        authors=book_dto.authors
    )


def author_api_dto_to_domain_create(author_dto: AuthorCreate) -> AuthorCreateData:
    """Convert API DTO to domain value object for author creation."""
    from datetime import date, datetime
    
    # Convert string dates to date objects if needed
    birth_date = author_dto.birth_date
    if isinstance(birth_date, str):
        birth_date = datetime.fromisoformat(birth_date).date()
    
    death_date = author_dto.death_date
    if isinstance(death_date, str):
        death_date = datetime.fromisoformat(death_date).date()
    
    return AuthorCreateData(
        first_name=author_dto.first_name,
        last_name=author_dto.last_name,
        birth_date=birth_date,
        death_date=death_date,
        nationality=author_dto.nationality,
        bio=author_dto.bio,
        photo_url=author_dto.photo_url
    )