-- taxi_trip_data_events: stores all Kafka events
CREATE TABLE IF NOT EXISTS taxi_trip_data_events (
    event_id     UUID      DEFAULT gen_random_uuid() PRIMARY KEY,
    event_type   VARCHAR   NOT NULL,
    user_id      VARCHAR,
    topic        VARCHAR   NOT NULL,
    event_data   JSON,
    event_timestamp DOUBLE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- rides: analytical copy of ride transactions
CREATE TABLE IF NOT EXISTS rides (
    ride_id          VARCHAR PRIMARY KEY,
    rider_id         VARCHAR NOT NULL,
    driver_id        VARCHAR,
    pickup_location  VARCHAR,
    dropoff_location VARCHAR,
    pickup_lat       DOUBLE,
    pickup_lng       DOUBLE,
    dropoff_lat      DOUBLE,
    dropoff_lng      DOUBLE,
    status           VARCHAR,
    ride_type        VARCHAR,
    estimated_fare   DOUBLE,
    actual_fare      DOUBLE,
    distance_km      DOUBLE,
    duration_minutes DOUBLE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at     TIMESTAMP
);

-- drivers: driver profiles and ratings
CREATE TABLE IF NOT EXISTS drivers (
    driver_id   VARCHAR PRIMARY KEY,
    name        VARCHAR,
    vehicle     VARCHAR,
    rating      DOUBLE,
    status      VARCHAR,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- llm_interactions: LLM audit log with embeddings
CREATE TABLE IF NOT EXISTS llm_interactions (
    interaction_id   UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id          VARCHAR,
    session_id       VARCHAR,
    prompt           TEXT,
    response         TEXT,
    response_time_ms INTEGER,
    tokens_used      INTEGER,
    cost             DOUBLE,
    prompt_embedding   DOUBLE[],
    response_embedding DOUBLE[],
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_events_event_type  ON taxi_trip_data_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_user_id     ON taxi_trip_data_events(user_id);
CREATE INDEX IF NOT EXISTS idx_rides_rider_id     ON rides(rider_id);
CREATE INDEX IF NOT EXISTS idx_rides_driver_id    ON rides(driver_id);
CREATE INDEX IF NOT EXISTS idx_rides_status       ON rides(status);
CREATE INDEX IF NOT EXISTS idx_drivers_rating     ON drivers(rating);
CREATE INDEX IF NOT EXISTS idx_llm_user_id        ON llm_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_session_id     ON llm_interactions(session_id);