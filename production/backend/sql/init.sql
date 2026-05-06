-- Active: 1770487880142@@127.0.0.1@5432
-- Active: 1770487880142@@127.0.0.1@5432@localhost@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432@127.0.0.1@5432
-- Create the rides table
CREATE TABLE IF NOT EXISTS rides (
    id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    pickup_location TEXT NOT NULL,
    drop_location TEXT NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    estimated_time_min DOUBLE PRECISION NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Index for history performance
CREATE INDEX IF NOT EXISTS idx_user_rides ON rides(user_id);

-- seed data from parquet for example row
INSERT INTO rides (
    id, user_id, pickup_location, drop_location, 
    vehicle_type, price, estimated_time_min, status, created_at
) VALUES (
    'RIDE-000001',
    'CNR4352144',
    'Pasar Baru',
    'Cilandak Timur',
    'Motorcycle',
    2599.789916	,
    18.90,
    'Completed',
    '2024-01-01 00:19:34'
) ON CONFLICT (id) DO NOTHING;