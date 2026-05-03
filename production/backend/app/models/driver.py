from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    vehicle_plate = Column(String, nullable=False)
    rating = Column(Float, default=5.0)
    is_online = Column(Boolean, default=False)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    total_trips = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}