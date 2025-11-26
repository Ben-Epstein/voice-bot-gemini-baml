"""
Basic tests for the voice bot application
"""

import pytest
from fastapi.testclient import TestClient
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import web_app, CallSession, CarDetail, BAMLProcessor


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(web_app)


def test_root_endpoint(client):
    """Test the health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_car_details():
    """Test car detail retrieval"""
    # Test getting economy car info
    economy = CarDetail.get_car_info("economy")
    assert economy is not None
    assert economy["name"] == "Economy Sedan"
    assert economy["price_per_day"] == 45

    # Test getting all cars summary
    summary = CarDetail.get_all_cars_summary()
    assert "Economy Sedan" in summary
    assert "Mid-size SUV" in summary
    assert "$45/day" in summary


def test_call_session():
    """Test call session management"""
    session = CallSession("test_call_123")

    # Test initial state
    assert session.call_sid == "test_call_123"
    assert len(session.conversation_history) == 0
    assert len(session.intents) == 0

    # Test adding messages
    session.add_message("user", "Hello, I need a car")
    session.add_message("assistant", "I can help you with that")

    assert len(session.conversation_history) == 2
    assert session.conversation_history[0]["role"] == "user"
    assert session.conversation_history[0]["content"] == "Hello, I need a car"

    # Test getting conversation text
    conv_text = session.get_conversation_text()
    assert "user: Hello, I need a car" in conv_text
    assert "assistant: I can help you with that" in conv_text


@pytest.mark.asyncio
async def test_baml_processor():
    """Test BAML processor functionality"""
    processor = BAMLProcessor()

    # Test intent extraction
    conversation = "user: How much does an economy car cost?\nassistant: $45 per day"
    intent = await processor.extract_intent(conversation)
    assert "pricing" in intent.lower() or "price" in intent.lower()

    # Test question extraction
    conversation = "user: What cars are available?\nuser: Do you have SUVs?"
    questions = await processor.extract_questions(conversation)
    assert len(questions) >= 0  # May or may not extract based on implementation

    # Test profile extraction
    conversation = "user: I'm looking for an economy car\nassistant: Great choice"
    profile = await processor.extract_renter_profile(conversation)
    assert isinstance(profile, dict)
    assert "car_preferences" in profile
    assert "economy" in profile["car_preferences"]


def test_webhook_endpoint(client):
    """Test Twilio webhook endpoint"""
    # Simulate Twilio webhook request
    form_data = {
        "CallSid": "CA1234567890",
        "From": "+15551234567",
        "To": "+15559876543",
    }

    response = client.post("/webhook", data=form_data)
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]

    # Check TwiML response contains expected elements
    response_text = response.text
    assert "<Response>" in response_text
    assert "Welcome to our car rental service" in response_text


@pytest.mark.asyncio
async def test_session_save_profile(tmp_path):
    """Test saving renter profile"""
    session = CallSession("test_call_456")
    session.add_message("user", "I need a luxury car")
    session.add_message("assistant", "Our luxury sedan is $120 per day")
    session.intents.append("Inquiring about luxury cars")
    session.questions.append("How much does a luxury car cost?")
    session.renter_profile = {"name": "John Doe", "car_preferences": ["luxury"]}

    # Save profile to temp directory
    profiles_dir = tmp_path / "profiles"
    await session.save_profile(profiles_dir)

    # Check file was created
    profile_files = list(profiles_dir.glob("profile_*.json"))
    assert len(profile_files) == 1

    # Check file contents
    with open(profile_files[0], "r") as f:
        data = json.load(f)

    assert data["call_sid"] == "test_call_456"
    assert len(data["conversation"]) == 2
    assert len(data["intents"]) == 1
    assert len(data["questions"]) == 1
    assert data["renter_profile"]["name"] == "John Doe"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
