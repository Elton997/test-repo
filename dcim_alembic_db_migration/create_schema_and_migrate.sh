#!/bin/bash

# Script to create DCIM schema and apply migrations
# Usage: ./create_schema_and_migrate.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database connection details (default for Oracle XE)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-1521}"
DB_SERVICE="${DB_SERVICE:-ORCLPDB1}"
DB_SYSTEM_USER="${DB_SYSTEM_USER:-system}"
DB_SYSTEM_PASSWORD="${DB_SYSTEM_PASSWORD:-Oracle123}"
DCIM_USER="${DCIM_USER:-dcim}"
DCIM_PASSWORD="${DCIM_PASSWORD:-dcim123}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  DCIM Schema Creation & Migration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if DB_URL is set, if not construct it
if [ -z "$DB_URL" ]; then
    echo -e "${YELLOW}DB_URL not set, constructing from environment variables...${NC}"
    DB_URL="oracle+oracledb://${DB_SYSTEM_USER}:${DB_SYSTEM_PASSWORD}@${DB_HOST}:${DB_PORT}/?service_name=${DB_SERVICE}"
    export DB_URL
    echo -e "${GREEN}Using DB_URL: oracle+oracledb://${DB_SYSTEM_USER}:***@${DB_HOST}:${DB_PORT}/?service_name=${DB_SERVICE}${NC}"
else
    echo -e "${GREEN}Using provided DB_URL${NC}"
fi

# Step 1: Create the schema using Python (more reliable than sqlplus)
echo ""
echo -e "${YELLOW}Step 1: Creating DCIM schema...${NC}"

python3 << PYTHON_SCRIPT
import oracledb
import sys
import os

try:
    # Parse connection details from DB_URL or use defaults
    db_url = os.getenv('DB_URL', '')
    
    if not db_url:
        print("Error: DB_URL not set")
        sys.exit(1)
    
    # Extract connection details (simple parsing)
    # Format: oracle+oracledb://user:password@host:port/?service_name=SERVICE
    import re
    match = re.search(r'oracle\+oracledb://([^:]+):([^@]+)@([^:]+):(\d+)/\?service_name=([^&]+)', db_url)
    
    if not match:
        print("Error: Could not parse DB_URL")
        sys.exit(1)
    
    user, password, host, port, service = match.groups()
    
    # Connect as SYSTEM user to create schema
    print(f"Connecting to {host}:{port}/{service} as {user}...")
    connection = oracledb.connect(
        user=user,
        password=password,
        host=host,
        port=int(port),
        service_name=service
    )
    
    cursor = connection.cursor()
    
    # Check if dcim user already exists
    cursor.execute("""
        SELECT COUNT(*) FROM dba_users WHERE username = 'DCIM'
    """)
    user_exists = cursor.fetchone()[0] > 0
    
    if user_exists:
        print("DCIM user already exists. Skipping creation.")
        # Grant privileges in case they're missing
        dcim_user = os.getenv('DCIM_USER', 'dcim')
        try:
            cursor.execute(f"GRANT CONNECT, RESOURCE TO {dcim_user}")
            cursor.execute(f"GRANT CREATE SESSION TO {dcim_user}")
            cursor.execute(f"GRANT CREATE TABLE TO {dcim_user}")
            cursor.execute(f"GRANT CREATE SEQUENCE TO {dcim_user}")
            cursor.execute(f"GRANT UNLIMITED TABLESPACE TO {dcim_user}")
            connection.commit()
            print("Privileges granted to existing DCIM user.")
        except Exception as e:
            print(f"Note: {e}")
    else:
        # Create the DCIM user
        dcim_user = os.getenv('DCIM_USER', 'dcim')
        dcim_password = os.getenv('DCIM_PASSWORD', 'dcim123')
        print(f"Creating DCIM user with password: {dcim_password}...")
        cursor.execute(f"""
            CREATE USER {dcim_user} IDENTIFIED BY {dcim_password}
        """)
        
        # Grant privileges
        cursor.execute(f"GRANT CONNECT, RESOURCE TO {dcim_user}")
        cursor.execute(f"GRANT CREATE SESSION TO {dcim_user}")
        cursor.execute(f"GRANT CREATE TABLE TO {dcim_user}")
        cursor.execute(f"GRANT CREATE SEQUENCE TO {dcim_user}")
        cursor.execute(f"GRANT CREATE PROCEDURE TO {dcim_user}")
        cursor.execute(f"GRANT CREATE TRIGGER TO {dcim_user}")
        cursor.execute(f"GRANT CREATE VIEW TO {dcim_user}")
        cursor.execute(f"GRANT UNLIMITED TABLESPACE TO {dcim_user}")
        
        connection.commit()
        print("DCIM user created successfully!")
    
    # Verify
    cursor.execute("""
        SELECT username, account_status, default_tablespace 
        FROM dba_users 
        WHERE username = 'DCIM'
    """)
    result = cursor.fetchone()
    if result:
        print(f"Verified: User {result[0]}, Status: {result[1]}, Tablespace: {result[2]}")
    
    cursor.close()
    connection.close()
    print("Schema creation completed successfully!")
    
except Exception as e:
    print(f"Error creating schema: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create schema${NC}"
    exit 1
fi

# Step 2: Run migrations
echo ""
echo -e "${YELLOW}Step 2: Running database migrations...${NC}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run migrations
alembic upgrade head

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Migration completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Schema:${NC} dcim"
    echo -e "${BLUE}Connection:${NC} oracle+oracledb://${DCIM_USER}:${DCIM_PASSWORD}@${DB_HOST}:${DB_PORT}/?service_name=${DB_SERVICE}"
else
    echo -e "${RED}Migration failed${NC}"
    exit 1
fi

