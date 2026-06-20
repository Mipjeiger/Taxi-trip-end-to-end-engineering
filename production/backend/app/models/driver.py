from sqlalchemy import Column, String, Float, Integer, DateTime, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = {"schema": "analytics"}

    driver_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    plate = Column(String, nullable=False)
    rating = Column(Float, default=4.5)
    total_trips = Column(Integer, default=0)
    status = Column(String, default='offline')  # offline, online, busy, on_break, inactive
    lat = Column(Float)
    lng = Column(Float)
    last_online_at = Column(DateTime)
    last_active_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(datetime.timezone.utc), onupdate=datetime.now(datetime.timezone.utc))

    def __repr__(self):
        return f"<Driver(driver_id={self.driver_id}, name={self.name}, status={self.status})>"