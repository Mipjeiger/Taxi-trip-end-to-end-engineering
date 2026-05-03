from sqlalchemy import Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Ride(Base):
    __tablename__ = 'rides'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    estimated_time_min = Column(Float, nullable=False)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def __repr__(self):
        return f"<Ride {self.id} from {self.pickup_location} to {self.drop_location}>"