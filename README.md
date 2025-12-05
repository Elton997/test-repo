# DCIM Repository

Data Center Infrastructure Management (DCIM) system with FastAPI backend and Angular frontend.

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Set Up Local Oracle Database](#0-set-up-local-oracle-database-optional)
  - [Create DCIM Schema](#1-create-dcim-schema)
  - [Install Dependencies](#2-install-dependencies)
  - [Configure Database](#3-configure-database)
  - [Run Database Migrations](#4-run-database-migrations)
  - [Seed Sample Data](#5-seed-sample-data-optional)
  - [Start Services](#6-start-services)
- [Makefile Commands](#makefile-commands)
  - [Service Management](#service-management)
  - [Installation](#installation)
  - [Database Migrations](#database-migrations)
  - [Data Seeding](#data-seeding)
  - [Utilities](#utilities)
  - [Oracle Docker Commands](#oracle-docker-commands)
- [Running Services](#running-services)
  - [Backend (FastAPI)](#backend-fastapi)
  - [Frontend (Angular)](#frontend-angular)
  - [Both Services](#both-services)
- [Database Migrations](#database-migrations-1)
  - [Running Migrations](#running-migrations)
  - [Creating New Migrations](#creating-new-migrations)
  - [Checking Migration Status](#checking-migration-status)
  - [Rolling Back Migrations](#rolling-back-migrations)
- [Development](#development)
  - [Backend Development](#backend-development)
  - [Logging System](#logging-system)
    - [Automatic Request/Response Logging](#automatic-requestresponse-logging)
    - [Configuration](#configuration)
    - [Using the Logger in New API Endpoints](#using-the-logger-in-new-api-endpoints)
    - [Log Output Examples](#log-output-examples)
    - [Notes](#notes)
  - [Frontend Development](#frontend-development)
  - [Database Schema](#database-schema)
- [Environment Variables](#environment-variables)
  - [Backend](#backend)
  - [Migrations](#migrations)
  - [Custom Package Repositories](#custom-package-repositories)
- [Troubleshooting](#troubleshooting)
  - [Services won't start](#services-wont-start)
  - [Migration errors](#migration-errors)
  - [Artifactory/Repository Issues](#artifactoryrepository-issues)
  - [Clean installation](#clean-installation)
- [API Endpoints](#api-endpoints)
  - [DCIM Endpoints](#dcim-endpoints)
  - [Authentication](#authentication)
- [License](#license)
- [Contributing](#contributing)

## Project Structure

```
dcim-repo/
├── dcim_backend_fastapi/     # FastAPI backend service
│   └── app/                   # Application code
├── dcim_frontend/             # Angular frontend application
├── dcim_alembic_db_migration/ # Database migrations (Alembic)
├── Makefile                   # Build and run commands
└── README.md                  # This file
```

## Prerequisites

- **Python 3.10+** (for backend and migrations)
- **Node.js 18+** and **npm** (for frontend)
- **Oracle Database** (for data storage) - Can use local Docker instance (see below)
- **Docker** and **Docker Compose** (for local Oracle database)
- **Make** (for using Makefile commands)

## Quick Start

### 0. Set Up Local Oracle Database (Optional)

For local development, you can run Oracle XE (Express Edition) using Docker or Podman:

```bash
# Using Makefile (recommended)
make oracle-setup

# Or using the helper script directly
./oracle-xe.sh start
```

**Note:** 
- Works with both **Docker** and **Podman** (automatically detects which is available)
- Uses community-maintained image (`gvenzl/oracle-xe`), no Oracle Container Registry login required
- No Docker Compose needed - uses raw container commands

After setup, the database will be available at:
- **Host:** localhost
- **Port:** 1521
- **Service Name:** ORCLPDB1
- **Username:** system
- **Password:** Oracle123

**Oracle XE Commands:**
```bash
# Using Makefile
make oracle-up        # Start Oracle container
make oracle-down      # Stop Oracle container
make oracle-logs      # View container logs
make oracle-shell     # Enter container shell
make oracle-status    # Show container status
make oracle-remove    # Remove container and volume

# Or using the script directly
./oracle-xe.sh start
./oracle-xe.sh stop
./oracle-xe.sh logs
./oracle-xe.sh shell
./oracle-xe.sh status
./oracle-xe.sh remove
```

### 1. Create DCIM Schema

Before running migrations, create the DCIM user/schema in Oracle:

```bash
# Create the 'dcim' user with required privileges
make create-schema
```

This runs the `create_schema_and_migrate.sh` script which:
- Creates the `dcim` user with password `dcim123`
- Grants required privileges (CONNECT, RESOURCE, CREATE TABLE, etc.)
- Applies all migrations automatically

**Note:** This requires connecting as the `system` user. Set `DB_URL` if using non-default credentials.

### 2. Install Dependencies

```bash
# Install backend dependencies
make install-backend

# Install frontend dependencies
make install-frontend
```

#### Using Custom Artifactory/Repository

You can use custom package repositories (Artifactory, private registries, or mirrors) for both Python and Node.js dependencies:

**Python (pip) with custom repository:**
```bash
# Using PyPI mirror or Artifactory
make install-backend PIP_INDEX_URL=https://pypi.org/simple

# Using private Artifactory (with authentication via .netrc or pip.conf)
make install-backend PIP_INDEX_URL=https://artifactory.company.com/api/pypi/pypi/simple

# Using environment variable
export PIP_INDEX_URL=https://pypi.org/simple
make install-backend
```

**Node.js (npm) with custom registry:**
```bash
# Using custom npm registry or Artifactory
make install-frontend NPM_REGISTRY=https://registry.npmjs.org/

# Using private Artifactory
make install-frontend NPM_REGISTRY=https://artifactory.company.com/api/npm/npm/

# Using environment variable
export NPM_REGISTRY=https://registry.npmjs.org/
make install-frontend
```

**Migrations with custom pip repository:**
```bash
# Run migrations using custom pip index
make migrate-up PIP_INDEX_URL=https://pypi.org/simple
```

**Note:** All custom repository options are optional. If not specified, the default public repositories (PyPI and npm registry) will be used.

### 3. Configure Database

Set the `DATABASE_URL` and `DB_URL` environment variables for database connections.

**For local Docker Oracle instance:**
```bash
export DATABASE_URL="oracle+oracledb://system:Oracle123@localhost:1521/?service_name=ORCLPDB1"
export DB_URL="oracle+oracledb://system:Oracle123@localhost:1521/?service_name=ORCLPDB1"
```

**For remote Oracle database:**
```bash
export DATABASE_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"
export DB_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"
```

**Tip:** You can create a `.env` file in the project root with these variables to avoid setting them each time.

### 4. Run Database Migrations

```bash
make migrate-up
```

### 5. Seed Sample Data (Optional)

```bash
# Load sample data into the database
make seed-data

# To clear seeded data later
make clear-seed
```

### 6. Start Services

```bash
# Start both backend and frontend
make run-all

# Or start individually:
make backend    # Start backend only (port 8000)
make frontend   # Start frontend only (port 4200)
```

## Makefile Commands

The project includes a comprehensive Makefile for common tasks. Run `make help` to see all available commands.

### Service Management

| Command | Description |
|---------|-------------|
| `make backend` | Start FastAPI backend server on http://localhost:8000 |
| `make frontend` | Start Angular frontend server on http://localhost:4200 |
| `make run-all` | Start both backend and frontend services |
| `make stop-backend` | Stop the backend server |
| `make stop-frontend` | Stop the frontend server |

### Installation

| Command | Description |
|---------|-------------|
| `make install-backend` | Install/update Python dependencies for backend |
| `make install-backend PIP_INDEX_URL=<url>` | Install backend dependencies using custom pip index (Artifactory/mirror) |
| `make install-frontend` | Install/update npm dependencies for frontend |
| `make install-frontend NPM_REGISTRY=<url>` | Install frontend dependencies using custom npm registry (Artifactory/mirror) |

### Database Migrations

| Command | Description |
|---------|-------------|
| `make create-schema` | Create DCIM schema/user (runs as system user) |
| `make migrate` or `make migrate-up` | Run all pending migrations (upgrade to head) |
| `make migrate-down` | Rollback the last migration |
| `make migrate-current` | Show current database migration version |
| `make migrate-history` | Show complete migration history |
| `make migrate-create MESSAGE='description'` | Create a new migration file |
| `make cleanup-tables` | Cleanup partial tables from failed migrations |

**Note:** Migration commands use default connection `dcim:dcim123@localhost:1521` if `DB_URL` not set.

### Data Seeding

| Command | Description |
|---------|-------------|
| `make seed-data` | Seed database with sample data |
| `make clear-seed` | Clear all seeded data from database |

### Utilities

| Command | Description |
|---------|-------------|
| `make clean` | Clean temporary files, logs, and Python cache |
| `make help` | Display all available Makefile commands |

### Oracle Docker Commands

| Command | Description |
|---------|-------------|
| `make oracle-setup` | Set up Oracle XE Docker instance (first time) |
| `make oracle-up` | Start Oracle Docker container |
| `make oracle-down` | Stop Oracle Docker container |
| `make oracle-logs` | View Oracle container logs |
| `make oracle-shell` | Enter Oracle container shell |
| `make oracle-status` | Show Oracle container status |
| `make oracle-remove` | Remove Oracle container and volume |

## Running Services

### Backend (FastAPI)

The backend API runs on **http://localhost:8000**

- **API Documentation (Swagger)**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

```bash
make backend
```

#### Manual backend startup (without Makefile)

If you want to run the backend manually inside `dcim_backend_fastapi/app`, you can reuse the same steps we use locally:

```bash
# (optional) verify nothing else is bound to port 8000
lsof -i :8000

# stop any leftover uvicorn processes
pkill -9 -f uvicorn

# install dependencies
pip install -r requirements.txt

# start FastAPI with hot reload
uvicorn app.main:app --reload
```

### Frontend (Angular)

The frontend application runs on **http://localhost:4200**

```bash
make frontend
```

### Both Services

To start both services simultaneously:

```bash
make run-all
```

This will open separate terminal windows for each service (if terminal emulator is available), or run them in the background.

### Nginx (Reverse Proxy for Local Development)

Run nginx as a reverse proxy for local development. This is useful when you want to serve the frontend and proxy API requests through nginx, similar to production setup:

**Prerequisites:**
1. Install nginx: `make nginx-install`
2. Build the frontend: `cd dcim_frontend && npm run build`
3. Ensure backend is running: `make backend` (in a separate terminal)

**Start nginx for local development:**
```bash
make nginx-local
```

This will:
- Run nginx on port **8080** (to avoid conflicts with system nginx on port 80)
- Serve frontend from `dcim_frontend/dist`
- Proxy API requests to backend on `localhost:8000`
- **Bypass SSL** (HTTP only for local development)
- Access application at: **http://localhost:8080**

**Stop nginx:**
```bash
make stop-nginx
```

**Other nginx commands:**
- `make nginx-test` - Test nginx configuration
- See `nginx/README.md` for detailed nginx configuration documentation

## Database Migrations

### Prerequisites

Before running migrations, ensure:
1. Oracle database is running and accessible
2. The `dcim` schema/user exists (see [Schema Configuration](#schema-configuration))
3. `DB_URL` environment variable is set (or use default)

**Default connection (if DB_URL not set):**
- Uses: `oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1`

**Custom connection:**
```bash
export DB_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"
```

### Schema Configuration

All tables are created in the `dcim` schema. Create the schema using:

**Using Makefile (Recommended):**
```bash
make create-schema
```

**Or manually using the script:**
```bash
cd dcim_alembic_db_migration
./create_schema_and_migrate.sh
```

**Or via SQL:**
```sql
CREATE USER dcim IDENTIFIED BY dcim123;
GRANT CONNECT, RESOURCE TO dcim;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE TO dcim;
GRANT CREATE PROCEDURE, CREATE TRIGGER, CREATE VIEW TO dcim;
GRANT UNLIMITED TABLESPACE TO dcim;
```

### Generating New Migrations

To create a new migration file for schema changes:

```bash
# Using Makefile (recommended)
make migrate-create MESSAGE="add new column to devices"

# Or using Alembic directly
cd dcim_alembic_db_migration
source venv/bin/activate
alembic revision -m "add new column to devices"
```

This will create a new migration file in `dcim_alembic_db_migration/alembic/versions/` that you can edit.

**Migration File Structure:**
Each migration file follows this pattern:
```python
def _create_table() -> None:
    # Create table definition
    op.create_table(...)

def _update_table() -> None:
    # Placeholder for pre-apply changes
    pass

def upgrade() -> None:
    _create_table()
    _update_table()

def downgrade() -> None:
    # Drop table/indexes
    op.drop_table(...)
```

**Important:** Never edit already-applied migration files. Always create a new migration for schema changes.

### Applying Migrations

Apply all pending migrations to bring the database up to date:

```bash
# Using Makefile (recommended)
make migrate-up

# Or using Alembic directly
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"
alembic upgrade head
```

#### Manual container workflow (seed + alembic)

When running Oracle in Docker (container name `oracle19.3`), you can manually copy and execute the seed script before upgrading with Alembic:

```bash
# copy the seed file into the running Oracle container
docker cp "SEED FILE PATH/seed_dcim.sql" oracle19.3:/tmp/seed_dcim.sql

# open a shell inside the container
docker exec -it oracle19.3 bash

# inside the container, seed using sqlplus
sqlplus DCIM/123456@//localhost:1521/dcim_dev_db @/tmp/seed_dcim.sql

# back on your host (inside dcim_alembic_db_migration), upgrade to head
alembic upgrade head
```

**What happens:**
- All pending migrations are applied in order
- Tables are created in the `dcim` schema
- Migration version is recorded in `alembic_version` table

**Before starting the backend, ensure migrations are up to date:**
```bash
# Set database URL
export DB_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"

# Run migrations
make migrate-up
```

### Checking Migration Status

Check the current migration version and view history:

```bash
# Check current version
make migrate-current

# View complete migration history
make migrate-history

# Or using Alembic directly
cd dcim_alembic_db_migration
source venv/bin/activate
alembic current
alembic history
```

### Rolling Back Migrations

Rollback migrations to undo schema changes:

```bash
# Rollback last migration (one step)
make migrate-down

# Rollback to specific revision
cd dcim_alembic_db_migration
source venv/bin/activate
export DB_URL="oracle+oracledb://user:password@hostname:1521/?service_name=ORCLPDB1"
alembic downgrade -1          # Rollback one migration
alembic downgrade <revision> # Rollback to specific revision
alembic downgrade base        # Rollback all migrations (⚠️ DANGEROUS)
```

**Warning:** Rolling back migrations will drop tables and lose data. Always backup your database before rolling back in production.

### Seeding Sample Data

After running migrations, you can seed the database with sample data:

**Using Makefile (Recommended):**

```bash
# Seed the database with sample data
make seed-data

# To clear all seeded data
make clear-seed
```

**Manual Options:**

*Option 1: Using SQL*Plus or SQL Developer*
```bash
sqlplus dcim/dcim123@localhost:1521/ORCLPDB1
@dcim_alembic_db_migration/db_scripts/seed_dcim.sql
```

*Option 2: Using custom DB_URL*
```bash
export DB_URL="oracle+oracledb://dcim:dcim123@hostname:1521/?service_name=ORCLPDB1"
make seed-data
```

**What gets seeded:**
- Sample users (`dcim_user`)
- Location hierarchy (`dcim_location`, `dcim_building`, `dcim_wing`, `dcim_floor`, `dcim_datacenter`)
- Sample racks (`dcim_rack`) and devices (`dcim_device`)
- Device metadata (`dcim_device_type`, `dcim_manufacturer`, `dcim_module`)
- RBAC system (`dcim_rbac_role`, `dcim_rbac_user_role`, `dcim_menu`, `dcim_sub_menu`, `dcim_rbac_role_sub_menu_access`)
- Audit logs (`dcim_audit_log`), environments (`dcim_environment`)
- Asset owners (`dcim_asset_owner`) and applications (`dcim_applications_mapped`)

**Note:** The seed script uses integer IDs for foreign keys. Make sure migrations are applied before seeding.

**Clearing seeded data:**
```bash
# Using Makefile (recommended)
make clear-seed

# This deletes data from all tables in the correct order (respecting foreign key constraints)
```

## Development

### Backend Development

The backend uses FastAPI with SQLAlchemy for database operations. Key directories:

- `dcim_backend_fastapi/app/` - Main application code
- `dcim_backend_fastapi/app/dcim/` - DCIM-related routers and models
- `dcim_backend_fastapi/app/auth/` - Authentication and authorization
- `dcim_backend_fastapi/app/db/` - Database session and configuration
- `dcim_backend_fastapi/app/core/` - Core utilities (config, logger, middleware)

### Logging System

The backend includes a comprehensive logging system that automatically logs API requests and responses. The logger supports JSON and text formats, with environment-based log levels.

#### Automatic Request/Response Logging

The logging middleware automatically logs all API requests and responses with the following information:

- **Request ID** (UUID) for request tracing
- **HTTP method and path**
- **Query parameters**
- **Request headers** (sensitive headers are redacted)
- **Request body** (for non-file uploads, <10KB)
- **Response status code**
- **Response time** (in milliseconds)
- **User information** (extracted from JWT token or request state)
- **Client IP address**
- **User agent**

#### Configuration

Configure logging via environment variables or `.env` file:

```bash
# Environment (dev, uat, or prod)
export ENVIRONMENT=dev

# Log format (json or text)
export LOG_FORMAT=json

# Optional: Log to file
export LOG_FILE=logs/app.log

# JWT configuration for user extraction
export JWT_SECRET_KEY="your-secret-key"
export JWT_ALGORITHM="HS256"
```

**Log Levels by Environment:**
- **dev/uat**: `DEBUG` - Logs request/response bodies and detailed information
- **prod**: `INFO` - Logs metadata only (no request/response bodies)

#### Using the Logger in New API Endpoints

When creating new API endpoints, you can use the logger for custom logging. **Request ID and request context (method, path) are automatically included in all logs** - you don't need to manually add them!

**1. Import the logger:**

```python
from app.core.logger import app_logger
```

**2. Basic logging examples:**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.logger import app_logger
from app.dcim.deps import get_db

router = APIRouter(prefix="/api/example", tags=["example"])

@router.get("/items/{item_id}")
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    # Info level logging
    # Note: request_id, method, and path are automatically included!
    app_logger.info(
        "Fetching item",
        extra={
            "item_id": item_id,
            "operation": "get_item"
        }
    )
    
    try:
        # Your business logic here
        item = db.query(Item).filter(Item.id == item_id).first()
        
        if not item:
            # Warning level logging
            app_logger.warning(
                "Item not found",
                extra={
                    "item_id": item_id,
                    "operation": "get_item"
                }
            )
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Success logging
        app_logger.info(
            "Item retrieved successfully",
            extra={
                "item_id": item_id,
                "operation": "get_item"
            }
        )
        
        return item
        
    except Exception as e:
        # Error level logging with exception details
        # request_id is automatically included from context
        app_logger.error(
            "Error fetching item",
            extra={
                "item_id": item_id,
                "operation": "get_item",
                "error": str(e)
            },
            exc_info=True  # Includes full stack trace
        )
        raise
```

**3. Automatic Request Context:**

The logger automatically includes the following in all log entries:
- **request_id** - Unique UUID for the request (set by middleware)
- **method** - HTTP method (GET, POST, etc.)
- **path** - Request path

You don't need to manually add these - they're included automatically! For example:

```python
@router.post("/items")
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
):
    # This log will automatically include:
    # - request_id (from middleware)
    # - method="POST"
    # - path="/api/example/items"
    app_logger.info(
        "Creating new item",
        extra={
            "operation": "create_item",
            "item_name": payload.name
        }
    )
    
    # Your business logic here
    item = Item(**payload.dict())
    db.add(item)
    db.commit()
    
    app_logger.info(
        "Item created successfully",
        extra={
            "operation": "create_item",
            "item_id": item.id
        }
    )
    
    return item
```

**4. Log levels:**

```python
# Debug - Detailed information (only in dev/uat)
app_logger.debug("Detailed debug information", extra={"key": "value"})

# Info - General informational messages
app_logger.info("Operation completed", extra={"key": "value"})

# Warning - Warning messages
app_logger.warning("Potential issue detected", extra={"key": "value"})

# Error - Error messages (includes stack trace with exc_info=True)
app_logger.error("Error occurred", extra={"key": "value"}, exc_info=True)

# Critical - Critical errors
app_logger.critical("Critical system error", extra={"key": "value"}, exc_info=True)
```

**5. Best practices:**

- **Use structured logging**: Always use the `extra` parameter to add structured data
- **Include context**: Add relevant context like `operation`, `user_id`, `resource_id`, etc.
- **Request context is automatic**: You don't need to manually add `request_id`, `method`, or `path` - they're included automatically
- **Use appropriate log levels**: 
  - `DEBUG` for detailed debugging (dev/uat only)
  - `INFO` for normal operations
  - `WARNING` for potential issues
  - `ERROR` for errors that need attention
  - `CRITICAL` for system-critical errors
- **Log exceptions**: Use `exc_info=True` when logging exceptions to include stack traces

**6. Example: Complete endpoint with logging:**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.logger import app_logger
from app.dcim.deps import get_db
from app.dcim import models, schemas

router = APIRouter(prefix="/api/example", tags=["example"])

@router.post("/items", response_model=schemas.ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    request: Request,
    payload: schemas.ItemCreate,
    db: Session = Depends(get_db),
):
    # Note: request_id, method, and path are automatically included in all logs!
    app_logger.info(
        "Creating new item",
        extra={
            "operation": "create_item",
            "item_name": payload.name,
            "user_id": getattr(request.state, "user_id", None)  # From JWT or auth
        }
    )
    
    try:
        # Check for duplicates
        existing = db.query(models.Item).filter(models.Item.name == payload.name).first()
        if existing:
            app_logger.warning(
                "Item with name already exists",
                extra={
                    "operation": "create_item",
                    "item_name": payload.name,
                    "existing_item_id": existing.id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item with this name already exists"
            )
        
        # Create item
        item = models.Item(**payload.dict())
        db.add(item)
        db.commit()
        db.refresh(item)
        
        app_logger.info(
            "Item created successfully",
            extra={
                "operation": "create_item",
                "item_id": item.id,
                "item_name": item.name
            }
        )
        
        return item
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # request_id is automatically included from context
        app_logger.error(
            "Error creating item",
            extra={
                "operation": "create_item",
                "item_name": payload.name,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )
```

#### Log Output Examples

**JSON Format (default):**
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "dcim_backend",
  "environment": "dev",
  "message": "API Request",
  "request_id": "abc-123-def-456",
  "method": "POST",
  "path": "/api/dcim/sites",
  "user": {
    "user_id": 123,
    "username": "john.doe"
  },
  "client_ip": "192.168.1.100",
  "status_code": 201,
  "process_time_ms": 45.23
}
```

**Text Format:**
```
[2024-01-15 10:30:45] [INFO] [dcim_backend] [dev] API Request request_id=abc-123 method=POST path=/api/dcim/sites user_id=123
```

#### Notes

- **Automatic logging**: All API requests/responses are automatically logged by the middleware
- **Automatic request context**: `request_id`, `method`, and `path` are automatically included in ALL log entries (no need to add them manually)
- **Sensitive data**: Authorization headers, cookies, and other sensitive headers are automatically redacted
- **Performance**: Logging is non-blocking and designed for production use
- **Request ID**: Every request gets a unique UUID that's included in response headers as `X-Request-ID` and automatically in all logs
- **User extraction**: User information is automatically extracted from JWT tokens in the `Authorization: Bearer <token>` header
- **Context variables**: The logger uses Python's `contextvars` for thread-safe async request context tracking

### Frontend Development

The frontend is built with Angular. Key directories:

- `dcim_frontend/src/app/` - Angular application code
- `dcim_frontend/src/environments/` - Environment configuration

### Database Schema

Database migrations are managed using Alembic in the `dcim_alembic_db_migration/` directory. Each migration file creates or modifies database tables.

**Current Tables (21 tables):**

| Category | Tables |
|----------|--------|
| **Authentication** | `dcim_user`, `dcim_user_token` |
| **Location Hierarchy** | `dcim_location`, `dcim_building`, `dcim_wing`, `dcim_floor`, `dcim_datacenter`, `dcim_rack` |
| **Device Management** | `dcim_device`, `dcim_device_type`, `dcim_manufacturer`, `dcim_module` |
| **Assets** | `dcim_asset_owner`, `dcim_applications_mapped`, `dcim_environment` |
| **RBAC** | `dcim_rbac_role`, `dcim_rbac_user_role`, `dcim_menu`, `dcim_sub_menu`, `dcim_rbac_role_sub_menu_access` |
| **Auditing** | `dcim_audit_log` |

**Key Schema Design:**
- All tables use **integer IDs as primary keys** (not string names)
- The `name` column is unique and non-null for human-readable identification
- All foreign key relationships use integer IDs for referential integrity
- Tables are prefixed with `dcim_` and created in the `dcim` schema

## Environment Variables

### Backend

The backend reads configuration from environment variables or a `.env` file:

- `DATABASE_URL` - Oracle database connection string (required)

### Migrations

- `DB_URL` - Oracle database connection string (optional, defaults to dcim user on localhost)

**Default (if DB_URL not set):**
```bash
# Uses: oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1
make migrate-up
```

**Custom connection:**
```bash
export DB_URL="oracle+oracledb://dcim:dcim123@oracledb-host:1521/?service_name=ORCLPDB1"
make migrate-up
```

**Note:** All tables are created in the `dcim` schema. The `dcim` user must exist and have appropriate privileges.

### Custom Package Repositories

You can configure custom Artifactory or package repositories using environment variables:

**Python (pip):**
- `PIP_INDEX_URL` - Custom pip package index URL (optional)
  ```bash
  export PIP_INDEX_URL="https://artifactory.company.com/api/pypi/pypi/simple"
  ```

**Node.js (npm):**
- `NPM_REGISTRY` - Custom npm registry URL (optional)
  ```bash
  export NPM_REGISTRY="https://artifactory.company.com/api/npm/npm/"
  ```

**Using with Artifactory Authentication:**

For authenticated Artifactory access, you can use:

1. **pip authentication** - Create `~/.pip/pip.conf` or use `.netrc`:
   ```ini
   [global]
   index-url = https://username:password@artifactory.company.com/api/pypi/pypi/simple
   ```

2. **npm authentication** - Use `.npmrc` file:
   ```ini
   registry=https://artifactory.company.com/api/npm/npm/
   //artifactory.company.com/api/npm/npm/:_authToken=YOUR_TOKEN
   ```

3. **Or pass via Makefile:**
   ```bash
   make install-backend PIP_INDEX_URL="https://username:password@artifactory.company.com/api/pypi/pypi/simple"
   make install-frontend NPM_REGISTRY="https://artifactory.company.com/api/npm/npm/"
   ```

## Troubleshooting

### Services won't start

1. Check if ports 8000 (backend) or 4200 (frontend) are already in use:
   ```bash
   ss -tuln | grep -E ":(8000|4200)"
   ```

2. Ensure dependencies are installed:
   ```bash
   make install-backend
   make install-frontend
   ```

### Migration errors

1. Verify `DB_URL` is set correctly:
   ```bash
   echo $DB_URL
   ```

2. Check database connectivity and credentials

3. Review migration history:
   ```bash
   make migrate-history
   ```

4. If migrations failed partially, cleanup and retry:
   ```bash
   # Clean up partial tables from failed migrations
   make cleanup-tables
   
   # Then retry migrations
   make migrate-up
   ```

### Artifactory/Repository Issues

If you're using custom Artifactory or package repositories:

1. **Verify repository URLs are accessible:**
   ```bash
   # Test pip repository
   curl -I https://artifactory.company.com/api/pypi/pypi/simple
   
   # Test npm registry
   npm ping --registry https://artifactory.company.com/api/npm/npm/
   ```

2. **Check authentication:**
   - For pip: Verify `~/.pip/pip.conf` or `.netrc` has correct credentials
   - For npm: Verify `~/.npmrc` or project `.npmrc` has correct auth token

3. **Test installation with verbose output:**
   ```bash
   # Python packages
   make install-backend PIP_INDEX_URL=<your-url> 2>&1 | tail -20
   
   # Node packages
   make install-frontend NPM_REGISTRY=<your-url> 2>&1 | tail -20
   ```

4. **Common Artifactory URL formats:**
   - **PyPI (pip):** `https://artifactory.company.com/api/pypi/pypi/simple`
   - **npm:** `https://artifactory.company.com/api/npm/npm/`
   - Ensure URLs end with `/simple` for pip and `/` for npm

5. **If packages are not found:**
   - Verify the Artifactory repository is configured to proxy/cache the upstream repositories
   - Check if the package exists in your Artifactory instance
   - Try using the upstream repository directly to verify the package exists

### Clean installation

To start fresh:

```bash
# Clean temporary files
make clean

# Reinstall dependencies
make install-backend
make install-frontend
```

## API Endpoints

### DCIM Endpoints

All DCIM endpoints are prefixed with `/api/dcim`:

- `/api/dcim/sites` - Site management
- `/api/dcim/locations` - Location management
- `/api/dcim/racks` - Rack management
- `/api/dcim/devices` - Device management

### Authentication

- `/api/dcim/login` - User login, returns a JWT `access_token` and opaque `refresh_token`
- `/api/dcim/logout` - Logout, invalidates all refresh tokens for the current user
- `/api/dcim/refresh` - Use a valid refresh token (in `Authorization: Bearer <refresh_token>`) to obtain a new JWT access token and refresh token pair

#### Login and Token Flow

1. **Login (Frontend → Backend)**  
   - Angular frontend calls `POST /api/dcim/login` with body:  
     ```json
     {
       "username": "admin",
       "password": "<bcrypt-hashed password>"
     }
     ```  
   - Backend validates the user and responds with:
     ```json
     {
       "access_token": "<JWT access token>",
       "refresh_token": "<opaque refresh token>",
       "user": { "...user fields..." },
       "menuList": [ /* RBAC-driven menu items */ ],
       "configure": {
         "is_editable": true,
         "is_deletable": false,
         "is_viewer": true
       }
     }
     ```
   - The frontend stores `access_token` and `refresh_token` in `localStorage` (via `AuthService.saveTokens`) along with `user`, `configure`, and `menu`.

2. **Access Token (JWT)**
   - The access token is a JWT signed with `JWT_SECRET_KEY` and `JWT_ALGORITHM` from backend config.
   - Claims include:
     - `sub` (user id), `username`, `email`
     - `roles` (active role codes, e.g. `["ADMIN", "EDITOR"]`)
     - `is_active`
     - `iat` / `exp` based on `ACCESS_TOKEN_EXPIRE_SECONDS`
   - Angular `AuthInterceptor` automatically adds `Authorization: Bearer <access_token>` to all protected API requests.

3. **Refresh Token**
   - A single refresh token per user is stored in the `dcim_user_token` table with:
     - `token_key` (opaque string), `user_id`, `expires`, `token_type="refresh"`.
   - Expiry is controlled via `REFRESH_TOKEN_EXPIRE_SECONDS` in backend config.

4. **Token Refresh (on 401 / expiry)**
   - When the backend returns **401 Unauthorized** for an API call, the Angular `AuthInterceptor`:
     - Checks if a `refresh_token` exists in `localStorage`.
     - Calls `POST /api/dcim/refresh` with header:  
       `Authorization: Bearer <refresh_token>`
   - Backend validates the refresh token from the DB and returns a new pair:
     ```json
     {
       "access_token": "<new JWT access token>",
       "refresh_token": "<new opaque refresh token>",
       "user": { "...user fields..." },
       "menuList": [ ... ],
       "configure": { ... }
     }
     ```
   - Frontend updates stored tokens via `AuthService.saveTokens` and retries the original request with the new access token.

5. **Logout**
   - Frontend clears tokens and user data from `localStorage` and navigates to `/login`.
   - Backend `POST /api/dcim/logout` (called with the current JWT access token) removes all refresh tokens for the user from `dcim_user_token`, effectively logging out from all sessions.

#### Auth-Related Configuration (Backend)

Configure these values via environment variables or `.env` files:

```bash
export JWT_SECRET_KEY="your-secret-key-change-in-production"
export JWT_ALGORITHM="HS256"

# Token expiration (seconds)
export ACCESS_TOKEN_EXPIRE_SECONDS=3600      # 1 hour access token
export REFRESH_TOKEN_EXPIRE_SECONDS=86400    # 1 day refresh token
```

These are exposed via `app/core/config.py` and used by the auth helper when creating and validating tokens.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
