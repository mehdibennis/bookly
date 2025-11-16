"""
Unit tests for AuthorService.
Tests business logic and validation rules.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.date_utils import parse_date
from app.domain.entities import AuthorEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.value_objects import AuthorUpdateData, PaginatedResult, PaginationMeta
from app.schemas.author_schema import AuthorCreate
from app.services.author_service import AuthorService


@pytest.fixture
def mock_repo():
    """Mock AuthorRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_uow():
    """Mock Unit of Work."""
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=None)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


@pytest.fixture
def author_service(mock_repo, mock_uow, monkeypatch):
    """Create AuthorService with mocked dependencies."""
    service = AuthorService(mock_repo, mock_uow)

    # Mock Redis cache to avoid connection issues in unit tests
    mock_cache = AsyncMock()
    mock_cache.connect = AsyncMock()
    mock_cache.close = AsyncMock()
    mock_cache.get_authors_page = AsyncMock(return_value=None)  # No cache hit
    mock_cache.set_authors_page = AsyncMock()

    monkeypatch.setattr(service, "cache", mock_cache)
    return service


# --- CREATE TESTS ---


@pytest.mark.asyncio
async def test_create_author_success(author_service, mock_repo):
    """Test successful author creation."""
    author_data = AuthorCreate(
        first_name="George", last_name="Orwell", nationality="British"
    )

    # Mock repository returns None (no duplicate)
    mock_repo.get_by_full_name.return_value = None
    mock_repo.create.return_value = AuthorEntity(
        id=1,
        first_name="George",
        last_name="Orwell",
        nationality="British",
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )

    result = await author_service.create_author(author_data)

    assert result.id == 1
    assert result.first_name == "George"
    assert result.last_name == "Orwell"
    mock_repo.get_by_full_name.assert_called_once_with("George", "Orwell")
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_author_empty_first_name(author_service):
    """Test creating author with empty first name raises ValueError."""
    author_data = AuthorCreate(first_name="   ", last_name="Test")

    with pytest.raises(ValueError, match="Author's first name cannot be empty."):
        await author_service.create_author(author_data)


@pytest.mark.asyncio
async def test_create_author_empty_last_name(author_service):
    """Test creating author with empty last name raises ValueError."""
    author_data = AuthorCreate(first_name="Test", last_name="   ")

    with pytest.raises(ValueError, match="Author's last name cannot be empty."):
        await author_service.create_author(author_data)


@pytest.mark.asyncio
async def test_create_author_duplicate(author_service, mock_repo):
    """Test creating duplicate author raises ConflictException."""
    author_data = AuthorCreate(first_name="Duplicate", last_name="Author")

    # Mock repository returns existing author
    mock_repo.get_by_full_name.return_value = AuthorEntity(
        id=1,
        first_name="Duplicate",
        last_name="Author",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )

    with pytest.raises(ConflictException, match="already exists"):
        await author_service.create_author(author_data)


# --- GET TESTS ---


@pytest.mark.asyncio
async def test_get_author_success(author_service, mock_repo):
    """Test getting author by ID."""
    mock_repo.get_by_id.return_value = AuthorEntity(
        id=1,
        first_name="Test",
        last_name="Author",
        nationality="French",
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )

    result = await author_service.get_author(1)

    assert result.id == 1
    assert result.first_name == "Test"
    mock_repo.get_by_id.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_author_invalid_id(author_service):
    """Test getting author with invalid ID raises ValueError."""
    with pytest.raises(ValueError, match="Author ID.*positive integer"):
        await author_service.get_author(0)

    with pytest.raises(ValueError, match="Author ID.*positive integer"):
        await author_service.get_author(-1)


@pytest.mark.asyncio
async def test_get_author_not_found(author_service, mock_repo):
    """Test getting non-existent author raises NotFoundException."""
    mock_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException, match="not found"):
        await author_service.get_author(999)


# --- LIST TESTS ---


@pytest.mark.asyncio
async def test_list_authors_by_page(author_service, mock_repo):
    """Test listing authors with pagination."""
    authors = [
        AuthorEntity(
            id=1,
            first_name="Author",
            last_name="One",
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        ),
        AuthorEntity(
            id=2,
            first_name="Author",
            last_name="Two",
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        ),
    ]

    mock_repo.get_paginated.return_value = PaginatedResult(
        data=authors,
        meta=PaginationMeta(
            total=10,
            page=1,
            size=2,
            count=len(authors),
        ),
    )

    result = await author_service.list_authors_by_page(page=1, size=2)

    assert len(result.data) == 2
    assert result.meta.total == 10
    assert result.meta.page == 1
    assert result.meta.size == 2
    # Verify repository was called with correct PaginationParams
    assert mock_repo.get_paginated.called


@pytest.mark.asyncio
async def test_list_authors_invalid_page(author_service):
    """Test listing with invalid page number raises ValueError."""
    with pytest.raises(ValueError, match="Page number must be >= 1."):
        await author_service.list_authors_by_page(page=0, size=10)


@pytest.mark.asyncio
async def test_list_authors_invalid_size(author_service):
    """Test listing with invalid size raises ValueError."""
    with pytest.raises(ValueError, match="Page size must be between 1 and 100."):
        await author_service.list_authors_by_page(page=1, size=0)


# --- PARTIAL UPDATE TESTS ---


@pytest.mark.asyncio
async def test_partial_update_author_success(author_service, mock_repo):
    """Test partial update updates only provided fields."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Original",
        last_name="Author",
        nationality="French",
        birth_date=None,
        death_date=None,
        bio="Old bio",
        photo_url=None,
    )

    mock_repo.get_by_id.return_value = existing_author
    mock_repo.partial_update.return_value = AuthorEntity(
        id=1,
        first_name="Original",
        last_name="Author",
        nationality="British",  # Updated
        birth_date=None,
        death_date=None,
        bio="Old bio",
        photo_url=None,
    )

    update_data = AuthorUpdateData(nationality="British")
    result = await author_service.partial_update_author(1, update_data)

    assert result.nationality == "British"
    mock_repo.partial_update.assert_called_once()
    # Verify only nationality was in update_data
    call_args = mock_repo.partial_update.call_args
    assert call_args[0][0] == 1  # author_id
    normalized_data = call_args[0][1]  # AuthorUpdateData
    assert normalized_data.nationality == "British"


@pytest.mark.asyncio
async def test_partial_update_author_invalid_id(author_service):
    """Test partial update with invalid ID raises ValueError."""
    with pytest.raises(ValueError, match="Author ID.*positive integer"):
        await author_service.partial_update_author(0, AuthorUpdateData())


@pytest.mark.asyncio
async def test_partial_update_author_not_found(author_service, mock_repo):
    """Test partial update of non-existent author raises NotFoundException."""
    mock_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException, match="not found"):
        await author_service.partial_update_author(
            999, AuthorUpdateData(nationality="Test")
        )


@pytest.mark.asyncio
async def test_partial_update_no_fields(author_service, mock_repo):
    """Test partial update with no fields returns existing author."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Test",
        last_name="Author",
        nationality="French",
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )
    mock_repo.get_by_id.return_value = existing_author
    mock_repo.partial_update.return_value = existing_author

    result = await author_service.partial_update_author(1, AuthorUpdateData())

    assert result == existing_author
    mock_repo.partial_update.assert_not_called()


@pytest.mark.asyncio
async def test_partial_update_empty_first_name(author_service, mock_repo):
    """Test partial update with empty first name raises ValueError."""
    # Value object validates at creation, so we test the validation directly
    with pytest.raises(ValueError, match="[Ff]irst name.*cannot be empty"):
        AuthorUpdateData(first_name="   ")


@pytest.mark.asyncio
async def test_partial_update_empty_last_name(author_service, mock_repo):
    """Test partial update with empty last name raises ValueError."""
    # Value object validates at creation, so we test the validation directly
    with pytest.raises(ValueError, match="Last name cannot be empty"):
        AuthorUpdateData(last_name="")
        await author_service.partial_update_author(1, AuthorUpdateData(last_name="   "))


@pytest.mark.asyncio
async def test_partial_update_name_conflict(author_service, mock_repo):
    """Test partial update with conflicting name raises ConflictException."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Original",
        last_name="Author",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )
    conflicting_author = AuthorEntity(
        id=2,
        first_name="Conflict",
        last_name="Author",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )

    mock_repo.get_by_id.return_value = existing_author
    mock_repo.get_by_full_name.return_value = conflicting_author

    with pytest.raises(ConflictException, match="already exists"):
        await author_service.partial_update_author(
            1, AuthorUpdateData(first_name="Conflict")
        )


@pytest.mark.asyncio
async def test_partial_update_normalization(author_service, mock_repo):
    """Test partial update normalizes field values."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Test",
        last_name="Author",
        nationality="french",
        birth_date=None,
        death_date=None,
        bio=" old bio ",
        photo_url=None,
    )

    mock_repo.get_by_id.return_value = existing_author
    mock_repo.get_by_full_name.return_value = None
    mock_repo.partial_update.return_value = existing_author

    update_data = AuthorUpdateData(
        first_name="  john  ", nationality="  british  ", bio="  new bio  "
    )

    await author_service.partial_update_author(1, update_data)

    # Service normalizes and creates new AuthorUpdateData to pass to repo
    call_args = mock_repo.partial_update.call_args
    normalized_data = call_args[0][1]  # Second positional arg is the AuthorUpdateData
    assert normalized_data.first_name == "John"  # Title case
    assert normalized_data.nationality == "British"  # Title case
    assert normalized_data.bio == "new bio"  # Stripped


# --- DELETE TESTS ---


@pytest.mark.asyncio
async def test_delete_author_success(author_service, mock_repo):
    """Test successful author deletion."""
    mock_repo.get_by_id.return_value = AuthorEntity(
        id=1,
        first_name="Delete",
        last_name="Me",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )
    mock_repo.delete.return_value = True

    result = await author_service.delete_author(1)

    assert result is True
    mock_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_author_invalid_id(author_service):
    """Test deleting author with invalid ID raises ValueError."""
    with pytest.raises(ValueError, match="Author ID.*positive integer"):
        await author_service.delete_author(-1)


@pytest.mark.asyncio
async def test_delete_author_not_found(author_service, mock_repo):
    """Test deleting non-existent author raises NotFoundException."""
    mock_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException, match="not found"):
        await author_service.delete_author(999)


# --- UPDATE (FULL) TESTS ---


@pytest.mark.asyncio
async def test_update_author_success(author_service, mock_repo):
    """Test full update of author."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Old",
        last_name="Name",
        nationality="French",
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )

    mock_repo.get_by_id.return_value = existing_author
    mock_repo.get_by_full_name.return_value = None
    mock_repo.partial_update.return_value = AuthorEntity(
        id=1,
        first_name="New",
        last_name="Name",
        nationality="British",
        birth_date=parse_date("1900-01-01"),
        death_date=None,
        bio="Bio",
        photo_url=None,
    )

    update_data = AuthorUpdateData(
        first_name="New",
        nationality="British",
        birth_date=parse_date("1900-01-01"),
        bio="Bio",
    )

    await author_service.partial_update_author(1, update_data)
    mock_repo.partial_update.assert_called_once()


@pytest.mark.asyncio
async def test_update_author_invalid_id(author_service):
    """Update with invalid ID should raise ValueError."""
    with pytest.raises(ValueError, match="Author ID.*positive integer"):
        await author_service.partial_update_author(
            0, AuthorUpdateData(first_name="Test")
        )


@pytest.mark.asyncio
async def test_update_author_not_found(author_service, mock_repo):
    """Update non-existent author should raise NotFoundException."""
    mock_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundException, match="not found"):
        await author_service.partial_update_author(
            1, AuthorUpdateData(first_name="Any")
        )


@pytest.mark.asyncio
async def test_update_author_empty_first_name(author_service, mock_repo):
    """Updating with empty first_name should raise ValueError."""
    # Value object validates at creation
    with pytest.raises(ValueError, match="[Ff]irst name.*cannot be empty"):
        AuthorUpdateData(first_name="   ")


@pytest.mark.asyncio
async def test_update_author_name_conflict(author_service, mock_repo):
    """Updating to a conflicting name should raise ConflictException."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Old",
        last_name="Name",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )
    conflicting_author = AuthorEntity(
        id=2,
        first_name="New",
        last_name="Name",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )
    mock_repo.get_by_id.return_value = existing_author
    mock_repo.partial_update.return_value = existing_author
    mock_repo.partial_update.return_value = existing_author
    mock_repo.get_by_full_name.return_value = conflicting_author
    with pytest.raises(ConflictException, match="already exists"):
        await author_service.partial_update_author(
            1, AuthorUpdateData(first_name="New")
        )


@pytest.mark.asyncio
async def test_update_author_empty_last_name(author_service, mock_repo):
    """Updating with empty last_name should raise ValueError."""
    # Value object validates at creation
    with pytest.raises(ValueError, match="Last name cannot be empty"):
        AuthorUpdateData(last_name="   ")


@pytest.mark.asyncio
async def test_partial_update_normalizes_last_name_and_photo(author_service, mock_repo):
    """Partial update should normalize last_name and trim photo_url."""
    existing_author = AuthorEntity(
        id=1,
        first_name="John",
        last_name="doe",
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url="  http://img  ",
    )
    mock_repo.get_by_id.return_value = existing_author
    mock_repo.get_by_full_name.return_value = None
    mock_repo.partial_update.return_value = existing_author
    await author_service.partial_update_author(
        1, AuthorUpdateData(last_name="  smith  ", photo_url="  http://x  ")
    )
    normalized_data = mock_repo.partial_update.call_args[0][1]  # AuthorUpdateData
    assert normalized_data.last_name == "Smith"
    assert normalized_data.photo_url == "http://x"


@pytest.mark.asyncio
async def test_update_author_preserves_unchanged_fields(author_service, mock_repo):
    """Test update preserves fields not provided in update data."""
    existing_author = AuthorEntity(
        id=1,
        first_name="Original",
        last_name="Author",
        nationality="French",
        birth_date=parse_date("1900-01-01"),
        death_date=None,
        bio="Original bio",
        photo_url="url",
    )

    mock_repo.get_by_id.return_value = existing_author
    mock_repo.get_by_full_name.return_value = None
    mock_repo.partial_update.return_value = existing_author

    # Only update nationality
    update_data = AuthorUpdateData(nationality="British")

    await author_service.partial_update_author(1, update_data)

    # Verify update was called with normalized AuthorUpdateData containing only nationality
    normalized_data = mock_repo.partial_update.call_args[0][1]
    assert normalized_data.nationality == "British"
    # All other fields should be None (not provided)
    assert normalized_data.first_name is None
    assert normalized_data.last_name is None
    assert normalized_data.birth_date is None
    assert normalized_data.death_date is None
    assert normalized_data.bio is None
    assert normalized_data.photo_url is None
