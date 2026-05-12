import logging
from logging.config import fileConfig

from sqlalchemy import pool
from alembic import context

from app.db import Base
from app.config import settings  # <-- añadir esta línea
from app import models  # noqa: F401

config = context.config
# Override the URL from .env, so we don't duplicate config in alembic.ini.
# Strip +psycopg from the URL just for Alembic — the sync driver doesn't need it.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from app.db import sync_engine

    with sync_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()