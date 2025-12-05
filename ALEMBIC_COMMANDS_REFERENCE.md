# Alembic Commands Reference

This document provides the direct Alembic commands equivalent to the Makefile migration commands.

## Prerequisites

Before running any Alembic commands, you need to:

1. **Navigate to the migration directory:**
   ```bash
   cd dcim_alembic_db_migration
   ```

2. **Set up virtual environment (if not already done):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install alembic oracledb
   ```

3. **Set the DB_URL environment variable:**
   ```bash
   # Default (dcim user on localhost)
   export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
   
   # Custom connection
   export DB_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"
   ```

   **Windows PowerShell:**
   ```powershell
   $env:DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
   ```

4. **Set PYTHONPATH (for some operations):**
   ```bash
   export PYTHONPATH=$(pwd):$PYTHONPATH
   ```

## Oracle Helper Functions

This project includes idempotent helper functions in `oracle_helpers.py` that make migrations safe to run multiple times. **Always use these helpers instead of direct Alembic operations** to prevent errors when objects already exist or don't exist.

### Available Helper Functions

| Function | Purpose |
|----------|---------|
| `column_exists(schema, table_name, column_name)` | Check if a column exists |
| `add_column_if_not_exists(schema, table_name, column)` | Add column only if it doesn't exist |
| `drop_column_if_exists(schema, table_name, column_name)` | Drop column only if it exists |
| `rename_column_if_exists(schema, table_name, old_name, new_name)` | Rename column safely |
| `table_exists(schema, table_name)` | Check if a table exists |
| `drop_table_if_exists(schema, table_name)` | Drop table only if it exists |
| `rename_table_if_exists(schema, old_name, new_name)` | Rename table safely |
| `index_exists(schema, index_name)` | Check if an index exists |
| `create_index_if_not_exists(schema, index_name, table_name, columns)` | Create index only if it doesn't exist |
| `drop_index_if_exists(schema, index_name, table_name)` | Drop index only if it exists |

### Import Statement

All migration files should import the helper functions:
```python
from oracle_helpers import (
    add_column_if_not_exists,
    drop_column_if_exists,
    rename_column_if_exists,
    rename_table_if_exists,
    create_index_if_not_exists,
    drop_index_if_exists,
    drop_table_if_exists,
    table_exists,
    column_exists,
)
```



### Migration Creation with Specific Operations

For operations like add column, drop column, rename, etc., you need to:

1. **Create the migration file:**
   ```bash
   alembic revision -m "your message here"
   ```

2. **Edit the generated file** in `alembic/versions/` to add the specific operations.

Below are examples for each operation type:

#### Add Column

```bash
# Step 1: Create migration
alembic revision -m "add column to table"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import add_column_if_not_exists, drop_column_if_exists

def upgrade() -> None:
    add_column_if_not_exists('dcim', 'dcim_device', sa.Column('new_field', sa.String(255), nullable=True))

def downgrade() -> None:
    drop_column_if_exists('dcim', 'dcim_device', 'new_field')
```

**Benefits:**
- Won't fail if column already exists
- Safe to run multiple times
- Idempotent migration

#### Drop Column

```bash
# Step 1: Create migration
alembic revision -m "remove deprecated field"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import add_column_if_not_exists, drop_column_if_exists

def upgrade() -> None:
    drop_column_if_exists('dcim', 'dcim_device', 'old_field')

def downgrade() -> None:
    # Note: Adjust the column type to match the original
    add_column_if_not_exists('dcim', 'dcim_device', sa.Column('old_field', sa.String(255), nullable=True))
```

**Benefits:**
- Won't fail if column doesn't exist
- Safe to run multiple times
- Idempotent migration

#### Rename Table

```bash
# Step 1: Create migration
alembic revision -m "rename table"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import rename_table_if_exists

def upgrade() -> None:
    rename_table_if_exists('dcim', 'old_table_name', 'new_table_name')

def downgrade() -> None:
    rename_table_if_exists('dcim', 'new_table_name', 'old_table_name')
```

**Benefits:**
- Won't fail if old table doesn't exist or new table already exists
- Safe to run multiple times
- Idempotent migration

#### Rename Column

```bash
# Step 1: Create migration
alembic revision -m "rename column"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import rename_column_if_exists

def upgrade() -> None:
    rename_column_if_exists('dcim', 'table_name', 'old_column_name', 'new_column_name')

def downgrade() -> None:
    rename_column_if_exists('dcim', 'table_name', 'new_column_name', 'old_column_name')
```

**Benefits:**
- Won't fail if old column doesn't exist or new column already exists
- Safe to run multiple times
- Idempotent migration

#### Add Table

```bash
# Step 1: Create migration
alembic revision -m "create new table"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import drop_table_if_exists, table_exists

def upgrade() -> None:
    if not table_exists('dcim', 'new_table'):
        op.create_table(
            'new_table',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            schema='dcim'
        )

def downgrade() -> None:
    drop_table_if_exists('dcim', 'new_table')
```

**Benefits:**
- Won't fail if table already exists
- Safe to run multiple times
- Idempotent migration
  
```bash
# Step 1: Create migration
alembic revision -m "drop table"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import drop_table_if_exists, table_exists

def upgrade() -> None:
    drop_table_if_exists('dcim', 'table_name')

def downgrade() -> None:
    # Note: You need to recreate the table structure exactly as it was
    if not table_exists('dcim', 'table_name'):
        op.create_table(
            'table_name',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            schema='dcim'
        )
```

**Benefits:**
- Won't fail if table doesn't exist
- Safe to run multiple times
- Idempotent migration

#### Modify Column

```bash
# Step 1: Create migration
alembic revision -m "modify column type"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import column_exists

def upgrade() -> None:
    # Check if column exists before modifying
    if column_exists('dcim', 'table_name', 'column_name'):
        op.alter_column('table_name', 'column_name',
                        type_=sa.String(500),  # New type
                        nullable=False,       # New nullable setting
                        schema='dcim')

def downgrade() -> None:
    # Check if column exists before modifying
    if column_exists('dcim', 'table_name', 'column_name'):
        op.alter_column('table_name', 'column_name',
                        type_=sa.String(255),  # Original type
                        nullable=True,          # Original nullable setting
                        schema='dcim')
```

**Note:** For Oracle, modifying column types may require special handling. Always test thoroughly.

**Benefits:**
- Won't fail if column doesn't exist
- Safe to run multiple times

#### Add Index

```bash
# Step 1: Create migration
alembic revision -m "add index"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import create_index_if_not_exists, drop_index_if_exists

def upgrade() -> None:
    create_index_if_not_exists('dcim', 'idx_table_column', 'table_name', ['column1', 'column2'])

def downgrade() -> None:
    drop_index_if_exists('dcim', 'idx_table_column', 'table_name')
```

**Benefits:**
- Won't fail if index already exists
- Safe to run multiple times
- Idempotent migration

#### Drop Index

```bash
# Step 1: Create migration
alembic revision -m "drop index"

# Step 2: Edit the generated file
```

**Full Example:**
```python
from alembic import op
import sqlalchemy as sa
from oracle_helpers import create_index_if_not_exists, drop_index_if_exists

def upgrade() -> None:
    drop_index_if_exists('dcim', 'idx_name', 'table_name')

def downgrade() -> None:
    create_index_if_not_exists('dcim', 'idx_name', 'table_name', ['column1', 'column2'])
```

**Benefits:**
- Won't fail if index doesn't exist
- Safe to run multiple times
- Idempotent migration

## Complete Command Examples

### Apply Migrations
```bash
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
alembic upgrade head
```

### Rollback Last Migration
```bash
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
alembic downgrade -1
```

### Check Current Version
```bash
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
alembic current
```

### View History
```bash
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
alembic history
```

### Create New Migration
```bash
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
export PYTHONPATH=$(pwd):$PYTHONPATH
alembic revision -m "your migration message"
```

## Additional Alembic Commands

### Rollback to Specific Revision
```bash
alembic downgrade <revision_id>  # Rollback to specific revision
alembic downgrade base           # Rollback all migrations (⚠️ DANGEROUS)
```

### Upgrade to Specific Revision
```bash
alembic upgrade <revision_id>    # Upgrade to specific revision
```

### Show Migration Branches
```bash
alembic branches                 # Show unmerged branches
alembic merge -m "merge message" <rev1> <rev2>  # Merge branches
```

### Show SQL for Migration (without executing)
```bash
alembic upgrade head --sql       # Show SQL that would be executed
```

## Important Notes

1. **Schema Name**: All operations use `schema='dcim'` - make sure to include this in your migration code.

2. **Import Statements**: In your migration files, you'll need:
   ```python
   from alembic import op
   import sqlalchemy as sa
   from oracle_helpers import (
       add_column_if_not_exists,
       drop_column_if_exists,
       rename_column_if_exists,
       rename_table_if_exists,
       create_index_if_not_exists,
       drop_index_if_exists,
       drop_table_if_exists,
       table_exists,
       column_exists,
   )
   ```
   
   **Always use helper functions** instead of direct `op.*` calls for column, table, and index operations to ensure idempotency.

3. **Migration File Location**: All migration files are created in `dcim_alembic_db_migration/alembic/versions/`

4. **Never Edit Applied Migrations**: Once a migration has been applied, never edit it. Always create a new migration for changes.

5. **Test Downgrades**: Always test that your `downgrade()` function works correctly before applying migrations to production.

6. **Column Types**: When creating downgrade functions, you need to know the original column types. Keep track of this information.

7. **Use Helper Functions**: Always use the helper functions from `oracle_helpers.py` for all operations (add/drop/rename columns, tables, indexes) to ensure migrations are idempotent and won't fail if objects already exist or don't exist.

8. **Idempotency**: All migrations should be idempotent (safe to run multiple times). The helper functions ensure this by checking if objects exist before creating/dropping them.

## Quick Setup Script

You can create a simple script to set up the environment:

```bash
#!/bin/bash
# setup-alembic.sh
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1}"
export PYTHONPATH=$(pwd):$PYTHONPATH
```

Then source it before running alembic commands:
```bash
source setup-alembic.sh
alembic upgrade head
```

