import base64
import os
from typing import Any, Literal
import typing
import typing_extensions
from fastapi import WebSocket
from datetime import datetime
from baml_client.async_client import types, b
import asyncio
from schemas import CallSession, TranscriptEntry
from google import genai
from google.genai import types as gt
from google.genai.live import AsyncSession
from twilio.rest import Client
from dotenv import load_dotenv
import logging
from db import CAR_DATABASE
from utils import mulaw_to_pcm16k

logger = logging.getLogger(__name__)

load_dotenv()

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_CLIENT = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

if os.environ["GOOGLE_APPLICATION_CREDENTIALS"].startswith("{"):
    creds_data = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    creds_path = "/tmp/google_creds.json"
    with open(creds_path, "w") as f:
        f.write(creds_data)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path


client = genai.Client(
    vertexai=True,
    project=os.environ["PROJECT_ID"],
    location=os.environ["GEMINI_REGION"],
)
MODEL = "gemini-live-2.5-flash-preview-native-audio-09-2025"

HUMAN_NUMBER = "+15164598996"


## Tools
async def can_end_call() -> dict:
    return {"can_end": True, "message": "You can end the call now."}


async def end_call() -> dict:
    return {"status": "ending call"}


async def transfer_to_human() -> dict:
    return {"status": "transferring to human agent..."}


async def can_transfer_to_human() -> dict:
    # Returns true if it is before 5pm local time
    now = datetime.now()
    after_hours = 17  # 5pm
    if now.hour >= after_hours:
        return {
            "can_transfer": False,
            "message": (
                f"It's after {after_hours - 12} local time. Call cannot be transfered to a human. Inform the renter "
                "that they can call back tomorrow during business hours, and that any preferences they "
                "share now will be noted."
            ),
        }
    return {
        "can_transfer": True,
        "message": "You can transfer the call to a human agent.",
    }


async def show_top_cars(
    makes: list[str] | None = None,
    models: list[str] | None = None,
    year_gte: int | None = None,
    year_lte: int | None = None,
    budget_low: float | None = None,
    budget_high: float | None = None,
    car_type: types.CarType | None = None,
    sale_type: types.SaleType | None = None,
    fuel_efficiency_gte: int | None = None,
    features: list[str] | None = None,
    horsepower_gte: int | None = None,
    seats_gte: int | None = None,
    order_by: Literal["year", "price", "mileage"] = "price",
    top_n: int = 5,
) -> dict:
    relevant_cars = [
        car
        for car in CAR_DATABASE
        if (not makes or car.make in makes)
        and (not models or car.model in models)
        and (not year_gte or car.year >= year_gte)
        and (not year_lte or car.year <= year_lte)
        and (not budget_low or car.price >= budget_low)
        and (not budget_high or car.price <= budget_high)
        and (not car_type or car.type == car_type)
        and (not sale_type or car.sale_type == sale_type)
        and (not fuel_efficiency_gte or car.fuel_efficiency >= fuel_efficiency_gte)
        and (not horsepower_gte or car.horsepower >= horsepower_gte)
        and (not seats_gte or car.seats >= seats_gte)
        and (not features or all(feature in car.features for feature in features))
    ]
    relevant_cars.sort(key=lambda car: getattr(car, order_by))
    print(relevant_cars[:top_n])
    return {"top_cars": [c.model_dump() for c in relevant_cars[:top_n]]}


can_end_call_decl = {
    "name": "can_end_call",
    "description": (
        "Check if the call can be ended. Returns a message if it can be ended. "
        "You must call this and it must return True before calling end_call."
    ),
    "parameters": {"type": "object", "properties": {}},
}
end_call_decl = {
    "name": "end_call",
    "description": "Immediately ends the call. This may only be called after can_end_call returns True.",
    "parameters": {"type": "object", "properties": {}},
}
can_transfer_to_human_decl = {
    "name": "can_transfer_to_human",
    "description": (
        "Check if the call can be transfered to a human agent. Returns true if there is a human able to take the "
        "transfer, false otherwise. You must call this and it must return True before calling transfer_to_human."
    ),
    "parameters": {"type": "object", "properties": {}},
}
transfer_to_human_decl = {
    "name": "transfer_to_human",
    "description": (
        "Transfer the call to a human leasing agent. This may only be called after `can_transfer_to_human` returne True"
    ),
    "parameters": {"type": "object", "properties": {}},
}
get_caller_profile_decl = {
    "name": "get_caller_profile",
    "description": (
        "Get the most up-to-date caller profile. Helpful when presenting available cars to the caller, "
        "to match to their stated preferences"
    ),
}


# all params default to None
def literal_union_values(t):
    vals = []
    for arg in t.__args__:
        if typing.get_origin(arg) is typing_extensions.Literal:
            vals.extend(arg.__args__)
    return vals


show_top_cars_decl = {
    "name": "show_top_cars",
    "description": "Show the top N cars matching the given criteria from the car database.",
    "parameters": {
        "type": "object",
        "properties": {
            "makes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of car makes to filter by.",
            },
            "models": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of car models to filter by.",
            },
            "year_gte": {
                "type": "integer",
                "description": "Minimum year of manufacture.",
            },
            "year_lte": {
                "type": "integer",
                "description": "Maximum year of manufacture.",
            },
            "budget_low": {"type": "number", "description": "Minimum budget."},
            "budget_high": {"type": "number", "description": "Maximum budget."},
            "car_type": {
                "type": "string",
                "enum": literal_union_values(types.CarType),
                "description": "Type of car (e.g., SUV, sedan).",
            },
            "sale_type": {
                "type": "string",
                "enum": literal_union_values(types.SaleType),
                "description": "Sale type (e.g., rental, lease).",
            },
            "fuel_efficiency_gte": {
                "type": "integer",
                "description": "Minimum fuel efficiency (mileage/MPG).",
            },
            "features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of desired features (e.g., GPS, sunroof).",
            },
            "horsepower_gte": {
                "type": "integer",
                "description": "Minimum horsepower.",
            },
            "seats_gte": {"type": "integer", "description": "Minimum number of seats."},
            "order_by": {
                "type": "string",
                "enum": ["year", "price", "mileage"],
                "description": "Attribute to order results by.",
            },
            "top_n": {
                "type": "integer",
                "description": "Number of car results to return. Default 3, can be set higher.",
            },
        },
    },
}  # end show_top_cars_decl

# whats the right type hint here?
TOOLS: dict[str, Any] = {
    "show_top_cars": show_top_cars,
    "can_transfer_to_human": can_transfer_to_human,
    "transfer_to_human": transfer_to_human,
    "can_end_call": can_end_call,
    "end_call": end_call,
}

TOOLS_DECL = [
    {
        "function_declarations": [
            show_top_cars_decl,
            can_transfer_to_human_decl,
            transfer_to_human_decl,
            can_end_call_decl,
            end_call_decl,
            get_caller_profile_decl,
        ]
    }
]


SYSTEM_PROMPT = f"""You're name is Joanne, and are a world-class car saleswoman. 
You help customers find the right rental or full purchase car for their needs selling the best parts of the car to their unique needs.
You have information about various cars including economy, SUV, luxury, and van options.
Be friendly, concise, and helpful. Answer questions about:
- Car availability and features
- Pricing
- Rental terms
- Recommendations based on customer needs

Keep responses brief and conversational since this is a voice call. During the call, try to naturally gather the following
information from the customer:
{types.CallerProfile.model_json_schema()}

The first thing you should do is call `get_caller_profile` tool to get the current caller profile, as they may
have already called before. If there is profile data, you can reference it in your responses. If not, introduce yourself,
ask for their name, and begin learning about their needs. You should start by getting their name if you don't have it yet.

At any point, you can call `get_caller_profile` again to get the most up-to-date information about the caller.

You are looking to sell a car today. Use `show_top_cars` to see the cars available, and pass in the filters based on what you learn about the renter.

If at any point the renter asks to speak to a human agent, or if you determine that the renter would be better served by a human agent, you should first call `can_transfer_to_human` to check if a human agent is available. If it returns true, call `transfer_to_human` to transfer the call.
If the renter is being rude, or otherwise inappropriate, you can choose to end the call by first calling `can_end_call` to check if it's appropriate to end the call, and if it returns true, call `end_call` to end the call.
If the call is over and there's nothing else to do, you can call `can_end_call` to see if you can end the call. If it's true, call `end_call` to end the call

Here is the schema of the car database you can reference when recommending cars:
{types.CarInfo.model_json_schema()}.
"""


async def baml_processing_loop(session: CallSession, end_call_event: asyncio.Event):
    """Async loop to extract intent and questions periodically"""
    while True and not end_call_event.is_set():
        try:
            await asyncio.sleep(2)  # Process every 5 seconds
            if len(session.transcript) > 0:
                conversation_text = session.get_conversation_text()
                questions, profile = await asyncio.gather(
                    b.ExtractQuestions(conversation_text),
                    b.ExtractRenterProfile(conversation_text),
                )
                # update the profile
                existing_profile = session.renter_profile.profile.model_dump()
                existing_profile.update(profile.model_dump())
                session.renter_profile.profile = types.CallerProfile.model_validate(
                    existing_profile
                )
                session.renter_profile.questions.extend(questions)
                session.renter_profile.questions = sorted(
                    set(session.renter_profile.questions)
                )
                # print("Updated session profile: ", session.renter_profile)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in BAML processing: {e}")


async def start_gemini_session():
    """Initialize a Gemini Live session with Grotto's system prompt and tools."""
    CONFIG = {
        "response_modalities": ["AUDIO"],
        "tools": TOOLS_DECL,
        "system_instruction": SYSTEM_PROMPT,
        "input_audio_transcription": {},
        "output_audio_transcription": {},
    }
    async with client.aio.live.connect(
        model=MODEL,
        config=CONFIG,  # type: ignore
    ) as gs:
        # Initialize the agent with context
        await gs.send_client_content(
            turns=gt.Content(role="user", parts=[gt.Part(text="")]), turn_complete=True
        )
        yield gs  # yield control back to Twilio bridge


async def handle_user_interruption(
    ws: WebSocket,
    stream_sid: str,
    user_interrupt: asyncio.Event,
    send_twililo_queue: asyncio.Queue,
):
    print("🎤 User interrupted - stopping playback")
    user_interrupt.set()
    await ws.send_json(
        {
            "event": "clear",
            "streamSid": stream_sid,
        }
    )
    # fush the twilio queue
    try:
        while not send_twililo_queue.empty():
            send_twililo_queue.get_nowait()
    except asyncio.QueueEmpty:
        pass


async def handle_tool_calls(
    ws: WebSocket,
    session: CallSession,
    function_calls: list[gt.FunctionCall],
    send_twililo_queue: asyncio.Queue,
    stream_sid: str,
    end_call_event: asyncio.Event,
) -> list[gt.FunctionResponse]:
    function_responses = []
    for fc in function_calls or []:
        print(f"🔧 Tool call: {fc.name}")
        if not fc.name:
            continue
        if fc.name in ("transfer_to_human", "end_call"):
            while not send_twililo_queue.empty():
                await asyncio.sleep(0.05)
            if fc.name == "transfer_to_human":
                # Send audio media to twilio saying "Transfering to a human now"
                # message = "Transferring to a human now"
                # In order to send 'automated' messages or transfer calls, we use the Client sdk
                # Say a message
                TWILIO_CLIENT.calls(session.call_sid).update(
                    twiml="<Response><Say>Please hold, transferring your call</Say></Response>"
                )
                # Transfer a call
                TWILIO_CLIENT.calls(session.call_sid).update(
                    twiml=f"<Response><Dial>{HUMAN_NUMBER}</Dial></Response>"
                )
            await asyncio.sleep(2)  # wait for 2 seconds to ensure twilio processes
            end_call_event.set()
            await ws.send_json(
                {
                    "event": "close",
                    "streamSid": stream_sid,
                }
            )
            await ws.close(code=1000, reason="Call ended by agent")
            return []
        if fc.name == "get_caller_profile":
            result = session.renter_profile.model_dump()
            function_responses.append(
                gt.FunctionResponse(
                    id=fc.id,
                    name=fc.name,
                    response=result,
                )
            )
            print(f"GOT CALLER PROFILE {result}")
            continue
        handler = TOOLS.get(fc.name)
        if handler:
            try:
                if fc.args:
                    result = await handler(**fc.args)
                else:
                    result = await handler()
            except BaseException as e:
                result = {"error": f"Tool call failed: {str(e)}"}
        else:
            result = {"error": f"Unknown tool: {fc.name}"}
        function_responses.append(
            gt.FunctionResponse(
                id=fc.id,
                name=fc.name,
                response=result,
            )
        )
    return function_responses


async def receive_from_gemini(
    gs: AsyncSession,
    session: CallSession,
    ws: WebSocket,
    stream_sid: str,
    user_interrupt: asyncio.Event,
    send_twililo_queue: asyncio.Queue,
    end_call_event: asyncio.Event,
):
    while True and not end_call_event.is_set():
        async for response in gs.receive():
            try:
                if (
                    (content := response.server_content)
                    and (transc := content.input_transcription)
                    and transc.text
                ):
                    session.transcript.append(
                        TranscriptEntry(speaker="caller", text=transc.text)
                    )
                if response.server_content and response.server_content.interrupted:
                    await handle_user_interruption(
                        ws, stream_sid, user_interrupt, send_twililo_queue
                    )
                    continue
                if response.tool_call:
                    function_responses = await handle_tool_calls(
                        ws,
                        session,
                        response.tool_call.function_calls or [],
                        send_twililo_queue,
                        stream_sid,
                        end_call_event,
                    )
                    if function_responses:
                        await gs.send_tool_response(
                            function_responses=function_responses
                        )
                    continue

                # audio output from gemini, send to Twilio
                if (
                    response.server_content
                    and response.server_content.model_turn
                    and not response.server_content.interrupted
                ):
                    user_interrupt.clear()
                    for part in response.server_content.model_turn.parts or []:
                        await send_twililo_queue.put(part)

                if (
                    response.server_content
                    and response.server_content.output_transcription
                ):
                    print(f"Agent: {response.server_content.output_transcription.text}")
                    session.transcript.append(
                        TranscriptEntry(
                            speaker="agent",
                            text=response.server_content.output_transcription.text
                            or "",
                        )
                    )
            except BaseException as e:
                logger.exception(f"Error processing response: {e}")
                continue


async def forward_audio_to_gemini(
    ws: WebSocket,
    gs: AsyncSession,
    end_call_event: asyncio.Event,
):
    while True and not end_call_event.is_set():
        msg = await ws.receive_json()
        event = msg.get("event")
        if event == "media":
            payload = base64.b64decode(msg["media"]["payload"])
            pcm16k = mulaw_to_pcm16k(payload)
            await gs.send_realtime_input(
                audio=gt.Blob(data=pcm16k, mime_type="audio/pcm;rate=16000")
            )
        elif event == "closed":
            break
