from typing import Union
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
    ONLINE = "Online"
    OFFLINE = "Offline"

class PredictionRequest(BaseModel):
    """ML prediction request with vehicle type validation"""
    pickup_location: str
    drop_location: str
    vehicle_type: str = Field(
        "HRV",
        pattern="^(HRV|Innova|Alphard|Go Sedan|Premier Sedan|Brio|Terios)$",
        description="One of: HRV, Innova, Alphard, Go Sedan, Premier Sedan, Brio, Terios"
    )
    hour: int
    day_of_week: int
    distance_km: float

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
                "vehicle_type": "HRV",
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
    price: float
    vehicle_type: str = Field(
        "HRV",
        pattern="^(HRV|Innova|Alphard|Go Sedan|Premier Sedan|Brio|Terios)$"
    )
    distance_km: Optional[float] = None
    demand_pressure: Optional[float] = None
    rating_avg: Optional[float] = None
    price: float
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "CID4647897",
                "pickup_location": "Kebon Baru",
                "drop_location": "Halim Perdana Kusuma",
                "vehicle_type": "Go Sedan",
                "distance_km": 39.92,
                "demand_pressure": 690.5,
                "rating_avg": 4,
                "price": 335000,
                "pickup_lat": -6.2329499,
                "pickup_lng": 106.8614867,
                "dropoff_lat": -6.2655682,
                "dropoff_lng": 106.8936385,
            }
        },
        protected_namespaces=()
    )


class RideResponse(BaseModel):
    """Response for database ride record with all fields"""
    ride_id: str
    rider_id: str
    driver_status: str
    pickup_location: str
    dropoff_location: str
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    status: str
    ride_type: str
    estimated_fare: float
    actual_fare: float
    distance_km: float
    duration_minutes: float
    driver_rating: float
    booking_status: str
    created_at: datetime
    vehicle_arrival_at: Optional[datetime]
    completed_at: Optional[Union[datetime, str]]
    day_of_week: int
    demand_pressure: float
    hour: int
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

class RideBookRequest(BaseModel):
    """Request to book a ride with all required fields"""
    user_id: str
    pickup_location: str
    drop_location: str
    vehicle_type: str
    price: float
    estimated_pickup_time_minute: float  # VTAT
    estimated_drop_time_minute: float    # CTAT
    pickup_encoded: int
    drop_encoded: int
    route_cluster: int
    ride_distance: float
    pickup_lat: float
    pickup_lon: float
    drop_lat: float
    drop_lon: float
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "CID123456",
                "pickup_location": "Senen",
                "drop_location": "Malaka Jaya",
                "vehicle_type": "Go Sedan",
                "price": 75000,
                "estimated_pickup_time_minute": 10.5,
                "estimated_drop_time_minute": 25.3,
                "pickup_encoded": 42,
                "drop_encoded": 18,
                "route_cluster": 7,
                "ride_distance": 12.5,
                "pickup_lat": -6.1754,
                "pickup_lon": 106.8272,
                "drop_lat": -6.2186,
                "drop_lon": 106.8501
            }
        },
        protected_namespaces=()
    )