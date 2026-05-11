from sqlalchemy import Column, String, Float, DateTime, Integer
from app.core.database import Base
from datetime import datetime

class Ride(Base):
    __tablename__ = 'rides'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    estimated_pickup_time_minute = Column(Float, nullable=False) # VTAT - prediction
    estimated_drop_time_minute = Column(Float, nullable=False) # CTAT - prediction
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    # ML Features integrated to app/services/ml_predictor.py
    pickup_encoded = Column(Integer, nullable=True)
    drop_encoded = Column(Integer, nullable=True)
    hour = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    route_cluster = Column(Integer, nullable=True)
    ride_distance = Column(Float, nullable=True)

    # Binary features
    is_peak_hour = Column(Integer, nullable=True)
    is_weekend = Column(Integer, nullable=True)
    is_night = Column(Integer, nullable=True)

    # Cyclical Encoding
    hour_sin = Column(Float, nullable=True)
    hour_cos = Column(Float, nullable=True)
    day_sin = Column(Float, nullable=True)
    day_cos = Column(Float, nullable=True)

    # Status & Timestamps
    status = Column(String, nullable=False)

    # VTAT - Vehicle arrival timestamp at pickup
    vtat = Column(DateTime, nullable=True)  # Vehicle Time to Arrival prediction

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}