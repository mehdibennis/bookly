"""
Tests for API mappers.
Tests conversion between API DTOs and domain objects.
"""
from datetime import date, datetime

import pytest

from app.api.mappers import AuthorMapper, BookMapper, PaginationMapper, _parse_date
from app.domain.entities import AuthorEntity, BookEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta
from app.schemas.author_schema import Author, AuthorCreate, AuthorUpdate
from app.schemas.book_schema import Book, BookCreate, BookUpdate


class TestParseDateHelper:
    """Tests for _parse_date helper function."""

    def test_parse_date_none(self):
        """Parse None should return None."""
        assert _parse_date(None) is None

    def test_parse_date_already_date(self):
        """Parse date object should return same date."""
        test_date = date(2023, 5, 15)
        assert _parse_date(test_date) == test_date

    def test_parse_date_valid_iso_string(self):
        """Parse valid ISO string should return date."""
        result = _parse_date("2023-05-15")
        assert result == date(2023, 5, 15)

    def test_parse_date_invalid_string(self):
        """Parse invalid string should return None."""
        assert _parse_date("not-a-date") is None

    def test_parse_date_empty_string(self):
        """Parse empty string should return None."""
        assert _parse_date("") is None

    def test_parse_date_invalid_type(self):
        """Parse invalid type should return None."""
        assert _parse_date(12345) is None  # type: ignore


class TestBookMapper:
    """Tests for BookMapper."""

    def test_create_dto_to_domain(self):
        """Convert BookCreate DTO to BookCreateData."""
        dto = BookCreate(title="Test Book", authors=[1, 2, 3])
        domain = BookMapper.create_dto_to_domain(dto)
        
        assert domain.title == "Test Book"
        assert domain.authors == [1, 2, 3]

    def test_update_dto_to_domain_all_fields(self):
        """Convert BookUpdate DTO to BookUpdateData with all fields."""
        dto = BookUpdate(title="Updated Title", authors=[4, 5])
        domain = BookMapper.update_dto_to_domain(dto)
        
        assert domain.title == "Updated Title"
        assert domain.authors == [4, 5]

    def test_update_dto_to_domain_partial(self):
        """Convert BookUpdate DTO to BookUpdateData with partial fields."""
        dto = BookUpdate(title="Only Title")
        domain = BookMapper.update_dto_to_domain(dto)
        
        assert domain.title == "Only Title"
        assert domain.authors is None

    def test_entity_to_dto_minimal(self):
        """Convert BookEntity to Book DTO with minimal fields."""
        entity = BookEntity(id=1, title="Test Book")
        dto = BookMapper.entity_to_dto(entity)
        
        assert dto.id == 1
        assert dto.title == "Test Book"
        assert dto.authors == []
        assert dto.authors_details == []

    def test_entity_to_dto_with_authors(self):
        """Convert BookEntity to Book DTO with authors."""
        entity = BookEntity(id=1, title="Test Book", authors=[1, 2], authors_number=2)
        dto = BookMapper.entity_to_dto(entity)
        
        assert dto.authors == [1, 2]
        assert dto.authors_number == 2

    def test_entity_to_dto_with_authors_details(self):
        """Convert BookEntity to Book DTO with authors details."""
        details = [{"id": 1, "name": "Author 1"}]
        entity = BookEntity(id=1, title="Test Book", authors_details=details)
        dto = BookMapper.entity_to_dto(entity)
        
        assert dto.authors_details == details

    def test_entity_to_dto_none_id_defaults_to_zero(self):
        """Convert BookEntity with None id should default to 0."""
        entity = BookEntity(id=None, title="Test Book")
        dto = BookMapper.entity_to_dto(entity)
        
        assert dto.id == 0

    def test_entities_to_dtos(self):
        """Convert list of BookEntity to list of Book DTOs."""
        entities = [
            BookEntity(id=1, title="Book 1"),
            BookEntity(id=2, title="Book 2"),
            BookEntity(id=3, title="Book 3"),
        ]
        dtos = BookMapper.entities_to_dtos(entities)
        
        assert len(dtos) == 3
        assert dtos[0].id == 1
        assert dtos[1].id == 2
        assert dtos[2].id == 3

    def test_entities_to_dtos_empty_list(self):
        """Convert empty list should return empty list."""
        dtos = BookMapper.entities_to_dtos([])
        assert dtos == []


class TestAuthorMapper:
    """Tests for AuthorMapper."""

    def test_create_dto_to_domain_minimal(self):
        """Convert AuthorCreate DTO to AuthorCreateData with minimal fields."""
        dto = AuthorCreate(first_name="John", last_name="Doe")
        domain = AuthorMapper.create_dto_to_domain(dto)
        
        assert domain.first_name == "John"
        assert domain.last_name == "Doe"
        assert domain.birth_date is None
        assert domain.nationality is None

    def test_create_dto_to_domain_all_fields(self):
        """Convert AuthorCreate DTO to AuthorCreateData with all fields."""
        dto = AuthorCreate(
            first_name="Jane",
            last_name="Smith",
            birth_date=date(1950, 1, 1),
            death_date=date(2020, 1, 1),
            nationality="USA",
            bio="Test bio",
            photo_url="http://example.com/photo.jpg",
        )
        domain = AuthorMapper.create_dto_to_domain(dto)
        
        assert domain.first_name == "Jane"
        assert domain.last_name == "Smith"
        assert domain.birth_date == date(1950, 1, 1)
        assert domain.death_date == date(2020, 1, 1)
        assert domain.nationality == "USA"
        assert domain.bio == "Test bio"
        assert domain.photo_url == "http://example.com/photo.jpg"

    def test_create_dto_to_domain_with_string_dates(self):
        """Convert AuthorCreate DTO with string dates."""
        dto = AuthorCreate(
            first_name="John",
            last_name="Doe",
            birth_date="1980-05-15",  # type: ignore
            death_date="2050-12-31",  # type: ignore
        )
        domain = AuthorMapper.create_dto_to_domain(dto)
        
        assert domain.birth_date == date(1980, 5, 15)
        assert domain.death_date == date(2050, 12, 31)

    def test_update_dto_to_domain_partial(self):
        """Convert AuthorUpdate DTO to AuthorUpdateData with partial fields."""
        dto = AuthorUpdate(first_name="Updated")
        domain = AuthorMapper.update_dto_to_domain(dto)
        
        assert domain.first_name == "Updated"
        assert domain.last_name is None

    def test_update_dto_to_domain_all_fields(self):
        """Convert AuthorUpdate DTO to AuthorUpdateData with all fields."""
        dto = AuthorUpdate(
            first_name="Updated",
            last_name="Author",
            birth_date=date(1960, 3, 10),
            nationality="UK",
            bio="Updated bio",
        )
        domain = AuthorMapper.update_dto_to_domain(dto)
        
        assert domain.first_name == "Updated"
        assert domain.last_name == "Author"
        assert domain.birth_date == date(1960, 3, 10)
        assert domain.nationality == "UK"

    def test_entity_to_dto_minimal(self):
        """Convert AuthorEntity to Author DTO with minimal fields."""
        entity = AuthorEntity(id=1, first_name="John", last_name="Doe")
        dto = AuthorMapper.entity_to_dto(entity)
        
        assert dto.id == 1
        assert dto.first_name == "John"
        assert dto.last_name == "Doe"
        assert dto.birth_date is None

    def test_entity_to_dto_all_fields(self):
        """Convert AuthorEntity to Author DTO with all fields."""
        birth = date(1950, 1, 1)
        death = date(2020, 1, 1)
        created = datetime(2023, 1, 1, 12, 0, 0)
        updated = datetime(2023, 1, 2, 12, 0, 0)
        
        entity = AuthorEntity(
            id=1,
            first_name="Jane",
            last_name="Smith",
            birth_date=birth,
            death_date=death,
            nationality="USA",
            bio="Test bio",
            photo_url="http://example.com/photo.jpg",
            created_at=created,
            updated_at=updated,
        )
        dto = AuthorMapper.entity_to_dto(entity)
        
        assert dto.id == 1
        assert dto.birth_date == birth
        assert dto.death_date == death
        assert dto.nationality == "USA"
        assert dto.bio == "Test bio"
        assert dto.photo_url == "http://example.com/photo.jpg"
        assert dto.created_at == created
        assert dto.updated_at == updated

    def test_entity_to_dto_none_id_defaults_to_zero(self):
        """Convert AuthorEntity with None id should default to 0."""
        entity = AuthorEntity(id=None, first_name="John", last_name="Doe")
        dto = AuthorMapper.entity_to_dto(entity)
        
        assert dto.id == 0

    def test_entities_to_dtos(self):
        """Convert list of AuthorEntity to list of Author DTOs."""
        entities = [
            AuthorEntity(id=1, first_name="John", last_name="Doe"),
            AuthorEntity(id=2, first_name="Jane", last_name="Smith"),
            AuthorEntity(id=3, first_name="Bob", last_name="Johnson"),
        ]
        dtos = AuthorMapper.entities_to_dtos(entities)
        
        assert len(dtos) == 3
        assert dtos[0].id == 1
        assert dtos[1].first_name == "Jane"
        assert dtos[2].last_name == "Johnson"

    def test_entities_to_dtos_empty_list(self):
        """Convert empty list should return empty list."""
        dtos = AuthorMapper.entities_to_dtos([])
        assert dtos == []


class TestPaginationMapper:
    """Tests for PaginationMapper."""

    def test_params_from_query_defaults(self):
        """Create PaginationParams with default values."""
        params = PaginationMapper.params_from_query()
        
        assert params.page == 1
        assert params.size == 10

    def test_params_from_query_custom_values(self):
        """Create PaginationParams with custom values."""
        params = PaginationMapper.params_from_query(page=3, size=25)
        
        assert params.page == 3
        assert params.size == 25

    def test_result_to_response_books(self):
        """Convert PaginatedResult to PaginatedResponse for books."""
        entities = [
            BookEntity(id=1, title="Book 1"),
            BookEntity(id=2, title="Book 2"),
        ]
        meta = PaginationMeta(total=10, page=1, size=10, count=2)
        domain_result = PaginatedResult(data=entities, meta=meta)
        
        response = PaginationMapper.result_to_response(
            domain_result,
            BookMapper.entities_to_dtos
        )
        
        assert len(response.data) == 2
        assert response.data[0].id == 1
        assert response.data[0].title == "Book 1"
        assert response.meta.total == 10
        assert response.meta.page == 1
        assert response.meta.count == 2

    def test_result_to_response_authors(self):
        """Convert PaginatedResult to PaginatedResponse for authors."""
        entities = [
            AuthorEntity(id=1, first_name="John", last_name="Doe"),
            AuthorEntity(id=2, first_name="Jane", last_name="Smith"),
        ]
        meta = PaginationMeta(total=20, page=2, size=5, count=2)
        domain_result = PaginatedResult(data=entities, meta=meta)
        
        response = PaginationMapper.result_to_response(
            domain_result,
            AuthorMapper.entities_to_dtos
        )
        
        assert len(response.data) == 2
        assert response.data[0].first_name == "John"
        assert response.meta.total == 20
        assert response.meta.page == 2
        assert response.meta.last_page == 4

    def test_result_to_response_empty(self):
        """Convert empty PaginatedResult to PaginatedResponse."""
        meta = PaginationMeta(total=0, page=1, size=10, count=0)
        domain_result = PaginatedResult(data=[], meta=meta)
        
        response = PaginationMapper.result_to_response(
            domain_result,
            BookMapper.entities_to_dtos
        )
        
        assert response.data == []
        assert response.meta.total == 0
        assert response.meta.count == 0

    def test_result_to_response_pagination_meta_properties(self):
        """Verify pagination meta properties are correctly mapped."""
        entities = [BookEntity(id=1, title="Book 1")]
        meta = PaginationMeta(total=50, page=3, size=10, count=1)
        domain_result = PaginatedResult(data=entities, meta=meta)
        
        response = PaginationMapper.result_to_response(
            domain_result,
            BookMapper.entities_to_dtos
        )
        
        assert response.meta.last_page == 5
        assert response.meta.next_page == 4
        assert response.meta.previous_page == 2
