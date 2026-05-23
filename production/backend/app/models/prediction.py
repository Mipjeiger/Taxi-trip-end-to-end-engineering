from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum

# Booking status enumeration matching dataframe values
class BookingStatus(str, Enum):
    """Booking status from 'Booking Status' column in data"""
    COMPLETED = "Completed"
    CANCELLED_BY_DRIVER =  "Cancelled by Driver"
    NO_DRIVER_FOUND = "No Driver Found"
    CANCELLED_BY_CUSTOMER = "Cancelled by Customer"
    INCOMPLETE = "Incomplete"
    PENDING = "Pending"

# Vehicle arrival status based on VTAT
class VehicleArrivalStatus(str, Enum):
    """Vehicle arrival status based on prediction"""
    ARRIVING_SOON = "arriving_soon"  # VTAT < 5 minutes
    ARRIVING = "arriving"               # 5-15 min
    COMING = "coming"                   # 15-30 min
    DELAYED = "delayed"                 # >= 30 min

class DriverStatus(str, Enum):
    """Driver status for real-time tracking"""
    ONLINE = "online"
    OFFLINE = "offline"

class PredictionRequest(BaseModel):
    """ML prediction request with vehicle type validation"""
    pickup_location: str
    drop_location: str
    vehicle_type: str = Field(
        "Car",
        pattern="^(Car|Motorcycle|Auto|Go Sedan|Premier Sedan|eBike|Uber XL)$",
        description="One of: Car, Motorcycle, Auto, Go Sedan, Premier Sedan, eBike, Uber XL"
    )
    hour: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    distance_km: Optional[float] = Field(10.0, gt=0)
    demand_pressure: Optional[float] = Field(500.0, ge=170, le=777)
    rating_avg: Optional[float] = Field(4.5, ge=3.8, le=5.0)

class RidePredictionResponse(BaseModel):
    """Complete ride prediction with VTAT vehicle arrival data"""
    # Location & vehicle info
    pickup_location: str
    drop_location: str
    vehicle_type: str
    distance_km: float

    # Booking time
    booking_datetime: datetime

    # Timing predictions
    estimated_pickup_time_minute: float
    estimated_drop_time_minute: float
    total_ride_time_minute: float

    # VTAT - Vehicle arrival tracking (new features added)
    estimated_vehicle_arrival_at: datetime # When vehicle arrives at pickup
    estimated_vehicle_arrival_minute: float # VTAT in minutes
    vehicle_arrival_status: str # arriving_soon, arriving, coming, delayed

    # Pricing predictions
    estimated_price_idr: float
    price_per_km: float
    average_speed_kmh: float

    # Contextual features
    is_peak_hour: bool
    demand_pressure: float
    rating_avg: float

    # Model info
    model_confidence: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pickup_location": "Kali Anyar",
                "drop_location": "Rawamangun",
                "vehicle_type": "Car",
                "distance_km": 39.29,
                "booking_datetime": "2024-01-01T14:00:00",
                "estimated_pickup_time_minute": 8.5,
                "estimated_drop_time_minute": 15.2,
                "total_ride_time_minute": 23.7,
                "estimated_vehicle_arrival_at": "2024-01-01T14:08:30",
                "estimated_vehicle_arrival_minute": 8.5,
                "vehicle_arrival_status": "arriving",
                "estimated_completed_at": "2024-01-01T14:15:12",
                "estimated_price_idr": 114000.0,
                "price_per_km": 2900.0,
                "average_speed_kmh": 99.3,
                "is_peak_hour": True,
                "demand_pressure": 600.0,
                "rating_avg": 4.5,
                "model_confidence": "high"
            }
        },
        protected_namespaces=()
    )

class RideCreationRequest(BaseModel):
    """Request to create new ride with ML predictions (simple client input)"""
    user_id: str
    pickup_location: str
    drop_location: str
    vehicle_type: str = Field(
        "Car",
        pattern="^(Car|Motorcycle|Auto|Go Sedan|Premier Sedan|eBike|Uber XL)$"
    )
    distance_km: Optional[float] = Field(10.0, gt=0)
    demand_pressure: Optional[float] = Field(500.0, ge=170, le=777)
    rating_avg: Optional[float] = Field(4.5, ge=3.8, le=5.0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "USR-123456",
                "pickup_location": "Kali Anyar",
                "drop_location": "Rawamangun",
                "vehicle_type": "Car",
                "distance_km": 39.29,
                "demand_pressure": 600.0,
                "rating_avg": 4.5
            }
        },
        protected_namespaces=()
    )


class RideResponse(BaseModel):
    """Response for database ride record with all fields"""
    id: str
    user_id: str
    pickup_location: str
    drop_location: str
    vehicle_type: str
    price: Optional[float]
    estimated_pickup_time_minute: float  # VTAT
    estimated_drop_time_minute: float    # CTAT
    booking_status: str  # BookingStatus value
    driver_status: Optional[str] = None  # DriverStatus value
    avg_rating: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime]
    
    # ML Features
    pickup_encoded: Optional[int]
    drop_encoded: Optional[int]
    hour: Optional[int]
    day_of_week: Optional[int]
    route_cluster: Optional[int]
    ride_distance: Optional[float]
    is_peak_hour: Optional[int]
    is_weekend: Optional[int]
    is_night: Optional[int]
    hour_sin: Optional[float]
    hour_cos: Optional[float]
    day_sin: Optional[float]
    day_cos: Optional[float]
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())