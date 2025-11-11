"""
Tests for domain entities.
Tests normalization and entity behavior.
"""

from datetime import date, datetime

from app.domain.entities import AuthorEntity, BookEntity


class TestAuthorEntity:
    """Tests for AuthorEntity."""

    def test_author_entity_creation_minimal(self):
        """Create author with minimal required fields."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe")
        assert author.id == 1
        assert author.first_name == "John"
        assert author.last_name == "Doe"
        assert author.birth_date is None
        assert author.nationality is None

    def test_author_entity_creation_all_fields(self):
        """Create author with all fields."""
        birth = date(1950, 1, 1)
        death = date(2020, 1, 1)
        created = datetime(2023, 1, 1, 12, 0, 0)
        updated = datetime(2023, 1, 2, 12, 0, 0)

        author = AuthorEntity(
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

        assert author.birth_date == birth
        assert author.death_date == death
        assert author.nationality == "USA"
        assert author.bio == "Test bio"
        assert author.photo_url == "http://example.com/photo.jpg"
        assert author.created_at == created
        assert author.updated_at == updated

    def test_normalize_first_name(self):
        """Normalize should title-case and strip first name."""
        author = AuthorEntity(id=1, first_name="  john  ", last_name="Doe")
        author.normalize()
        assert author.first_name == "John"

    def test_normalize_last_name(self):
        """Normalize should title-case and strip last name."""
        author = AuthorEntity(id=1, first_name="John", last_name="  doe  ")
        author.normalize()
        assert author.last_name == "Doe"

    def test_normalize_nationality(self):
        """Normalize should title-case and strip nationality."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe", nationality="  france  ")
        author.normalize()
        assert author.nationality == "France"

    def test_normalize_nationality_none(self):
        """Normalize should handle None nationality."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe", nationality=None)
        author.normalize()
        assert author.nationality is None

    def test_normalize_bio(self):
        """Normalize should strip bio whitespace."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe", bio="  Test bio  ")
        author.normalize()
        assert author.bio == "Test bio"

    def test_normalize_bio_none(self):
        """Normalize should handle None bio."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe", bio=None)
        author.normalize()
        assert author.bio is None

    def test_normalize_photo_url(self):
        """Normalize should strip photo_url whitespace."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe", photo_url="  http://example.com  ")
        author.normalize()
        assert author.photo_url == "http://example.com"

    def test_normalize_photo_url_none(self):
        """Normalize should handle None photo_url."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe", photo_url=None)
        author.normalize()
        assert author.photo_url is None

    def test_normalize_returns_self(self):
        """Normalize should return self for chaining."""
        author = AuthorEntity(id=1, first_name="John", last_name="Doe")
        result = author.normalize()
        assert result is author


class TestBookEntity:
    """Tests for BookEntity."""

    def test_book_entity_creation_minimal(self):
        """Create book with minimal required fields."""
        book = BookEntity(id=1, title="Test Book")
        assert book.id == 1
        assert book.title == "Test Book"
        assert book.authors == []
        assert book.authors_details == []
        assert book.authors_number is None

    def test_book_entity_creation_with_authors(self):
        """Create book with authors."""
        book = BookEntity(id=1, title="Test Book", authors=[1, 2, 3])
        assert book.authors == [1, 2, 3]

    def test_book_entity_creation_with_authors_details(self):
        """Create book with authors details."""
        details = [{"id": 1, "name": "Author 1"}, {"id": 2, "name": "Author 2"}]
        book = BookEntity(id=1, title="Test Book", authors_details=details)
        assert book.authors_details == details

    def test_book_entity_creation_with_authors_number(self):
        """Create book with authors number."""
        book = BookEntity(id=1, title="Test Book", authors_number=3)
        assert book.authors_number == 3

    def test_normalize_title(self):
        """Normalize should title-case and strip title."""
        book = BookEntity(id=1, title="  test book  ")
        book.normalize()
        assert book.title == "Test Book"

    def test_normalize_title_complex(self):
        """Normalize should handle complex titles."""
        book = BookEntity(id=1, title="the lord of the rings")
        book.normalize()
        assert book.title == "The Lord Of The Rings"

    def test_normalize_returns_self(self):
        """Normalize should return self for chaining."""
        book = BookEntity(id=1, title="Test")
        result = book.normalize()
        assert result is book

    def test_book_entity_default_factory_authors(self):
        """Default factory should create independent lists for authors."""
        book1 = BookEntity(id=1, title="Book 1")
        book2 = BookEntity(id=2, title="Book 2")

        book1.authors.append(1)

        assert book1.authors == [1]
        assert book2.authors == []

    def test_book_entity_default_factory_authors_details(self):
        """Default factory should create independent lists for authors_details."""
        book1 = BookEntity(id=1, title="Book 1")
        book2 = BookEntity(id=2, title="Book 2")

        book1.authors_details.append({"id": 1})

        assert len(book1.authors_details) == 1
        assert len(book2.authors_details) == 0
