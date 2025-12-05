"""
Oracle-specific helper functions for Alembic migrations.
These functions make migrations idempotent by checking if objects exist before creating them.
"""

from alembic import op
import sqlalchemy as sa


def table_exists(schema: str, table_name: str) -> bool:
    """Check if a table exists in the given schema."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM all_tables WHERE owner = UPPER(:schema) AND table_name = UPPER(:table_name)"
        ),
        {"schema": schema, "table_name": table_name},
    )
    return result.scalar() > 0


def sequence_exists(schema: str, seq_name: str) -> bool:
    """Check if a sequence exists in the given schema."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM all_sequences WHERE sequence_owner = UPPER(:schema) AND sequence_name = UPPER(:seq_name)"
        ),
        {"schema": schema, "seq_name": seq_name},
    )
    return result.scalar() > 0


def trigger_exists(schema: str, trigger_name: str) -> bool:
    """Check if a trigger exists in the given schema."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM all_triggers WHERE owner = UPPER(:schema) AND trigger_name = UPPER(:trigger_name)"
        ),
        {"schema": schema, "trigger_name": trigger_name},
    )
    return result.scalar() > 0


def index_exists(schema: str, index_name: str) -> bool:
    """Check if an index exists in the given schema."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM all_indexes WHERE owner = UPPER(:schema) AND index_name = UPPER(:index_name)"
        ),
        {"schema": schema, "index_name": index_name},
    )
    return result.scalar() > 0


def create_sequence_if_not_exists(schema: str, seq_name: str) -> None:
    """Create a sequence if it doesn't exist."""
    if not sequence_exists(schema, seq_name):
        op.execute(sa.text(f"CREATE SEQUENCE {schema}.{seq_name} START WITH 1 INCREMENT BY 1"))


def create_trigger_for_autoincrement(schema: str, table_name: str, trigger_name: str, seq_name: str) -> None:
    """Create or replace a trigger for auto-increment ID."""
    # CREATE OR REPLACE will handle existing trigger
    trigger_sql = f"""
        CREATE OR REPLACE TRIGGER {schema}.{trigger_name}
        BEFORE INSERT ON {schema}.{table_name}
        FOR EACH ROW
        BEGIN
            IF \\:NEW.id IS NULL THEN
                SELECT {schema}.{seq_name}.NEXTVAL INTO \\:NEW.id FROM DUAL;
            END IF;
        END;
    """
    op.execute(sa.text(trigger_sql))


def drop_trigger_if_exists(schema: str, trigger_name: str) -> None:
    """Drop a trigger if it exists."""
    if trigger_exists(schema, trigger_name):
        op.execute(sa.text(f"DROP TRIGGER {schema}.{trigger_name}"))


def drop_sequence_if_exists(schema: str, seq_name: str) -> None:
    """Drop a sequence if it exists."""
    if sequence_exists(schema, seq_name):
        op.execute(sa.text(f"DROP SEQUENCE {schema}.{seq_name}"))


def drop_table_if_exists(schema: str, table_name: str) -> None:
    """Drop a table if it exists."""
    if table_exists(schema, table_name):
        op.execute(sa.text(f"DROP TABLE {schema}.{table_name} CASCADE CONSTRAINTS"))


def column_exists(schema: str, table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table and schema."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM all_tab_columns WHERE owner = UPPER(:schema) AND table_name = UPPER(:table_name) AND column_name = UPPER(:column_name)"
        ),
        {"schema": schema, "table_name": table_name, "column_name": column_name},
    )
    return result.scalar() > 0


def add_column_if_not_exists(schema: str, table_name: str, column: sa.Column) -> None:
    """Add a column if it doesn't exist."""
    if not column_exists(schema, table_name, column.name):
        op.add_column(table_name, column, schema=schema)


def drop_column_if_exists(schema: str, table_name: str, column_name: str) -> None:
    """Drop a column if it exists."""
    if column_exists(schema, table_name, column_name):
        op.drop_column(table_name, column_name, schema=schema)


def rename_column_if_exists(schema: str, table_name: str, old_column_name: str, new_column_name: str) -> None:
    """Rename a column if the old column exists and the new column doesn't exist.
    
    Oracle uses: ALTER TABLE schema.table_name RENAME COLUMN old_name TO new_name
    """
    if column_exists(schema, table_name, old_column_name) and not column_exists(schema, table_name, new_column_name):
        # Oracle requires direct SQL for renaming columns
        op.execute(sa.text(f'ALTER TABLE {schema}.{table_name} RENAME COLUMN {old_column_name} TO {new_column_name}'))


def rename_table_if_exists(schema: str, old_table_name: str, new_table_name: str) -> None:
    """Rename a table if the old table exists and the new table doesn't exist."""
    if table_exists(schema, old_table_name) and not table_exists(schema, new_table_name):
        op.rename_table(old_table_name, new_table_name, schema=schema)


def create_index_if_not_exists(schema: str, index_name: str, table_name: str, columns: list) -> None:
    """Create an index if it doesn't exist."""
    if not index_exists(schema, index_name):
        op.create_index(index_name, table_name, columns, schema=schema)


def drop_index_if_exists(schema: str, index_name: str, table_name: str) -> None:
    """Drop an index if it exists."""
    if index_exists(schema, index_name):
        op.drop_index(index_name, table_name=table_name, schema=schema)

