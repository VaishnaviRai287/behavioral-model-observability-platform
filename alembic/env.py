from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import your Base so Alembic knows about your tables
from app.database import Base
from app.models import ml_model  # noqa: F401 — must import to register models
from app.models import probe_session  # noqa: F401
from app.models import probe_result   # noqa: F401
from app.models import fingerprint    # noqa: F401
from app.models import prediction_log   # noqa: F401
from app.models import faiss_index  # noqa: F401
from app.models import drift_event  # noqa: F401
from app.models import alert  # noqa: F401

from app.config import settings
import os
db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or settings.database_url


config = context.config
fileConfig(config.config_file_name)

# Dynamically override the database URL using the environment or application settings
config.set_main_option("sqlalchemy.url", db_url)

# This is the key line: tell Alembic to use your ORM metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    section = config.get_section(config.config_ini_section)
    section["sqlalchemy.url"] = db_url
    connectable = engine_from_config(
        section,
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
