from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional

Base = declarative_base()

class Trip(Base):
    """Model for sql table (analytics.trip)"""
    __table__name = "trip"
    __table_args__ = {'schema': 'analytics'}

    ride_id: str = Column(String, primary_key=True)
    rider_id: str = Column(String)
    driver_status: str = Column(String)
    pickup_location: str = Column(String)
    dropoff_location: str = Column(String)
    pickup_lat: float = Column(Float)
    pickup_lng: float = Column(Float)
    dropoff_lat: float = Column(Float)
    dropoff_lng: float = Column(Float)
    status: str = Column(String)
    ride_type: str = Column(String)
    estimated_fare: float = Column(Float)
    actual_fare: float = Column(Float)
    distance_km: float = Column(Float)
    duration_minutes: float = Column(Float)
    driver_rating: float = Column(Float)
    booking_status: str = Column(String)
    created_at: datetime = Column(DateTime)
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)