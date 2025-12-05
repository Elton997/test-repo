#!/usr/bin/env python3
"""Cleanup script to drop partially created tables from failed migrations"""
from sqlalchemy import create_engine, text
import os
import sys

db_url = os.getenv("DB_URL")
if not db_url:
    print("Error: DB_URL environment variable is not set")
    sys.exit(1)

engine = create_engine(db_url)

# Tables that might exist from partial migrations 017-021
partial_tables = [
    'dcim_rbac_roles',
    'dcim_rbac_user_roles', 
    'dcim_menu',
    'dcim_sub_menu',
    'dcim_rbac_role_sub_menu_access'
]

with engine.connect() as conn:
    print("Checking for partially created tables...")
    dropped_count = 0
    
    for table in partial_tables:
        try:
            # Check if table exists
            result = conn.execute(text(f"""
                SELECT COUNT(*) 
                FROM user_tables 
                WHERE table_name = UPPER('{table}')
            """))
            exists = result.scalar() > 0
            
            if exists:
                conn.execute(text(f"DROP TABLE {table} CASCADE CONSTRAINTS"))
                print(f"  ✓ Dropped {table}")
                dropped_count += 1
            else:
                print(f"  - {table} does not exist (skipping)")
        except Exception as e:
            print(f"  ✗ Error with {table}: {e}")
    
    conn.commit()
    
    if dropped_count > 0:
        print(f"\n✓ Cleanup complete! Dropped {dropped_count} table(s)")
    else:
        print("\n✓ No partial tables found to clean up")

