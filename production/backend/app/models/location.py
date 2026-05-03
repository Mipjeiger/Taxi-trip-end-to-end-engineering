from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    encoded_value = Column(Integer, unique=True)
    lat = Column(Float) # Latitude
    lng = Column(Float) # Longitude
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "encoded_value": self.encoded_value,
            "lat": self.lat,
            "lng": self.lng
        }
    
    def __repr__(self):
        return f"<Location {self.name} (encoded: {self.encoded_value})>"