-- Database initialization script for production

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone TO 'UTC';

-- Create additional database user privileges if needed
-- ALTER USER cookbook_user CREATEDB;