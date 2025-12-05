-- Create DCIM Schema and User
-- This script creates the dcim user/schema with necessary privileges

-- Connect as SYSTEM user to create the schema
-- Note: Run this script as SYSTEM user or a user with DBA privileges

-- Create the DCIM user (schema)
CREATE USER dcim IDENTIFIED BY dcim123;

-- Grant necessary privileges
GRANT CONNECT, RESOURCE TO dcim;

-- Grant additional privileges for table creation and management
GRANT CREATE SESSION TO dcim;
GRANT CREATE TABLE TO dcim;
GRANT CREATE SEQUENCE TO dcim;
GRANT CREATE PROCEDURE TO dcim;
GRANT CREATE TRIGGER TO dcim;
GRANT CREATE VIEW TO dcim;
GRANT UNLIMITED TABLESPACE TO dcim;

-- Allow the user to create objects in their own schema
-- (This is implicit but stated for clarity)

-- Verify the user was created
SELECT username, account_status, default_tablespace 
FROM dba_users 
WHERE username = 'DCIM';

-- Exit
EXIT;

