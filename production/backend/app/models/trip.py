from sqlalchemy import Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trip(Base):
    __tablename__ = "trip"
    __table_args__ = {"schema": "analytics"}

    # Primary key
    ride_id = Column(String, primary_key=True)
    
    # Customer info
    rider_id = Column(String)
    driver_status = Column(String)
    
    # Location info
    pickup_location = Column(String)
    dropoff_location = Column(String)
    pickup_lat = Column(Float)
    pickup_lng = Column(Float)
    dropoff_lat = Column(Float)
    dropoff_lng = Column(Float)
    
    # Status
    status = Column(String)
    booking_status = Column(String)
    ride_type = Column(String)
    
    # Pricing
    estimated_fare = Column(Float)
    actual_fare = Column(Float)
    
    # Timing
    distance_km = Column(Float)
    duration_minutes = Column(Float)  # CTAT stored here
    driver_rating = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime)
    vehicle_arrival_at = Column(DateTime)  # VTAT timestamp
    completed_at = Column(DateTime)        # CTAT timestamp
    
    # ML Features (NEW)
    vtat_minutes = Column(Float)           # VTAT in minutes
    ctat_minutes = Column(Float)           # CTAT in minutes
    pickup_encoded = Column(Integer)
    drop_encoded = Column(Integer)
    route_cluster = Column(Integer)
    
    # Time features
    day_of_week = Column(Integer)
    demand_pressure = Column(Float)
    hour = Column(Integer)