import importlib
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import src.config.env as env
import src.database.factories as factories
from src.database.session import Base

# Import factories package itself first so its __init__.py can register models.
importlib.import_module("src.database.factories")

# Then import any concrete modules under factories/ (if present).
for loader, module_name, is_pkg in pkgutil.iter_modules(factories.__path__):
    importlib.import_module(f"src.database.factories.{module_name}")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return env.DATABASE_URL


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Ensure we have a real mapping (dict) before using the dictionary unpack operator
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        {
            **dict(section),
            "sqlalchemy.url": get_url(),
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
