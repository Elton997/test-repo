from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent folder to path for oracle_helpers import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get DB URL from environment
db_url = os.getenv("DB_URL")
if not db_url:
    raise RuntimeError("DB_URL environment variable is not set")

config.set_main_option("sqlalchemy.url", db_url)

target_metadata = None  # we’re using pure-op migrations, not autogenerate


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_num_length=128,
    )

    with context.begin_transaction():
        context.run_migrations()


def _ensure_alembic_version_table(connection) -> None:
    """Ensure alembic_version table exists with correct column size (VARCHAR2(128))."""
    from sqlalchemy import text
    
    # Check if table exists
    result = connection.execute(text("""
        SELECT COUNT(*) FROM all_tables 
        WHERE owner = 'DCIM' AND table_name = 'ALEMBIC_VERSION'
    """))
    table_exists = result.scalar() > 0
    
    if not table_exists:
        # Create table with correct column size BEFORE Alembic does
        print("[env.py] Creating alembic_version table with VARCHAR2(128)...")
        connection.execute(text("""
            CREATE TABLE dcim.alembic_version (
                version_num VARCHAR2(128) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """))
        connection.commit()
        print("[env.py] Created alembic_version table")
    else:
        # Table exists - check and fix column size if needed
        result = connection.execute(text("""
            SELECT data_length FROM all_tab_columns 
            WHERE owner = 'DCIM' AND table_name = 'ALEMBIC_VERSION' AND column_name = 'VERSION_NUM'
        """))
        current_size = result.scalar()
        if current_size and current_size < 128:
            print(f"[env.py] Fixing alembic_version column size ({current_size} -> 128)...")
            connection.execute(text("ALTER TABLE dcim.alembic_version MODIFY version_num VARCHAR2(128)"))
            connection.commit()
            print("[env.py] Fixed alembic_version column")
        else:
            print("[env.py] alembic_version table OK")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Ensure alembic_version table exists with correct column size
        _ensure_alembic_version_table(connection)
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_num_length=128,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
