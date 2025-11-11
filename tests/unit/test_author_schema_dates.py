import pytest
from pydantic import ValidationError

from app.repositories.author_repository import _parse_date
from app.schemas.author_schema import AuthorCreate, AuthorUpdate


def test_author_create_invalid_date_raises_validation_error():
    """Test that invalid date format raises ValidationError in AuthorCreate."""
    # Invalid format that matches none of the accepted patterns
    with pytest.raises(ValidationError, match="ne correspond à aucun format accepté"):
        AuthorCreate(first_name="Ada", last_name="Lovelace", birth_date="31-02-2020")


def test_author_create_completely_invalid_date():
    """Test completely invalid date string in AuthorCreate."""
    with pytest.raises(ValidationError, match="ne correspond à aucun format accepté"):
        AuthorCreate(first_name="Test", last_name="Author", birth_date="not-a-date-at-all")


def test_author_update_invalid_date_raises_validation_error():
    """Test that invalid date format raises ValidationError in AuthorUpdate."""
    # Invalid format that matches none of the accepted patterns
    with pytest.raises(ValidationError, match="ne correspond à aucun format accepté"):
        AuthorUpdate(birth_date="2020/31/12")


def test_author_update_invalid_death_date():
    """Test invalid death_date format in AuthorUpdate."""
    with pytest.raises(ValidationError, match="ne correspond à aucun format accepté"):
        AuthorUpdate(death_date="invalid-date-format")


def test_parse_date_unsupported_type_returns_none():
    # Passing an unsupported type (e.g., dict) should return None gracefully
    assert _parse_date({"not": "a date"}) is None


def test_parse_date_iso_string_valid():
    # Valid ISO date string should be parsed to a date object
    from datetime import date

    parsed = _parse_date("2020-01-02")
    assert isinstance(parsed, date)
    assert parsed == date(2020, 1, 2)
