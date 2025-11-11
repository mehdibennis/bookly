"""
Comprehensive tests for domain value objects.
Tests all validations, edge cases, and property calculations.
"""

from datetime import date

import pytest

from app.domain.value_objects import (
    AuthorCreateData,
    AuthorUpdateData,
    BookCreateData,
    BookUpdateData,
    PaginatedResult,
    PaginationMeta,
    PaginationParams,
)


class TestBookCreateData:
    """Tests for BookCreateData value object."""

    def test_valid_book_create_data(self):
        """Valid book creation should succeed."""
        book_data = BookCreateData(title="Valid Title", authors=[1, 2, 3])
        assert book_data.title == "Valid Title"
        assert book_data.authors == [1, 2, 3]

    def test_empty_title_raises_error(self):
        """Empty title should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            BookCreateData(title="", authors=[1])

    def test_whitespace_only_title_raises_error(self):
        """Whitespace-only title should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            BookCreateData(title="   ", authors=[1])

    def test_empty_authors_list_raises_error(self):
        """Empty authors list should raise ValueError."""
        with pytest.raises(ValueError, match="At least one author is required"):
            BookCreateData(title="Valid", authors=[])

    def test_zero_author_id_raises_error(self):
        """Author ID of 0 should raise ValueError."""
        with pytest.raises(
            ValueError, match="All author IDs must be positive integers"
        ):
            BookCreateData(title="Valid", authors=[0])

    def test_negative_author_id_raises_error(self):
        """Negative author ID should raise ValueError."""
        with pytest.raises(
            ValueError, match="All author IDs must be positive integers"
        ):
            BookCreateData(title="Valid", authors=[-1])

    def test_mixed_invalid_author_ids_raises_error(self):
        """Mixed valid and invalid author IDs should raise ValueError."""
        with pytest.raises(
            ValueError, match="All author IDs must be positive integers"
        ):
            BookCreateData(title="Valid", authors=[1, 2, -3])


class TestBookUpdateData:
    """Tests for BookUpdateData value object."""

    def test_valid_book_update_data_all_fields(self):
        """Valid update with all fields should succeed."""
        update_data = BookUpdateData(title="New Title", authors=[4, 5])
        assert update_data.title == "New Title"
        assert update_data.authors == [4, 5]

    def test_valid_book_update_data_partial(self):
        """Valid partial update should succeed."""
        update_data = BookUpdateData(title="Only Title")
        assert update_data.title == "Only Title"
        assert update_data.authors is None

    def test_empty_title_when_provided_raises_error(self):
        """Empty title when provided should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty when provided"):
            BookUpdateData(title="")

    def test_whitespace_title_when_provided_raises_error(self):
        """Whitespace-only title when provided should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty when provided"):
            BookUpdateData(title="   ")

    def test_empty_authors_when_provided_raises_error(self):
        """Empty authors list when provided should raise ValueError."""
        with pytest.raises(
            ValueError, match="Authors list cannot be empty when provided"
        ):
            BookUpdateData(authors=[])

    def test_invalid_author_id_when_provided_raises_error(self):
        """Invalid author ID when provided should raise ValueError."""
        with pytest.raises(
            ValueError, match="All author IDs must be positive integers"
        ):
            BookUpdateData(authors=[1, 0])


class TestAuthorCreateData:
    """Tests for AuthorCreateData value object."""

    def test_valid_author_create_data_minimal(self):
        """Valid author creation with minimal fields should succeed."""
        author_data = AuthorCreateData(first_name="John", last_name="Doe")
        assert author_data.first_name == "John"
        assert author_data.last_name == "Doe"
        assert author_data.birth_date is None
        assert author_data.death_date is None

    def test_valid_author_create_data_all_fields(self):
        """Valid author creation with all fields should succeed."""
        birth = date(1950, 1, 1)
        death = date(2020, 12, 31)
        author_data = AuthorCreateData(
            first_name="Jane",
            last_name="Smith",
            birth_date=birth,
            death_date=death,
            nationality="USA",
            bio="Test bio",
            photo_url="http://example.com/photo.jpg",
        )
        assert author_data.first_name == "Jane"
        assert author_data.birth_date == birth
        assert author_data.death_date == death

    def test_empty_first_name_raises_error(self):
        """Empty first name should raise ValueError."""
        with pytest.raises(ValueError, match="First name cannot be empty"):
            AuthorCreateData(first_name="", last_name="Doe")

    def test_whitespace_first_name_raises_error(self):
        """Whitespace-only first name should raise ValueError."""
        with pytest.raises(ValueError, match="First name cannot be empty"):
            AuthorCreateData(first_name="   ", last_name="Doe")

    def test_empty_last_name_raises_error(self):
        """Empty last name should raise ValueError."""
        with pytest.raises(ValueError, match="Last name cannot be empty"):
            AuthorCreateData(first_name="John", last_name="")

    def test_whitespace_last_name_raises_error(self):
        """Whitespace-only last name should raise ValueError."""
        with pytest.raises(ValueError, match="Last name cannot be empty"):
            AuthorCreateData(first_name="John", last_name="   ")

    def test_death_before_birth_raises_error(self):
        """Death date before birth date should raise ValueError."""
        with pytest.raises(ValueError, match="Death date cannot be before birth date"):
            AuthorCreateData(
                first_name="John",
                last_name="Doe",
                birth_date=date(2000, 1, 1),
                death_date=date(1990, 1, 1),
            )


class TestAuthorUpdateData:
    """Tests for AuthorUpdateData value object."""

    def test_valid_author_update_data_partial(self):
        """Valid partial update should succeed."""
        update_data = AuthorUpdateData(first_name="NewName")
        assert update_data.first_name == "NewName"
        assert update_data.last_name is None

    def test_valid_author_update_data_all_fields(self):
        """Valid update with all fields should succeed."""
        birth = date(1960, 5, 10)
        update_data = AuthorUpdateData(
            first_name="Updated",
            last_name="Author",
            birth_date=birth,
            nationality="UK",
        )
        assert update_data.first_name == "Updated"
        assert update_data.birth_date == birth

    def test_empty_first_name_when_provided_raises_error(self):
        """Empty first name when provided should raise ValueError."""
        with pytest.raises(
            ValueError, match="First name cannot be empty when provided"
        ):
            AuthorUpdateData(first_name="")

    def test_whitespace_first_name_when_provided_raises_error(self):
        """Whitespace-only first name when provided should raise ValueError."""
        with pytest.raises(
            ValueError, match="First name cannot be empty when provided"
        ):
            AuthorUpdateData(first_name="   ")

    def test_empty_last_name_when_provided_raises_error(self):
        """Empty last name when provided should raise ValueError."""
        with pytest.raises(ValueError, match="Last name cannot be empty when provided"):
            AuthorUpdateData(last_name="")

    def test_death_before_birth_when_both_provided_raises_error(self):
        """Death before birth when both provided should raise ValueError."""
        with pytest.raises(ValueError, match="Death date cannot be before birth date"):
            AuthorUpdateData(
                birth_date=date(2000, 1, 1),
                death_date=date(1990, 1, 1),
            )


class TestPaginationParams:
    """Tests for PaginationParams value object."""

    def test_valid_pagination_params(self):
        """Valid pagination parameters should succeed."""
        params = PaginationParams(page=2, size=10)
        assert params.page == 2
        assert params.size == 10

    def test_page_less_than_one_raises_error(self):
        """Page number < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            PaginationParams(page=0, size=10)

    def test_negative_page_raises_error(self):
        """Negative page number should raise ValueError."""
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            PaginationParams(page=-1, size=10)

    def test_size_less_than_one_raises_error(self):
        """Size < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            PaginationParams(page=1, size=0)

    def test_size_greater_than_hundred_raises_error(self):
        """Size > 100 should raise ValueError."""
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            PaginationParams(page=1, size=101)

    def test_skip_calculation_first_page(self):
        """Skip calculation for first page should be 0."""
        params = PaginationParams(page=1, size=10)
        assert params.skip == 0

    def test_skip_calculation_second_page(self):
        """Skip calculation for second page should be size."""
        params = PaginationParams(page=2, size=10)
        assert params.skip == 10

    def test_skip_calculation_arbitrary_page(self):
        """Skip calculation should work for any page."""
        params = PaginationParams(page=5, size=20)
        assert params.skip == 80

    def test_limit_property(self):
        """Limit property should return size."""
        params = PaginationParams(page=1, size=25)
        assert params.limit == 25


class TestPaginationMeta:
    """Tests for PaginationMeta value object."""

    def test_last_page_calculation_exact_division(self):
        """Last page with exact division should calculate correctly."""
        meta = PaginationMeta(total=100, page=1, size=10, count=10)
        assert meta.last_page == 10

    def test_last_page_calculation_with_remainder(self):
        """Last page with remainder should round up."""
        meta = PaginationMeta(total=95, page=1, size=10, count=10)
        assert meta.last_page == 10

    def test_last_page_calculation_empty_results(self):
        """Last page with no results should be 1."""
        meta = PaginationMeta(total=0, page=1, size=10, count=0)
        assert meta.last_page == 1

    def test_next_page_not_on_last_page(self):
        """Next page should be page + 1 when not on last page."""
        meta = PaginationMeta(total=100, page=3, size=10, count=10)
        assert meta.next_page == 4

    def test_next_page_on_last_page(self):
        """Next page should be None on last page."""
        meta = PaginationMeta(total=100, page=10, size=10, count=10)
        assert meta.next_page is None

    def test_previous_page_not_on_first_page(self):
        """Previous page should be page - 1 when not on first page."""
        meta = PaginationMeta(total=100, page=3, size=10, count=10)
        assert meta.previous_page == 2

    def test_previous_page_on_first_page(self):
        """Previous page should be None on first page."""
        meta = PaginationMeta(total=100, page=1, size=10, count=10)
        assert meta.previous_page is None


class TestPaginatedResult:
    """Tests for PaginatedResult value object."""

    def test_paginated_result_creation(self):
        """PaginatedResult should store data and meta correctly."""
        meta = PaginationMeta(total=50, page=2, size=10, count=10)
        data = [1, 2, 3, 4, 5]
        result = PaginatedResult(data=data, meta=meta)

        assert result.data == data
        assert result.meta == meta
        assert result.meta.page == 2
        assert result.meta.total == 50

    def test_paginated_result_with_empty_data(self):
        """PaginatedResult should handle empty data list."""
        meta = PaginationMeta(total=0, page=1, size=10, count=0)
        result = PaginatedResult(data=[], meta=meta)

        assert result.data == []
        assert result.meta.total == 0
