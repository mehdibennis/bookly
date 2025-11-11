from datetime import date
from uuid import uuid4

import pytest

from app.db.session import get_session
from app.domain.value_objects import AuthorCreateData, AuthorUpdateData, PaginationParams
from app.main import app
from app.repositories.author_repository import AuthorRepository


@pytest.mark.asyncio
async def test_author_repository_create_and_get_by_id(client):
    """Test creating author and retrieving by ID."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        first_name = f"Test_{uuid4()}"
        last_name = f"Author_{uuid4()}"

        create_data = AuthorCreateData(
            first_name=first_name,
            last_name=last_name,
            nationality="French",
            birth_date=date(1900, 1, 1),
            death_date=None,
            bio="Test bio",
            photo_url=None,
        )

        created = await repo.create(create_data)
        assert created.id is not None
        assert created.first_name == first_name
        assert created.last_name == last_name

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.first_name == first_name
        assert fetched.last_name == last_name
        assert fetched.nationality == "French"


@pytest.mark.asyncio
async def test_author_repository_get_by_full_name(client):
    """Test retrieving author by full name."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        first_name = f"Unique_{uuid4()}"
        last_name = f"Name_{uuid4()}"

        create_data = AuthorCreateData(
            first_name=first_name,
            last_name=last_name,
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        )

        await repo.create(create_data)

        fetched = await repo.get_by_full_name(first_name, last_name)
        assert fetched is not None
        assert fetched.first_name == first_name
        assert fetched.last_name == last_name


@pytest.mark.asyncio
async def test_author_repository_get_paginated(client):
    """Test pagination."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        for i in range(5):
            create_data = AuthorCreateData(
                first_name=f"Author_{uuid4()}",
                last_name=f"Test_{i}",
                nationality=None,
                birth_date=None,
                death_date=None,
                bio=None,
                photo_url=None,
            )
            await repo.create(create_data)

        pagination = PaginationParams(page=1, size=2)
        result = await repo.get_paginated(pagination)

        assert len(result.data) == 2
        assert result.meta.total >= 5
        assert result.meta.page == 1
        assert result.meta.size == 2


@pytest.mark.asyncio
async def test_author_repository_update(client):
    """Test updating author."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        create_data = AuthorCreateData(
            first_name="Original",
            last_name="Author",
            nationality="French",
            birth_date=date(1900, 1, 1),
            death_date=None,
            bio="Original bio",
            photo_url=None,
        )

        created = await repo.create(create_data)

        update_data = AuthorUpdateData(
            first_name="Updated",
            last_name="Author",
            nationality="British",
            birth_date=date(1900, 1, 1),
            death_date=None,
            bio="Updated bio",
            photo_url=None,
        )

        updated = await repo.update(created.id, update_data)
        assert updated.first_name == "Updated"
        assert updated.nationality == "British"
        assert updated.bio == "Updated bio"


@pytest.mark.asyncio
async def test_author_repository_partial_update(client):
    """Test partial update."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        create_data = AuthorCreateData(
            first_name="Original",
            last_name="Author",
            nationality="French",
            birth_date=date(1900, 1, 1),
            death_date=None,
            bio="Original bio",
            photo_url=None,
        )

        created = await repo.create(create_data)

        update_data = AuthorUpdateData(nationality="British", bio="Updated bio")
        updated = await repo.partial_update(created.id, update_data)

        assert updated is not None
        assert updated.first_name == "Original"
        assert updated.nationality == "British"
        assert updated.bio == "Updated bio"


@pytest.mark.asyncio
async def test_author_repository_delete(client):
    """Test deleting author."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        create_data = AuthorCreateData(
            first_name="ToDelete",
            last_name="Author",
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        )

        created = await repo.create(create_data)
        deleted = await repo.delete(created.id)

        assert deleted is True

        fetched = await repo.get_by_id(created.id)
        assert fetched is None


@pytest.mark.asyncio
async def test_author_repository_get_by_id_not_found(client):
    """Test get_by_id returns None for non-existent author."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)
        result = await repo.get_by_id(99999)
        assert result is None


@pytest.mark.asyncio
async def test_author_repository_delete_not_found(client):
    """Test delete returns False for non-existent author."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)
        result = await repo.delete(99999)
        assert result is False


@pytest.mark.asyncio
async def test_author_repository_partial_update_not_found(client):
    """Test partial_update returns None for non-existent author."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)
        update_data = AuthorUpdateData(nationality="Test")
        result = await repo.partial_update(99999, update_data)
        assert result is None


@pytest.mark.asyncio
async def test_author_repository_update_with_dates(client):
    """Test updating author with date fields."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        # Create author
        first_name = f"Test_{uuid4()}"
        last_name = f"Author_{uuid4()}"
        create_data = AuthorCreateData(
            first_name=first_name,
            last_name=last_name,
            nationality="French",
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        )
        created = await repo.create(create_data)
        assert created.id is not None

        # Update with dates
        update_data = AuthorUpdateData(
            first_name=first_name,
            last_name=last_name,
            birth_date=date(1950, 1, 1),
            death_date=date(2020, 12, 31),
            nationality="British",
            bio="Updated bio",
            photo_url="http://example.com/photo.jpg",
        )
        updated = await repo.update(created.id, update_data)

        assert updated is not None
        assert updated.birth_date == date(1950, 1, 1)
        assert updated.death_date == date(2020, 12, 31)
        assert updated.nationality == "British"
        assert updated.bio == "Updated bio"
        assert updated.photo_url == "http://example.com/photo.jpg"


@pytest.mark.asyncio
async def test_author_repository_partial_update_with_dates(client):
    """Test partial_update with date fields."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        # Create author
        first_name = f"Test_{uuid4()}"
        last_name = f"Author_{uuid4()}"
        create_data = AuthorCreateData(
            first_name=first_name,
            last_name=last_name,
            nationality="French",
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        )
        created = await repo.create(create_data)
        assert created.id is not None

        # Partial update with dates
        update_data = AuthorUpdateData(
            birth_date=date(1960, 5, 15),
            death_date=date(2025, 3, 20),
        )
        updated = await repo.partial_update(created.id, update_data)

        assert updated is not None
        assert updated.birth_date == date(1960, 5, 15)
        assert updated.death_date == date(2025, 3, 20)
        # Other fields should remain unchanged
        assert updated.first_name == first_name
        assert updated.last_name == last_name
        assert updated.nationality == "French"


@pytest.mark.asyncio
async def test_parse_date_invalid_string(client):
    """Test _parse_date with invalid date string."""
    from app.repositories.author_repository import _parse_date

    # Invalid date string should return None
    result = _parse_date("not-a-date")
    assert result is None

    # Invalid format should return None
    result = _parse_date("2023/01/01")  # Wrong separator
    assert result is None

    # Empty string should return None
    result = _parse_date("")
    assert result is None


@pytest.mark.asyncio
async def test_author_repository_update_not_found(client):
    """Test update returns None for non-existent author."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)
        update_data = AuthorUpdateData(
            first_name="Test",
            last_name="Author",
            nationality="French",
        )
        result = await repo.update(99999, update_data)
        assert result is None


@pytest.mark.asyncio
async def test_author_repository_partial_update_invalid_field(client):
    """Test partial_update skips fields that don't exist on the model."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)

        # Create author
        first_name = f"Test_{uuid4()}"
        last_name = f"Author_{uuid4()}"
        create_data = AuthorCreateData(
            first_name=first_name,
            last_name=last_name,
            nationality="French",
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        )
        created = await repo.create(create_data)
        assert created.id is not None

        # Manually create an AuthorUpdateData with a fake field
        # We'll use a dict and modify it to simulate an invalid field
        update_data = AuthorUpdateData(nationality="British")

        # Add a fake field to __dict__ (this won't be in the dataclass normally)
        # This is to test the hasattr check in partial_update
        object.__setattr__(update_data, "_fake_field_123", "value")

        # The update should still work, skipping the invalid field
        updated = await repo.partial_update(created.id, update_data)

        assert updated is not None
        assert updated.nationality == "British"
