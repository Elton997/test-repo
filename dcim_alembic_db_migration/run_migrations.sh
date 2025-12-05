#!/bin/bash
# Script to clean up partial tables and run migrations

export DB_URL="oracle+oracledb://system:Oracle123@localhost:1521/?service_name=ORCLPDB1"

cd "$(dirname "$0")"
source venv/bin/activate

echo "Cleaning up partial tables..."
python -c "
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DB_URL'))
conn = engine.connect()

tables = ['dcim_rbac_roles', 'dcim_rbac_user_roles', 'dcim_modules', 'dcim_submodules', 'dcim_rbac_role_submodule_access']

for table in tables:
    try:
        conn.execute(text(f'DROP TABLE {table} CASCADE CONSTRAINTS'))
        print(f'Dropped {table}')
    except:
        pass

conn.commit()
print('Cleanup done')
"

echo ""
echo "Running migrations..."
cd ..
make migrate-up

