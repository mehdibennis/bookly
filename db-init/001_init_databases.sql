-- Create separate databases for app and keycloak
-- Use IF NOT EXISTS to avoid errors if databases already exist
SELECT 'CREATE DATABASE bookly_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bookly_db')\gexec

SELECT 'CREATE DATABASE keycloak_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\gexec
