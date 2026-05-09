-- Active: 1770487880142@@127.0.0.1@5432
-- Active: 1770487880142@@127.0.0.1@5432@localhost@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432

-- Drop table if exists
DROP TABLE IF EXISTS rides;

-- Add the missing ML feature columns to the rides table
ALTER TABLE rides 
ADD COLUMN IF NOT EXISTS pickup_encoded DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS drop_encoded DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS hour INTEGER,
ADD COLUMN IF NOT EXISTS day_of_week INTEGER,
ADD COLUMN IF NOT EXISTS route_cluster INTEGER,
ADD COLUMN IF NOT EXISTS ride_distance DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS is_peak_hour BOOLEAN,
ADD COLUMN IF NOT EXISTS is_weekend BOOLEAN,
ADD COLUMN IF NOT EXISTS is_night BOOLEAN,
ADD COLUMN IF NOT EXISTS hour_sin DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS hour_cos DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS day_sin DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS day_cos DOUBLE PRECISION;

-- Create the rides table
CREATE TABLE IF NOT EXISTS rides (
    id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    pickup_location TEXT NOT NULL,
    drop_location TEXT NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    price DOUBLE PRECISION,
    estimated_pickup_time_minute DOUBLE PRECISION NOT NULL,
    estimated_drop_time_minute DOUBLE PRECISION NOT NULL,
    status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    pickup_encoded INT NOT NULL,
    drop_encoded INT NOT NULL,
    hour INT NOT NULL,
    day_of_week INT NOT NULL,
    route_cluster INT NOT NULL,
    ride_distance DOUBLE PRECISION NOT NULL,
    is_peak_hour INT NOT NULL,
    is_weekend INT NOT NULL,
    is_night INT NOT NULL,
    hour_sin DOUBLE PRECISION NOT NULL,
    hour_cos DOUBLE PRECISION NOT NULL,
    day_sin DOUBLE PRECISION NOT NULL,
    day_cos DOUBLE PRECISION NOT NULL,
    vtat TIMESTAMP WITH TIME ZONE
);

-- Index for history performance
CREATE INDEX IF NOT EXISTS idx_user_rides ON rides(user_id);

-- seed data from parquet for example row
INSERT INTO rides (
    id, user_id, pickup_location, drop_location, 
    vehicle_type, price, estimated_pickup_time_minute, estimated_drop_time_minute, status, created_at, completed_at, pickup_encoded, drop_encoded,
    hour, day_of_week, route_cluster, ride_distance, is_peak_hour, is_weekend, is_night, hour_sin, hour_cos, day_sin, day_cos, vtat
) VALUES (
    'RIDE-000001',
    'CNR4352144',
    'Pasar Baru',
    'Cilandak Timur',
    'Motorcycle',
    null,
    18.90,
    11.55,
    'Completed',
    '2024-01-01 00:19:34',
    NULL,
    110,
    18,
    0,
    0,
    4,
   37.98,
   0,
   0,
   1,
   0.000000,
   1.000000,
   0.0,
   1.0,
   null
) ON CONFLICT (id) DO NOTHING;

SELECT * FROM rides;

