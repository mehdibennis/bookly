"""initial clean schema for books/authors m2m

Revision ID: 0001_initial_clean_m2m
Revises:
Create Date: 2025-10-20 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_clean_m2m"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # authors table
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("death_date", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(), nullable=True),
        sa.Column("photo_url", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_authors_first_name", "authors", ["first_name"], unique=False)
    op.create_index("ix_authors_last_name", "authors", ["last_name"], unique=False)

    # books table
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # association table
    op.create_table(
        "book_authors",
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id"), primary_key=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("authors.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("book_authors")
    op.drop_index("ix_authors_last_name", table_name="authors")
    op.drop_index("ix_authors_first_name", table_name="authors")
    op.drop_table("books")
    op.drop_table("authors")
