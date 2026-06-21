


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
TRUNCATE TABLE analytics.drivers;
CREATE TABLE IF NOT EXISTS analytics.drivers (
    driver_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    vehicle_type VARCHAR NOT NULL,
    plate VARCHAR NOT NULL,
    rating FLOAT DEFAULT 4.5,
    total_trips INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'offline',  -- ✅ Default: not available
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Data analyst to define which aren't Completed Trip
SELECT booking_status, completed_at, vehicle_arrival_at
FROM analytics.trip
WHERE booking_status != 'Completed';

-- Update changing name on postgres
UPDATE analytics.trip
SET
    ride_type = 'Alphard'
WHERE
    ride_type = 'Auto';

UPDATE analytics.trip
SET
    ride_type = 'HRV'
WHERE
    ride_type = 'Car';

UPDATE analytics.trip
SET
    ride_type = 'Innova'
WHERE
    ride_type = 'Motorcycle';

UPDATE analytics.trip
SET
    ride_type = 'Brio'
WHERE
    ride_type = 'eBike';

UPDATE analytics.trip
SET
    ride_type = 'Terios'
WHERE
    ride_type = 'Uber XL';

-- Backfill ML features for existing trips
-- This computes values from existing data

-- 1. Backfill vtat_minutes and ctat_minutes
UPDATE analytics.trip
SET
    ctat_minutes = duration_minutes,
    vtat_minutes = EXTRACT(EPOCH FROM (vehicle_arrival_at - created_at)) / 60
WHERE vehicle_arrival_at IS NOT NULL
    AND duration_minutes IS NOT NULL
    AND vtat_minutes IS NULL;

-- 2. For trips without vehicle_arrival_at, estimate VTAT as 30% of CTAT
UPDATE analytics.trip
SET
    ctat_minutes = duration_minutes,
    vtat_minutes = duration_minutes * 0.3
WHERE vehicle_arrival_at IS NULL
    AND duration_minutes IS NOT NULL
    AND vtat_minutes IS NULL;

-- 3. Backfill pickup_encoded, drop_encoded, route_cluster
-- Using hash-based encoding (consistent with your ML pipeline)
UPDATE analytics.trip 
SET 
    pickup_encoded = ABS(hashtext(COALESCE(pickup_location, ''))) % 1000,
    drop_encoded = ABS(hashtext(COALESCE(dropoff_location, ''))) % 1000,
    route_cluster = ABS(hashtext(COALESCE(pickup_location, '') || '|' || COALESCE(dropoff_location, ''))) % 100
WHERE pickup_encoded IS NULL;

SELECT booking_status, pickup_location, dropoff_location, ride_type, driver_status, driver_rating FROM analytics.trip
WHERE booking_status = 'Pending';

SELECT pickup_location, dropoff_location FROM analytics.trip LIMIT 65;

-- SQL database scaling
DROP TABLE analytics.data_retrieves;
CREATE TABLE IF NOT EXISTS analytics.data_retrieves (
	ride_id VARCHAR PRIMARY KEY,
	driver_id VARCHAR,
	vehicle_type VARCHAR,
	drop_location VARCHAR,
	pickup_location VARCHAR,
	price_per_ride DOUBLE PRECISION,
	booking_status VARCHAR,
	driver_rating DOUBLE PRECISION
);

-- insert to analytics.data_retrieves DB
INSERT INTO analytics.data_retrieves (
	ride_id,
    driver_id, 
    vehicle_type, 
    drop_location, 
    pickup_location, 
    price_per_ride, 
    booking_status, 
    driver_rating
)
SELECT DISTINCT ON (t.ride_id) -- Ensure each ride_id is only processed ONCE
	t.ride_id,
    d.driver_id,
    d.vehicle_type,
    t.dropoff_location,
    t.pickup_location,
    t.actual_fare,
    t.booking_status,
    t.driver_rating
FROM 
    analytics.trip t
JOIN
	analytics.drivers d ON LOWER(t.driver_status) = d.status;
	-- Note: This matches 'online' from drivers with 'Online' from trips

-- Inner join to fetch botch database are inserting driver_name
SELECT
	dr.driver_id,
	d.name AS driver_name, -- join driver name from drivers DB
	dr.vehicle_type,
	dr.pickup_location,
	dr.drop_location,
	dr.price_per_ride,
	dr.booking_status,
	dr.driver_rating
FROM
	analytics.drivers d
JOIN
	analytics.data_retrieves dr ON d.driver_id = dr.driver_id;
	-- Note: data_retieves define as dr to join dr on d as driver

-- select data
SELECT * FROM analytics.data_retrieves;

------------------------------------------------------------
-- Select data
SELECT * FROM analytics.trip;

SELECT * FROM analytics.drivers;

SELECT * FROM analytics.llm_interactions;

SELECT * FROM analytics.taxi_trip_data_events;

SELECT pickup_location, dropoff_location, booking_status, ride_id, rider_id, ride_type
FROM analytics.trip
WHERE pickup_location = 'Rawasari' AND dropoff_location = 'Kembangan Utara';

-- Find database
SELECT
	pickup_location, dropoff_location, ride_type, hour, day_of_week, distance_km,
COUNT(*) as trip_count,
	ROUND(AVG(actual_fare)::numeric, 0) as avg_fare,
	ROUND(AVG(duration_minutes)::numeric, 1) as avg_duration
FROM analytics.trip
WHERE ride_id IS NOT NULL
	AND pickup_location = 'Fatmawati'
	AND dropoff_location = 'Rorotan'
	AND ride_type = 'Alphard'
GROUP BY pickup_location, dropoff_location, ride_type, hour, day_of_week, distance_km
ORDER BY trip_count DESC;