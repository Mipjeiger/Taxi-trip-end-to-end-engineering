import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Mock driver data with realistic Indonesian names (used as fallback)
MOCK_DRIVERS = {
    "Alphard": [
        {"name": "Ahmad Rizki", "plate": "B 1234 XY", "trips": 1240},
        {"name": "Budi Santoso", "plate": "B 5678 AB", "trips": 856},
    ],
    "HRV": [
        {"name": "Aji Ahmad", "plate": "B 9012 CD", "trips": 2340},
        {"name": "Dedi Firmansyah", "plate": "B 3456 EF", "trips": 512},
    ],
    "Go Sedan": [
        {"name": "Eko Pratama", "plate": "B 7890 GH", "trips": 320},
        {"name": "Fajar Pratama", "plate": "B 2345 IJ", "trips": 180},
    ],
    "Innova": [
        {"name": "Guguh Setiawan", "plate": "B 6789 KL", "trips": 95},
        {"name": "Hendra Wijaya", "plate": "B 0123 MN", "trips": 450},
    ],
    "Premier Sedan": [
        {"name": "Irfan Maulana", "plate": "B 4567 OP", "trips": 210},
        {"name": "Joko Susilo", "plate": "B 8901 QR", "trips": 75},
    ],
    "Brio": [
        {"name": "Khairul Anwar", "plate": "B 2345 ST", "trips": 150},
        {"name": "Lukman Hakim", "plate": "B 6789 UV", "trips": 60},
    ],
    "Terios": [
        {"name": "Khairi Kahfi", "plate": "B 0123 WX", "trips": 40},
        {"name": "Nugroho Aji", "plate": "B 4567 YZ", "trips": 25},
    ]
}


class DriverMatchingService:
    """Service to match drivers to rides"""
    
    @staticmethod
    async def find_driver(
        db: AsyncSession,
        pickup_location: str,
        dropoff_location: str,
        vehicle_type: str,
        ride_id: str
    ) -> Optional[Dict]:
        """
        Find and assign a driver to a ride.
        driver_status = 'Online' means driver is assigned and active.
        """
        try:
            # First try to get available driver from database
            query = text("""
                SELECT 
                    driver_id,
                    name,
                    vehicle_type,
                    plate,
                    rating,
                    total_trips,
                    status,
                    lat,
                    lng
                FROM analytics.drivers
                WHERE status = 'online'
                AND vehicle_type = :vehicle_type
                ORDER BY rating DESC, total_trips DESC
                LIMIT 1
            """)
            
            result = await db.execute(query, {"vehicle_type": vehicle_type})
            driver = result.fetchone()
            
            # If no exact match, find any online driver
            if not driver:
                logger.info(f"⚠️ No online {vehicle_type} driver, finding any online driver")
                query = text("""
                    SELECT 
                        driver_id,
                        name,
                        vehicle_type,
                        plate,
                        rating,
                        total_trips,
                        status,
                        lat,
                        lng
                    FROM analytics.drivers
                    WHERE status = 'online'
                    ORDER BY rating DESC, total_trips DESC
                    LIMIT 1
                """)
                result = await db.execute(query)
                driver = result.fetchone()
                
                # If still no driver, try to create one from trip data
                if not driver:
                    logger.info(f"ℹ️ No online drivers available, creating driver from trip data for {vehicle_type}")
                    
                    # Try to create a driver from trip data
                    create_query = text("""
                        INSERT INTO analytics.drivers (driver_id, name, vehicle_type, plate,
                                        rating, total_trips, status, lat, lng)
                        SELECT
                            CONCAT('DRV', LPAD(ROW_NUMBER() OVER (PARTITION BY ride_type ORDER BY driver_rating DESC)::TEXT, 3, '0')) as driver_id,
                            CONCAT('Driver ', ride_type, ' ', ROW_NUMBER() OVER (PARTITION BY ride_type ORDER BY driver_rating DESC)) as name,
                            ride_type as vehicle_type,
                            CONCAT('B ', 
                                LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0'), 
                                ' ', 
                                CHR(65 + FLOOR(RANDOM() * 26)::INT), 
                                CHR(65 + FLOOR(RANDOM() * 26)::INT)
                            ) as plate,
                            ROUND(AVG(driver_rating), 1) as rating,
                            COUNT(*) as total_trips,
                            'online' as status,
                            -6.17 + (RANDOM() - 0.5) * 0.05 as lat,
                            106.82 + (RANDOM() - 0.5) * 0.05 as lng
                        FROM analytics.trip
                        WHERE driver_rating IS NOT NULL
                            AND ride_type = :vehicle_type
                            AND status = 'Completed'
                        GROUP BY ride_type
                        LIMIT 1
                    """)

                    await db.execute(create_query, {"vehicle_type": vehicle_type})
                    await db.commit()

                    # Try again to find the newly created driver
                    result = await db.execute(query, {"vehicle_type": vehicle_type})
                    driver = result.fetchone()
                    
                    if driver:
                        logger.info(f"✅ Created new driver for {vehicle_type} from trip data")

            # If still no driver, use mock fallback
            if not driver:
                logger.warning(f"⚠️ No drivers available in database, using mock driver")
                return await DriverMatchingService._find_mock_driver(
                    vehicle_type, pickup_location, dropoff_location, ride_id, db
                )
            
            # Calculate ETA based on distance (simplified)
            eta_minutes = 2 + (abs(hash(pickup_location)) % 10)
            vehicle_arrival_at = datetime.now() + timedelta(minutes=eta_minutes)
            
            # Update ride - SET driver_status to 'Online' (driver assigned)
            update_query = text("""
                UPDATE analytics.trip 
                SET 
                    driver_status = 'Online',
                    driver_rating = :driver_rating,
                    vehicle_arrival_at = :vehicle_arrival_at
                WHERE ride_id = :ride_id
            """)
            
            await db.execute(update_query, {
                "driver_rating": driver[4],
                "vehicle_arrival_at": vehicle_arrival_at,
                "ride_id": ride_id
            })
            await db.commit()
            
            # Mark driver as busy (so they won't be assigned another ride)
            update_driver_query = text("""
                UPDATE analytics.drivers 
                SET 
                    status = 'busy',
                    last_active_at = :now,
                    updated_at = :now
                WHERE driver_id = :driver_id
            """)
            
            await db.execute(update_driver_query, {
                "driver_id": driver[0],
                "now": datetime.now()
            })
            await db.commit()
            
            logger.info(f"✅ Driver {driver[1]} assigned to ride {ride_id} (status: Online)")
            
            return {
                "driver_id": driver[0],
                "name": driver[1],
                "vehicle": driver[2],
                "plate": driver[3],
                "rating": driver[4],
                "trips": driver[5],
                "status": "Online",
                "lat": driver[7],
                "lng": driver[8],
                "eta_minutes": eta_minutes
            }
            
        except Exception as e:
            logger.error(f"❌ Error finding driver: {e}")
            # Use mock fallback on error
            return await DriverMatchingService._find_mock_driver(
                vehicle_type, pickup_location, dropoff_location, ride_id, db
            )
    
    @staticmethod
    async def _find_mock_driver(
        vehicle_type: str,
        pickup_location: str,
        dropoff_location: str,
        ride_id: str,
        db: AsyncSession
    ) -> Optional[Dict]:
        """Fallback to mock drivers when no database drivers available"""
        try:
            # Get real driver_rating from database for this vehicle type
            rating_query = text("""
                SELECT AVG(driver_rating) as avg_rating
                FROM analytics.trip
                WHERE ride_type = :vehicle_type
                  AND driver_rating IS NOT NULL
                LIMIT 1
            """)
            
            result = await db.execute(rating_query, {"vehicle_type": vehicle_type})
            avg_rating = result.fetchone()
            driver_rating = float(avg_rating[0]) if avg_rating and avg_rating[0] else 4.5
            
            # Get mock driver info for this vehicle type
            drivers = MOCK_DRIVERS.get(vehicle_type, [
                {"name": "Driver", "plate": "B 1234 XY", "trips": 100}
            ])
            driver_info = random.choice(drivers)
            
            eta_minutes = 2 + (abs(hash(pickup_location)) % 10)
            vehicle_arrival_at = datetime.now() + timedelta(minutes=eta_minutes)
            
            # Update ride with driver info
            update_query = text("""
                UPDATE analytics.trip 
                SET 
                    driver_status = 'Online',
                    driver_rating = :driver_rating,
                    vehicle_arrival_at = :vehicle_arrival_at
                WHERE ride_id = :ride_id
            """)
            
            await db.execute(update_query, {
                "driver_rating": driver_rating,
                "vehicle_arrival_at": vehicle_arrival_at,
                "ride_id": ride_id
            })
            await db.commit()
            
            logger.info(f"✅ Mock driver {driver_info['name']} assigned to ride {ride_id}")
            
            return {
                "driver_id": f"DRV{random.randint(100, 999)}",
                "name": driver_info["name"],
                "vehicle": vehicle_type,
                "plate": driver_info["plate"],
                "rating": round(driver_rating, 1),
                "trips": driver_info["trips"],
                "status": "Online",
                "lat": -6.1754 + (random.random() - 0.5) * 0.01,
                "lng": 106.8272 + (random.random() - 0.5) * 0.01,
                "eta_minutes": eta_minutes
            }
            
        except Exception as e:
            logger.error(f"❌ Error using mock driver: {e}")
            return None
    
    @staticmethod
    async def complete_ride(db: AsyncSession, ride_id: str) -> bool:
        """
        Complete a ride - sets driver_status back to 'Offline'.
        """
        try:
            # Get the ride to find which driver is assigned
            get_driver_query = text("""
                SELECT driver_id FROM analytics.trip WHERE ride_id = :ride_id
            """)
            result = await db.execute(get_driver_query, {"ride_id": ride_id})
            row = result.fetchone()
            
            update_query = text("""
                UPDATE analytics.trip 
                SET 
                    driver_status = 'Offline',
                    booking_status = 'Completed',
                    status = 'Completed',
                    completed_at = :completed_at
                WHERE ride_id = :ride_id
            """)
            
            await db.execute(update_query, {
                "completed_at": datetime.now(),
                "ride_id": ride_id
            })
            
            # If driver exists, set them back to online
            if row and row[0]:
                update_driver_query = text("""
                    UPDATE analytics.drivers 
                    SET 
                        status = 'online',
                        total_trips = total_trips + 1,
                        updated_at = :now
                    WHERE driver_id = :driver_id
                """)
                await db.execute(update_driver_query, {
                    "driver_id": row[0],
                    "now": datetime.now()
                })
            
            await db.commit()
            
            logger.info(f"✅ Ride {ride_id} completed - driver_status set to Offline")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error completing ride: {e}")
            return False
    
    @staticmethod
    async def cancel_ride(db: AsyncSession, ride_id: str) -> bool:
        """
        Cancel a ride - sets driver_status back to 'Offline'.
        """
        try:
            # Get the ride to find which driver is assigned
            get_driver_query = text("""
                SELECT driver_id FROM analytics.trip WHERE ride_id = :ride_id
            """)
            result = await db.execute(get_driver_query, {"ride_id": ride_id})
            row = result.fetchone()
            
            update_query = text("""
                UPDATE analytics.trip 
                SET 
                    driver_status = 'Offline',
                    booking_status = 'Cancelled by Customer',
                    status = 'Cancelled by Customer'
                WHERE ride_id = :ride_id
            """)
            
            await db.execute(update_query, {"ride_id": ride_id})
            
            # If driver exists, set them back to online
            if row and row[0]:
                update_driver_query = text("""
                    UPDATE analytics.drivers 
                    SET 
                        status = 'online',
                        updated_at = :now
                    WHERE driver_id = :driver_id
                """)
                await db.execute(update_driver_query, {
                    "driver_id": row[0],
                    "now": datetime.now()
                })
            
            await db.commit()
            
            logger.info(f"✅ Ride {ride_id} cancelled - driver_status set to Offline")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cancelling ride: {e}")
            return False
    
    @staticmethod
    async def get_ride_status(db: AsyncSession, ride_id: str) -> Dict:
        """Get current ride status with driver info"""
        try:
            query = text("""
                SELECT 
                    ride_id,
                    rider_id,
                    pickup_location,
                    dropoff_location,
                    status,
                    booking_status,
                    driver_status,
                    driver_rating,
                    ride_type,
                    estimated_fare,
                    actual_fare,
                    distance_km,
                    duration_minutes,
                    created_at,
                    vehicle_arrival_at,
                    completed_at
                FROM analytics.trip
                WHERE ride_id = :ride_id
            """)
            
            result = await db.execute(query, {"ride_id": ride_id})
            row = result.fetchone()
            
            if not row:
                return {"error": "Ride not found"}
            
            current_time = datetime.now()
            progress = 0
            status_message = "Ride booked"
            driver_name = None
            driver_vehicle = None
            driver_plate = None
            driver_trips = 0
            
            # Check driver status
            if row[6] == "Online":
                # Driver is assigned and active
                if row[14] and row[14] > current_time:
                    progress = 25
                    status_message = "Driver en route to you"
                elif row[14] and row[14] <= current_time:
                    progress = 50
                    status_message = "Driver arrived"
                elif row[15] and row[15] <= current_time:
                    progress = 100
                    status_message = "Arrived at destination"
                
                # Try to get driver info from drivers table
                driver_info_query = text("""
                    SELECT name, vehicle_type, plate, total_trips
                    FROM analytics.drivers
                    WHERE vehicle_type = :vehicle_type AND status IN ('busy', 'online')
                    LIMIT 1
                """)
                driver_result = await db.execute(driver_info_query, {"vehicle_type": row[8]})
                driver_row = driver_result.fetchone()
                
                if driver_row:
                    driver_name = driver_row[0]
                    driver_vehicle = driver_row[1]
                    driver_plate = driver_row[2]
                    driver_trips = driver_row[3]
                else:
                    # Fallback to mock data
                    mock_drivers = MOCK_DRIVERS.get(row[8], [{"name": "Driver", "plate": "B 1234 XY", "trips": 100}])
                    mock = random.choice(mock_drivers)
                    driver_name = mock["name"]
                    driver_vehicle = row[8]
                    driver_plate = mock["plate"]
                    driver_trips = mock["trips"]
                    
            elif row[6] == "Offline":
                # No driver assigned or ride completed
                if row[15] and row[15] <= current_time:
                    progress = 100
                    status_message = "Ride completed"
                else:
                    status_message = "Finding driver..."
            
            return {
                "ride_id": row[0],
                "rider_id": row[1],
                "pickup_location": row[2],
                "dropoff_location": row[3],
                "status": row[4],
                "booking_status": row[5],
                "driver_status": row[6],
                "driver_rating": row[7],
                "ride_type": row[8],
                "estimated_fare": float(row[9]) if row[9] else 0,
                "actual_fare": float(row[10]) if row[10] else 0,
                "distance_km": float(row[11]) if row[11] else 0,
                "duration_minutes": float(row[12]) if row[12] else 0,
                "created_at": row[13].isoformat() if row[13] else None,
                "vehicle_arrival_at": row[14].isoformat() if row[14] else None,
                "completed_at": row[15].isoformat() if row[15] else None,
                "driver_name": driver_name,
                "driver_vehicle": driver_vehicle,
                "driver_plate": driver_plate,
                "driver_trips": driver_trips,
                "progress": progress,
                "status_message": status_message
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting ride status: {e}")
            return {"error": str(e)}