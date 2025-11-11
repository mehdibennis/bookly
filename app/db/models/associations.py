from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.session import Base

# Association table for Book <-> Author many-to-many
book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id"), primary_key=True),
)
