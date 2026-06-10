from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trip(Base):
    __tablename__ = "trip"
    __table_args__ = {"schema": "analytics"}
    
    ride_id = Column(String, primary_key=True)
    rider_id = Column(String)
    driver_status = Column(String)
    pickup_location = Column(String)
    dropoff_location = Column(String)
    pickup_lat = Column(Float)
    pickup_lng = Column(Float)
    dropoff_lat = Column(Float)
    dropoff_lng = Column(Float)
    status = Column(String)
    ride_type = Column(String)
    estimated_fare = Column(Float)
    actual_fare = Column(Float)
    distance_km = Column(Float)
    duration_minutes = Column(Float)
    driver_rating = Column(Float)
    booking_status = Column(String)
    created_at = Column(DateTime)
    completed_at = Column(DateTime)