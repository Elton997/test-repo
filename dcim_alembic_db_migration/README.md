# DCIM & RBAC Database Migrations (Oracle / Alembic)

This repository contains **standalone Alembic migrations** for the DCIM + RBAC schema, targeting an **Oracle** database.

- One **table per migration file** in `alembic/versions/`
- Each file has:
  - `_create_table()` – initial table definition
  - `_update_table()` – placeholder for future changes (before applying)
  - `downgrade()` – drops indexes / table
- **All tables are created in the `dcim` schema**

This repo is **independent** of the FastAPI service. It can be used purely for DB schema management.

## Schema Configuration

**All tables are created in the `dcim` schema.** Before running migrations:

1. Ensure the `dcim` schema exists in your Oracle database
2. Ensure the database user specified in `DB_URL` has privileges to create tables in the `dcim` schema

To create the schema (if it doesn't exist):
```sql
CREATE USER dcim IDENTIFIED BY dcim123;
GRANT CONNECT, RESOURCE TO dcim;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE TO dcim;
GRANT UNLIMITED TABLESPACE TO dcim;
```

Or use the provided script:
```bash
./create_schema_and_migrate.sh
```

Alternatively, if you want to use an existing user's schema, you can modify the migrations to use a different schema name, or grant the user privileges to create objects in the `dcim` schema.

---

## Schema Design Notes

**Location Tables Primary Key Design:**
- All location-related tables use **integer IDs as primary keys** (not string names):
  - `dcim_location.location_id` (Integer, PK)
  - `dcim_building.building_id` (Integer, PK)
  - `dcim_wing.wings_id` (Integer, PK)
  - `dcim_floor.floor_id` (Integer, PK)
  - `dcim_datacenter.dc_id` (Integer, PK)
  - `dcim_rack.id` (Integer, PK)
- The `name` column in these tables is a unique, non-null column for human-readable identification
- All foreign key relationships between location tables reference integer IDs for better performance and referential integrity
- See `SCHEMA_SUMMARY.md` in the project root for complete schema documentation

## 1. Prerequisites

- Python 3.10+ (recommended)
- Oracle DB instance (on-prem or cloud)
- Oracle client / driver:
  - `cx_Oracle` or `oracledb` (thin or thick mode)

---

## 2. Installation
Create and activate a virtual environment (recommended):

python -m venv venv
source venv/bin/activate
pip install alembic oracledb
# OR:
pip install alembic cx_Oracle


4. Configure Database Connection (DB_URL)
Alembic uses an environment variable DB_URL for connecting to Oracle.

**Default (local development with Oracle XE):**
```bash
# Uses dcim user on localhost (default if DB_URL not set)
export DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
```

**Custom connection:**
```bash
export DB_URL="oracle+oracledb://dcim:dcim123@hostname:1521/?service_name=ORCLPDB1"
```

**Windows PowerShell:**
```powershell
$env:DB_URL="oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1"
```

**Important:** 
- The `dcim` user must exist and have privileges to create tables in the `dcim` schema
- If the `dcim` schema doesn't exist, create it first (see Schema Configuration above)
- When using the `dcim` user, tables are automatically created in the `dcim` schema

5. Running Database Migrations

**Apply all migrations (upgrade to head):**
```bash
alembic upgrade head
```

**Rollback migrations:**
```bash
alembic downgrade -1          # Rollback one migration
alembic downgrade <revision> # Rollback to specific revision
alembic downgrade base        # Rollback all migrations (⚠️ DANGEROUS)
```

**Check migration status:**
```bash
alembic current   # Show current version
alembic history   # Show complete migration history
```

**Using Makefile (from project root):**
```bash
make migrate-up        # Apply all migrations
make migrate-down      # Rollback last migration
make migrate-current   # Show current version
make migrate-history   # Show migration history
make seed-data         # Seed database with sample data
make clear-seed        # Clear all seed data from database
```

6. Seeding Sample Data

After running migrations, you can seed the database with sample data from `db_scripts/seed_dcim.sql`:

**Using Makefile (Recommended):**
```bash
# From project root
make seed-data        # Seed database with sample data
make clear-seed       # Clear all seed data from database
```

**Using SQL*Plus:**
```bash
sqlplus user/password@hostname:1521/ORCLPDB1 @db_scripts/seed_dcim.sql
```

**Using Python/SQLAlchemy:**
```python
from sqlalchemy import create_engine, text

engine = create_engine(DB_URL)
with open('db_scripts/seed_dcim.sql', 'r') as f:
    seed_sql = f.read()

with engine.connect() as conn:
    conn.execute(text(seed_sql))
    conn.commit()
```

**Note:** The seed script includes sample data for:
- Users, tokens, locations, buildings, wings, floors, datacenters
- Racks, devices, device types, makes, models
- RBAC roles, menus, sub_menus, permissions
- Audit logs, environments, asset owners, applications

**Clearing Seed Data:**
To remove all seed data from the database (useful for testing or resetting):
```bash
make clear-seed
```

This will delete all data from seed tables in the correct order to respect foreign key constraints.

7. Migration File Pattern
Each file under alembic/versions/ follows this pattern:
def _create_table():
    op.create_table(..., schema="dcim")
    op.create_index(..., schema="dcim")

def _update_table():
    # Placeholder for pre-apply changes
    pass

def upgrade():
    _create_table()
    _update_table()

def downgrade():
    op.drop_index(..., schema="dcim")
    op.drop_table(..., schema="dcim")

8. Adding a New Table
To add a new table, create a new revision:
alembic revision -m "create dcim_new_table"
Edit the generated file and implement upgrade() and downgrade().
Apply with:
alembic upgrade head

9. Updating an Existing Table
Do NOT edit already-applied migration files.
Create a new revision:
alembic revision -m "alter dcim_devices add column foo"
Example:
def upgrade():
    op.add_column("dcim_devices", sa.Column("foo", sa.String(64)))

def downgrade():
    op.drop_column("dcim_devices", "foo")
Run:
alembic upgrade head
10. Usage With FastAPI (Optional)

If used alongside a FastAPI project:
Keep this Alembic repo separate
FastAPI connects to the same DB but does not share Alembic logic
Deployment steps:
Push migration files
Run alembic upgrade head
Deploy the FastAPI service

