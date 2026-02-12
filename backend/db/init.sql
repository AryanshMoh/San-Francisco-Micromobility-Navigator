-- Initialize PostGIS extension and set up base schema
-- This runs automatically when the PostgreSQL container starts

-- Enable PostGIS extension for geospatial queries
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions (the main user is created by Docker env vars)
-- These ensure the application user has proper access

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized with PostGIS extensions';
END $$;
