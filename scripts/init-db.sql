-- Initial database setup for development environment

-- Create test database for running tests
CREATE DATABASE task_management_test_db;

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Grant all privileges on the test database to postgres user
GRANT ALL PRIVILEGES ON DATABASE task_management_test_db TO postgres;
