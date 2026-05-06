from sqlalchemy import Column, String, Float, DateTime
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
    estimated_pickup_time_minute = Column(Float, nullable=False)
    estimated_drop_time_minute = Column(Float, nullable=False)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}