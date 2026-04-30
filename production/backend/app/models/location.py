from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    encoded_value = Column(Integer, unique=True)
    lat = Column(Float) # Latitude
    lng = Column(Float) # Longitude