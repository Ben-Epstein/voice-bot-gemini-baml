"""
Voice Bot with Gemini and BAML
A Modal app with FastAPI serving Twilio webhooks and WebSocket connections
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import modal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
import google.generativeai as genai

# Initialize Modal app
app = modal.App("voice-bot-gemini-baml")

# Define Modal image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi",
        "twilio",
        "google-generativeai",
        "websockets",
        "python-dotenv",
        "pydantic",
        "aiofiles",
        "python-multipart",
    )
)

# Create persistent volume for storing profiles
volume = modal.Volume.from_name("voice-bot-profiles", create_if_missing=True)

# FastAPI instance
web_app = FastAPI(title="Voice Bot Gemini BAML")


class CarDetail:
    """Car rental detail information"""
    
    AVAILABLE_CARS = {
        "economy": {
            "name": "Economy Sedan",
            "price_per_day": 45,
            "features": ["4 doors", "5 seats", "automatic", "AC", "Bluetooth"],
            "fuel_efficiency": "35 MPG",
        },
        "suv": {
            "name": "Mid-size SUV",
            "price_per_day": 75,
            "features": ["5 doors", "7 seats", "automatic", "AC", "4WD", "navigation"],
            "fuel_efficiency": "25 MPG",
        },
        "luxury": {
            "name": "Luxury Sedan",
            "price_per_day": 120,
            "features": ["4 doors", "5 seats", "automatic", "premium sound", "leather seats", "sunroof"],
            "fuel_efficiency": "28 MPG",
        },
        "van": {
            "name": "Family Van",
            "price_per_day": 85,
            "features": ["sliding doors", "8 seats", "automatic", "AC", "entertainment system"],
            "fuel_efficiency": "22 MPG",
        },
    }
    
    @classmethod
    def get_car_info(cls, car_type: str) -> Optional[Dict]:
        """Get information about a specific car type"""
        return cls.AVAILABLE_CARS.get(car_type.lower())
    
    @classmethod
    def get_all_cars_summary(cls) -> str:
        """Get a summary of all available cars"""
        summary = "We have the following cars available:\n"
        for car_type, details in cls.AVAILABLE_CARS.items():
            summary += f"- {details['name']}: ${details['price_per_day']}/day\n"
        return summary


class CallSession:
    """Manages a single call session"""
    
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.conversation_history: List[Dict[str, str]] = []
        self.start_time = datetime.now()
        self.intents: List[str] = []
        self.questions: List[str] = []
        self.renter_profile: Dict = {}
        
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_conversation_text(self) -> str:
        """Get conversation as plain text"""
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.conversation_history
        ])
    
    async def save_profile(self, profiles_dir: Path):
        """Save renter profile to JSON file"""
        profile_data = {
            "call_sid": self.call_sid,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "conversation": self.conversation_history,
            "intents": self.intents,
            "questions": self.questions,
            "renter_profile": self.renter_profile,
        }
        
        profiles_dir.mkdir(parents=True, exist_ok=True)
        filename = f"profile_{self.call_sid}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = profiles_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(profile_data, f, indent=2)
        
        print(f"Saved profile to {filepath}")


class GeminiVoiceAgent:
    """Gemini-powered voice agent for car rental inquiries"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.system_prompt = """You are a helpful car rental assistant. 
You help customers find the right rental car for their needs.
You have information about various cars including economy, SUV, luxury, and van options.
Be friendly, concise, and helpful. Answer questions about:
- Car availability and features
- Pricing
- Rental terms
- Recommendations based on customer needs

Keep responses brief and conversational since this is a voice call.
"""
    
    async def generate_response(self, user_message: str, conversation_history: List[Dict]) -> str:
        """Generate a response to user message"""
        # Build context from conversation history
        context = self.system_prompt + "\n\nAvailable cars:\n" + CarDetail.get_all_cars_summary()
        context += "\n\nConversation so far:\n"
        
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            context += f"{msg['role']}: {msg['content']}\n"
        
        context += f"\nUser: {user_message}\nAssistant:"
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                context
            )
            return response.text
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I apologize, I'm having trouble processing that. Could you please repeat?"


class BAMLProcessor:
    """
    Processes conversation using BAML functions
    
    NOTE: This is currently a SIMULATED implementation for demonstration purposes.
    
    To use real BAML integration:
    1. Run `baml generate` to create the Python client from baml_src/main.baml
    2. Import the generated client: `from baml_client import b`
    3. Replace simulated methods with actual BAML calls:
       - intent = await b.ExtractIntent(conversation)
       - questions = await b.ExtractQuestions(conversation)
       - profile = await b.ExtractRenterProfile(conversation)
    """
    
    def __init__(self):
        # TODO: Replace with actual BAML client initialization
        # from baml_client import b
        # self.client = b
        pass
    
    async def extract_intent(self, conversation: str) -> str:
        """Extract intent from conversation (simulated)"""
        # In real implementation: from baml_client import b
        # return await b.ExtractIntent(conversation)
        
        # Simulated extraction
        if "price" in conversation.lower() or "cost" in conversation.lower():
            return "Inquiring about pricing"
        elif "available" in conversation.lower() or "cars" in conversation.lower():
            return "Asking about car availability"
        elif "book" in conversation.lower() or "reserve" in conversation.lower():
            return "Wants to make a reservation"
        else:
            return "General inquiry about car rental"
    
    async def extract_questions(self, conversation: str) -> List[str]:
        """Extract questions from conversation (simulated)"""
        # In real implementation: from baml_client import b
        # return await b.ExtractQuestions(conversation)
        
        # Simulated extraction
        questions = []
        lines = conversation.split('\n')
        for line in lines:
            if '?' in line and 'user:' in line.lower():
                questions.append(line.split(':', 1)[-1].strip())
        return questions
    
    async def extract_renter_profile(self, conversation: str) -> Dict:
        """Extract renter profile from conversation (simulated)"""
        # In real implementation: from baml_client import b
        # profile = await b.ExtractRenterProfile(conversation)
        # return profile.model_dump()
        
        # Simulated extraction
        profile = {
            "name": None,
            "phone": None,
            "email": None,
            "rental_dates": None,
            "car_preferences": [],
            "budget_range": None,
            "location": None,
            "additional_notes": None,
        }
        
        conv_lower = conversation.lower()
        if "economy" in conv_lower:
            profile["car_preferences"].append("economy")
        if "suv" in conv_lower:
            profile["car_preferences"].append("suv")
        if "luxury" in conv_lower:
            profile["car_preferences"].append("luxury")
            
        return profile


# Active call sessions
active_sessions: Dict[str, CallSession] = {}


@web_app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "voice-bot-gemini-baml"}


@web_app.post("/webhook")
async def twilio_webhook(request: Request):
    """
    Twilio webhook endpoint - receives incoming call notifications
    Creates TwiML response to connect the call to our WebSocket
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    to_number = form_data.get("To")
    
    print(f"Incoming call: {call_sid} from {from_number} to {to_number}")
    
    # Create new call session
    session = CallSession(call_sid)
    active_sessions[call_sid] = session
    
    # Create TwiML response to connect to WebSocket
    response = VoiceResponse()
    response.say("Welcome to our car rental service. How can I help you today?")
    
    # Connect to our WebSocket endpoint
    connect = Connect()
    # Get WebSocket URL from environment or use a placeholder
    # Set MODAL_WEBSOCKET_URL environment variable to your actual Modal deployment URL
    base_url = os.environ.get("MODAL_WEBSOCKET_URL", "wss://your-modal-app.modal.run")
    websocket_url = f"{base_url}/ws/{call_sid}"
    stream = Stream(url=websocket_url)
    connect.append(stream)
    response.append(connect)
    
    return Response(content=str(response), media_type="application/xml")


@web_app.websocket("/ws/{call_sid}")
async def websocket_endpoint(websocket: WebSocket, call_sid: str):
    """
    WebSocket endpoint for real-time voice communication with Gemini
    Runs voice agent and BAML processing concurrently
    """
    await websocket.accept()
    print(f"WebSocket connected for call: {call_sid}")
    
    # Get or create session
    session = active_sessions.get(call_sid)
    if not session:
        session = CallSession(call_sid)
        active_sessions[call_sid] = session
    
    # Initialize Gemini agent
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    agent = GeminiVoiceAgent(gemini_api_key)
    
    # Initialize BAML processor
    baml_processor = BAMLProcessor()
    
    # Start BAML processing loop
    async def baml_processing_loop():
        """Async loop to extract intent and questions periodically"""
        while True:
            try:
                await asyncio.sleep(5)  # Process every 5 seconds
                
                if len(session.conversation_history) > 0:
                    conversation_text = session.get_conversation_text()
                    
                    # Extract intent
                    intent = await baml_processor.extract_intent(conversation_text)
                    if intent and intent not in session.intents:
                        session.intents.append(intent)
                        print(f"Extracted intent: {intent}")
                    
                    # Extract questions
                    questions = await baml_processor.extract_questions(conversation_text)
                    for q in questions:
                        if q and q not in session.questions:
                            session.questions.append(q)
                            print(f"Extracted question: {q}")
                    
                    # Update renter profile
                    profile = await baml_processor.extract_renter_profile(conversation_text)
                    session.renter_profile.update(profile)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in BAML processing: {e}")
    
    # Start BAML processing task
    baml_task = asyncio.create_task(baml_processing_loop())
    
    try:
        while True:
            # Receive audio/text data from Twilio
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different Twilio message types
            if message_data.get("event") == "connected":
                print(f"Stream connected: {call_sid}")
                
            elif message_data.get("event") == "start":
                print(f"Stream started: {call_sid}")
                
            elif message_data.get("event") == "media":
                # Audio data from caller
                # In a full implementation, this would be transcribed
                # For now, we'll simulate with text
                pass
                
            elif message_data.get("event") == "stop":
                print(f"Stream stopped: {call_sid}")
                break
            
            # Simulate handling a text message (in real implementation, transcribe audio)
            if "text" in message_data:
                user_message = message_data["text"]
                session.add_message("user", user_message)
                
                # Generate response with Gemini
                response = await agent.generate_response(
                    user_message,
                    session.conversation_history
                )
                session.add_message("assistant", response)
                
                # Send response back
                await websocket.send_json({
                    "event": "response",
                    "text": response
                })
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {call_sid}")
    except Exception as e:
        print(f"Error in WebSocket handler: {e}")
    finally:
        # Cancel BAML processing
        baml_task.cancel()
        try:
            await baml_task
        except asyncio.CancelledError:
            pass
        
        # Save renter profile
        profiles_dir = Path("/profiles")
        await session.save_profile(profiles_dir)
        
        # Clean up session
        if call_sid in active_sessions:
            del active_sessions[call_sid]
        
        print(f"Call ended and profile saved: {call_sid}")


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-api-key"),
        modal.Secret.from_name("twilio-credentials"),
    ],
    volumes={"/profiles": volume},
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    """Modal ASGI app wrapper for FastAPI"""
    return web_app


if __name__ == "__main__":
    # For local development
    import uvicorn
    uvicorn.run(web_app, host="0.0.0.0", port=8000)
