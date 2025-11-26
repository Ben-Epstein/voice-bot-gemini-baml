from datetime import datetime
import json
from pydantic import BaseModel, Field
from pathlib import Path

from typing import Literal
from baml_client.async_client import types


class TranscriptEntry(BaseModel):
    speaker: Literal["agent", "caller"]
    text: str
    time: datetime = Field(default_factory=datetime.now)


class CallSession:
    """Manages a single call session"""

    def __init__(self, call_sid: str, caller_number: str):
        self.call_sid = call_sid
        self.caller_number: str = caller_number
        self.start_time = datetime.now()
        self.intents: list[str] = []
        self.questions: list[str] = []
        self.renter_profile: types.CallerData = types.CallerData(
            profile=types.CallerProfile(additional_notes=[], car_preferences=[]),
            questions=[],
        )
        self.transcript: list[TranscriptEntry] = []

    def get_conversation_text(self) -> str:
        """Get conversation as plain text"""
        return "\n".join([f"{msg.speaker}: {msg.text}" for msg in self.transcript])

    async def save_profile(self, profiles_dir: Path):
        """Save renter profile to JSON file"""
        profile_data = {
            "call_sid": self.call_sid,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "transcript": self.get_conversation_text(),
            "intents": self.intents,
            "questions": self.questions,
            "renter_profile": self.renter_profile.model_dump(),
        }

        profiles_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self.caller_number}_profile_{self.call_sid}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = profiles_dir / filename

        with open(filepath, "w") as f:
            json.dump(profile_data, f, indent=2)

        print(f"Saved profile to {filepath}")
