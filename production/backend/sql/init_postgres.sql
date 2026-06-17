-- Active: 1781591252887@@localhost@5433@taxi_db
-- DuckDB Analytics Schema (Local Tables)
-- PostgreSQL schema for analytics
CREATE SCHEMA IF NOT EXISTS analytics;

-- ================================================================
-- Table 1: Kafka events from frontend/rides
-- ================================================================
CREATE TABLE IF NOT EXISTS analytics.taxi_trip_data_events (
    event_id VARCHAR PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    user_id VARCHAR,
    topic VARCHAR NOT NULL,
    event_data JSON,
    event_timestamp DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- Table 2: Rides analytics copy
-- ================================================================

-- -- Extend analytics shema
ALTER TABLE analytics.trip ADD COLUMN driver_rating DOUBLE PRECISION;
-- included driver_rating column
ALTER TABLE analytics.trip ADD COLUMN booking_status VARCHAR;
-- included booking_status column

ALTER TABLE analytics.trip ADD COLUMN driver_status VARCHAR;
-- included driver_status column
ALTER TABLE analytics.trip DROP COLUMN driver_id;
-- drop existing driver_id column

-- add table column for day_of_week, demand_pressure, hour
ALTER TABLE analytics.trip ADD COLUMN day_of_week INTEGER;

ALTER TABLE analytics.trip
ADD COLUMN demand_pressure DOUBLE PRECISION;

ALTER TABLE analytics.trip ADD COLUMN hour INTEGER;

CREATE TABLE IF NOT EXISTS analytics.trip (
    ride_id VARCHAR PRIMARY KEY,
    rider_id VARCHAR NOT NULL,
    driver_status VARCHAR,
    pickup_location VARCHAR,
    dropoff_location VARCHAR,
    pickup_lat DOUBLE PRECISION,
    pickup_lng DOUBLE PRECISION,
    dropoff_lat DOUBLE PRECISION,
    dropoff_lng DOUBLE PRECISION,
    status VARCHAR,
    ride_type VARCHAR,
    estimated_fare DOUBLE PRECISION,
    actual_fare DOUBLE PRECISION,
    distance_km DOUBLE PRECISION,
    duration_minutes DOUBLE PRECISION,
    driver_rating DOUBLE PRECISION,
    booking_status VARCHAR,
    day_of_week INTEGER,
    demand_pressure DOUBLE PRECISION,
    hour INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vehicle_arrival_at TIMESTAMP,
    completed_at VARCHAR -- being set to the string 'No Trips' for all booking statuses except Completed
);

-- Backfill from status column if already loaded
UPDATE analytics.trip
SET
    booking_status = status
WHERE
    booking_status IS NULL
    AND status IS NOT NULL;

SELECT * FROM analytics.trip;

-- ================================================================
-- Table 3: Driver profiles
-- ================================================================
DROP TABLE IF EXISTS analytics.drivers;

CREATE TABLE IF NOT EXISTS analytics.drivers (
    driver_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    vehicle VARCHAR,
    rating DOUBLE PRECISION,
    status VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vehicle_arrival_at TIMESTAMP,
    completed_at TIMESTAMP
);

SELECT * FROM analytics.drivers;

-- ================================================================
-- Table 4: LLM interactions audit log
-- ================================================================
CREATE TABLE IF NOT EXISTS analytics.llm_interactions (
    interaction_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    session_id VARCHAR,
    prompt TEXT,
    response TEXT,
    response_time_ms INTEGER,
    tokens_used INTEGER,
    cost DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- Create indexes for better query performance
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_events_event_type ON analytics.taxi_trip_data_events (event_type);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON analytics.taxi_trip_data_events (user_id);

CREATE INDEX IF NOT EXISTS idx_trip_rider_id ON analytics.trip (rider_id);

CREATE INDEX IF NOT EXISTS idx_trip_driver_id ON analytics.trip (driver_id);

CREATE INDEX IF NOT EXISTS idx_trip_status ON analytics.trip (status);

CREATE INDEX IF NOT EXISTS idx_drivers_rating ON analytics.drivers (rating);

CREATE INDEX IF NOT EXISTS idx_llm_user_id ON analytics.llm_interactions (user_id);

CREATE INDEX IF NOT EXISTS idx_llm_session_id ON analytics.llm_interactions (session_id);

-- ================================================================
-- Create Database Index for Performance (LLM interactions)
-- ================================================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trip_pickup_location ON analytics.trip USING gin (
    lower(pickup_location) gin_trgm_ops
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trip_dropoff_location ON analytics.trip USING gin (
    lower(dropoff_location) gin_trgm_ops
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trip_status_ride_type ON analytics.trip (status, ride_type);

-- if don't have trigram extension:
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- ================================================================
-- Create analytical views for common queries
-- ================================================================

-- View 1: Rides summary by status
CREATE VIEW analytics.rides_by_status AS
SELECT
    status,
    COUNT(*) as total_rides,
    AVG(distance_km) as avg_distance,
    AVG(actual_fare) as avg_fare,
    MAX(created_at) as latest_ride
FROM analytics.trip
GROUP BY
    status;

-- View 2: Driver performance metrics
CREATE OR REPLACE VIEW analytics.driver_metrics AS
SELECT
    t.rider_id,
    COUNT(t.ride_id) as total_rides,
    AVG(d.rating) as avg_rating,
    SUM(t.actual_fare) as total_earnings
FROM analytics.trip t
    JOIN analytics.drivers d ON t.rider_id = d.driver_id
WHERE
    t.rider_id IS NOT NULL
GROUP BY
    t.rider_id;

-- View 3: Hourly ride trends
CREATE VIEW analytics.hourly_ride_trends AS
SELECT DATE_TRUNC('hour', created_at) as hour, COUNT(*) as ride_count, AVG(actual_fare) as avg_fare
FROM analytics.trip
GROUP BY
    DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;