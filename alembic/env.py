import os
import sys
from logging.config import fileConfig
from typing import Any, cast

from sqlalchemy import engine_from_config, pool

from alembic import context

# Permet d'importer app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

# Import models so that Base.metadata is populated
from app.db.models import associations, author_model, book_model  # noqa: F401
from app.db.session import Base

# Alembic Config object
config = context.config
cfg_name: str | None = getattr(config, "config_file_name", None)
if cfg_name:
    fileConfig(cfg_name)

target_metadata = Base.metadata

# Utilisation de la bonne URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        cast(dict[str, Any], config.get_section(config.config_ini_section)),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Exclude objects that exist in the DB but are not part of our SQLAlchemy metadata
        # This prevents autogenerate from attempting to drop unrelated tables (e.g., Keycloak)
        def include_object(object, name, type_, reflected, compare_to):
            # If Alembic is reflecting a table that's not present in metadata, skip it
            if type_ == "table" and reflected and compare_to is None:
                return False
            return True

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
