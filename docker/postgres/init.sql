-- Overview: PostgreSQL initialization script for Nimbus local development.
-- Architecture: Creates application and Temporal databases (Section 2, 10)
-- Dependencies: PostgreSQL 16
-- Concepts: Multi-tenancy foundation, Temporal persistence

-- Application database (created by POSTGRES_DB env var as 'nimbus')
-- This script runs against the default database, so we create the Temporal DB here.

-- Temporal Server requires its own databases (main + visibility)
CREATE DATABASE nimbus_temporal;
CREATE DATABASE nimbus_temporal_visibility;

-- Create core schema for system-wide tables
\connect nimbus;
CREATE SCHEMA IF NOT EXISTS nimbus_core;
