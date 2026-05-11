from kafka import KafkaProducer
import json
from datetime import datetime
import logging

class FrontendEventProducer:
    """
    Kafka producer for frontend user interactions.
    Events:
    - find_rides: User searches for rides
    - chat_message: User asks LLM Chatbot for ride recommendations
    - route_selected: User selects a route
    - ride_booked: User confirms ride booking
    """

    def __init__(self, bootstrap_servers=['kafka:9092']):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )

    def track_find_rides_event(self, user_id, pickup, drop, vehicle_type):
        """Track user searching for rides"""
        event = {
            'event_type': 'finde_rides',
            'user_id': user_id,
            'pickup_location': pickup,
            'drop_location': drop,
            'vehicle_type': vehicle_type,
            'timestamp': datetime.now().isoformat(),
            'event_id': f"{user_id}_{datetime.now().timestamp()}"
        }
        self.producer.send('frontend-events', value=event)
        logging.info(f"📤 Event sent: {event['event_type']}")

    def track_chat_event(self, user_id, message, response, model_used='groq'):
        """Track LLM chatbot interactions"""
        event = {
            'event_type': 'chat_message',
            'user_id': user_id,
            'message': message,
            'response': response,
            'model_used': model_used,
            'timestamp': datetime.now().isoformat(),
            'event_id': f"{user_id}_{datetime.now().timestamp()}"
        }
        self.producer.send('frontend-events', value=event)
        logging.info(f"📤 Chat event tracked")

    def track_route_selection(self, user_id, route_id, estimated_price, estimated_time):
        """Track route selection by user"""
        event = {
            'event_type': 'route_selected',
            'user_id': user_id,
            'route_id': route_id,
            'estimated_price': estimated_price,
            'estimated_time': estimated_time,
            'timestamp': datetime.now().isoformat(),
            'event_id': f"{user_id}_route_{datetime.now().timestamp()}"
        }
        self.producer.send('frontend-events', value=event)

    def track_ride_booked(self, user_id, ride_id, pickup, drop, price):
        """Track ride booking confirmation"""
        event = {
            'event_type': 'ride_booked',
            'user_id': user_id,
            'ride_id': ride_id,
            'pickup_location': pickup,
            'drop_location': drop,
            'price': price,
            'timestamp': datetime.now().isoformat(),
            'event_id': f"{user_id}_booking_{datetime.now().timestamp()}"
        }
        self.producer.send('frontend-events', value=event)
        logging.info(f"📤 Ride booked: {ride_id}")

# FastAPI Integration
from fastapi import APIRouter

router = APIRouter()
event_producer = FrontendEventProducer()

@router.post('/track/find_rides')
async def track_find_rides(user_id: str, pickup: str, drop: str, vehicle_type: str):
    """API endpoint to track ride search events"""
    event_producer.track_find_rides_event(user_id, pickup, drop, vehicle_type)
    return {"status": "tracked"}

@router.post("/track/chat")
async def track_chat(user_id: str, message: str, response: str):
    """API endpoint to track chat interactions"""
    event_producer.track_chat_event(user_id, message, response)
    return {"status": "tracked"}

@router.post("/track/route_selected")
async def track_route_selection(user_id: str, route_id: str, price: float, time: float):
    """API endpoint to track route selection"""
    event_producer.track_route_selection(user_id, route_id, price, time)
    return {"status": "tracked"}

@router.post("/track/ride_booked")
async def track_ride_booked(user_id: str, ride_id: str, pickup: str, drop: str, price: float):
    """API endpoint to track ride booking"""
    event_producer.track_ride_booked(user_id, ride_id, pickup, drop, price)
    return {"status": "tracked"}