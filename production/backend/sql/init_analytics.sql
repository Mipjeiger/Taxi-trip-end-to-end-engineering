-- DuckDB Analytics Schema (Local Tables)
-- Kafka consumer will write events here in real-time

-- ================================================================
-- Table 1: Kafka events from frontend/rides
-- ================================================================
CREATE TABLE IF NOT EXISTS taxi_trip_data_events (
    event_id        VARCHAR PRIMARY KEY,
    event_type      VARCHAR NOT NULL,
    user_id         VARCHAR,
    topic           VARCHAR NOT NULL,
    event_data      JSON,
    event_timestamp DOUBLE PRECISION,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- Table 2: Rides analytics copy
-- ================================================================
CREATE TABLE IF NOT EXISTS trip (
    ride_id          VARCHAR PRIMARY KEY,
    rider_id         VARCHAR NOT NULL,
    driver_id        VARCHAR,
    pickup_location  VARCHAR,
    dropoff_location VARCHAR,
    pickup_lat       DOUBLE PRECISION,
    pickup_lng       DOUBLE PRECISION,
    dropoff_lat      DOUBLE PRECISION,
    dropoff_lng      DOUBLE PRECISION,
    status           VARCHAR,
    ride_type        VARCHAR,
    estimated_fare   DOUBLE PRECISION,
    actual_fare      DOUBLE PRECISION,
    distance_km      DOUBLE PRECISION,
    duration_minutes DOUBLE PRECISION,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at     TIMESTAMP
);

-- ================================================================
-- Table 3: Driver profiles
-- ================================================================
CREATE TABLE IF NOT EXISTS drivers (
    driver_id   VARCHAR PRIMARY KEY,
    name        VARCHAR,
    vehicle     VARCHAR,
    rating      DOUBLE PRECISION,
    status      VARCHAR,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- Table 4: LLM interactions audit log
-- ================================================================
CREATE TABLE IF NOT EXISTS llm_interactions (
    interaction_id   VARCHAR PRIMARY KEY,
    user_id          VARCHAR,
    session_id       VARCHAR,
    prompt           TEXT,
    response         TEXT,
    response_time_ms INTEGER,
    tokens_used      INTEGER,
    cost             DOUBLE PRECISION,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- Create indexes for better query performance
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_events_event_type  ON taxi_trip_data_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_user_id     ON taxi_trip_data_events(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_rider_id      ON trip(rider_id);
CREATE INDEX IF NOT EXISTS idx_trip_driver_id     ON trip(driver_id);
CREATE INDEX IF NOT EXISTS idx_trip_status        ON trip(status);
CREATE INDEX IF NOT EXISTS idx_drivers_rating     ON drivers(rating);
CREATE INDEX IF NOT EXISTS idx_llm_user_id        ON llm_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_session_id     ON llm_interactions(session_id);

-- ================================================================
-- Create analytical views for common queries
-- ================================================================

-- View 1: Rides summary by status
CREATE VIEW IF NOT EXISTS rides_by_status AS
SELECT 
    status,
    COUNT(*) as total_rides,
    AVG(distance_km) as avg_distance,
    AVG(actual_fare) as avg_fare,
    MAX(created_at) as latest_ride
FROM trip
GROUP BY status;

-- View 2: Driver performance metrics
CREATE VIEW IF NOT EXISTS driver_metrics AS
SELECT 
    driver_id,
    COUNT(ride_id) as total_rides,
    AVG(rating) as avg_rating,
    SUM(actual_fare) as total_earnings
FROM trip
WHERE driver_id IS NOT NULL
GROUP BY driver_id;

-- View 3: Hourly ride trends
CREATE VIEW IF NOT EXISTS hourly_ride_trends AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as ride_count,
    AVG(actual_fare) as avg_fare
FROM trip
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;