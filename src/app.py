"""
Voice Bot with Gemini and BAML
A Modal app with FastAPI serving Twilio webhooks and WebSocket connections
"""

import os
import asyncio
from pathlib import Path

import modal
from fastapi import FastAPI, WebSocket, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from schemas import CallSession
from twilio_utils import send_to_twilio
from voice_agent import (
    baml_processing_loop,
    forward_audio_to_gemini,
    receive_from_gemini,
    start_gemini_session,
)
from google.genai import types as gt
from baml_client import types
from dotenv import load_dotenv
import requests
import vllm_server

load_dotenv()

if os.getenv("RUN_LOCAL") == "1":
    ACTIVE_SESSIONS: dict[str, CallSession] = {}
    USER_SESSIONS: dict[str, types.CallerData] = {}
else:
    ACTIVE_SESSIONS: dict[str, CallSession] = modal.Dict.from_name(  # type: ignore
        "active-sessions", create_if_missing=True
    )
    USER_SESSIONS: dict[str, types.CallerData] = modal.Dict.from_name(  # type: ignore
        "user-sessions", create_if_missing=True
    )


def get_websocket() -> str:
    if os.getenv("RUN_LOCAL") == "1":
        ngrok_url: str = requests.get("http://localhost:4040/api/tunnels").json()[
            "tunnels"
        ][0]["public_url"]
        websocket = ngrok_url.replace("https://", "wss://")
    else:
        websocket = os.environ["MODAL_WEBSOCKET_URL"]
    return websocket


app = modal.App("voice-bot-gemini-baml")
PYTHON_SOURCES = [
    "baml_client",
    "app",
    "db",
    "schemas",
    "twilio_utils",
    "voice_agent",
    "utils",
    "vllm_server",
]
# Define Modal image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_sync()
    .add_local_python_source(*PYTHON_SOURCES)
)

# Create persistent volume for storing profiles
volume = modal.Volume.from_name("voice-bot-profiles", create_if_missing=True)

# FastAPI instance
web_app = FastAPI(title="Voice Bot Gemini BAML")


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
    call_sid: str = str(form_data["CallSid"])
    from_number: str = str(form_data["From"])
    to_number = form_data.get("To")

    print(f"Incoming call: {call_sid} from {from_number} to {to_number}")

    # Create new call session
    session = CallSession(call_sid, from_number)
    ACTIVE_SESSIONS[from_number] = session
    if from_number not in USER_SESSIONS:
        USER_SESSIONS[from_number] = types.CallerData(
            profile=types.CallerProfile(car_preferences=[], additional_notes=[]),
            questions=[],
        )

    # Create TwiML response to connect to WebSocket
    response = VoiceResponse()
    response.say(
        "Welcome to our car rental service. A service representative will connect with you shortly."
    )

    # Connect to our WebSocket endpoint
    connect = Connect()
    base_url = get_websocket()
    websocket_url = f"{base_url}/ws/{from_number}"
    stream = Stream(url=websocket_url)
    connect.append(stream)
    response.append(connect)

    return Response(content=str(response), media_type="application/xml")


@web_app.websocket("/ws/{from_number}")
async def websocket_endpoint(ws: WebSocket, from_number: str):
    """
    WebSocket endpoint for real-time voice communication with Gemini
    Runs voice agent and BAML processing concurrently
    """
    await ws.accept()
    print(f"WebSocket connected for call: {from_number}")
    while True:
        msg = await ws.receive_json()
        if msg.get("event") != "start":
            await asyncio.sleep(0.01)
            continue
        stream_sid = msg["streamSid"]
        break
    print("Got stream SID")

    # Get or create session
    session = ACTIVE_SESSIONS[from_number]
    caller_data = USER_SESSIONS.get(from_number)
    if caller_data:
        session.renter_profile = caller_data
    send_twililo_queue: asyncio.Queue[gt.Part] = asyncio.Queue()
    user_interrupt = asyncio.Event()
    end_call = asyncio.Event()
    try:
        async for gs in start_gemini_session():
            await asyncio.gather(
                baml_processing_loop(session, end_call),
                send_to_twilio(
                    ws,
                    stream_sid,
                    end_call,
                    user_interrupt,
                    send_twililo_queue,
                ),
                forward_audio_to_gemini(
                    ws,
                    gs,
                    end_call,
                ),
                receive_from_gemini(
                    gs,
                    session,
                    ws,
                    stream_sid,
                    user_interrupt,
                    send_twililo_queue,
                    end_call,
                ),
            )
    except BaseException as e:
        print(f"Error in WebSocket for call {from_number}: {e}")
        import traceback

        traceback.print_exc()
    finally:
        ACTIVE_SESSIONS[from_number] = session
        USER_SESSIONS[from_number] = session.renter_profile
        await session.save_profile(Path("./profiles"))
        try:
            end_call.set()
            await ws.close()
        except Exception:
            pass
        print(f"WebSocket closed for call: {from_number}")


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini"),
        modal.Secret.from_name("twilio-credentials"),
        modal.Secret.from_name("modal"),
    ],
    volumes={"/profiles": volume},
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def fastapi_app():
    """Modal ASGI app wrapper for FastAPI"""
    return web_app


@app.function(
    image=vllm_server.vllm_image.uv_sync().add_local_python_source(*PYTHON_SOURCES),
    gpu=f"{vllm_server.GPU}:{vllm_server.N_GPU}",
    # how long should we stay up with no requests?
    scaledown_window=15 * vllm_server.MINUTES,
    volumes={
        "/root/.cache/huggingface": vllm_server.hf_cache_vol,
        "/root/.cache/vllm": vllm_server.vllm_cache_vol,
    },
    secrets=[
        modal.Secret.from_name("gemini"),
        modal.Secret.from_name("twilio-credentials"),
        modal.Secret.from_name("modal"),
        modal.Secret.from_name("huggingface"),
    ],
)
@modal.concurrent(max_inputs=100)
@modal.web_server(port=vllm_server.VLLM_PORT, startup_timeout=5 * vllm_server.MINUTES)
def serve():
    import subprocess

    cmd = [
        "vllm",
        "serve",
        "--uvicorn-log-level=info",
        vllm_server.MODEL_NAME,
        "--revision",
        vllm_server.MODEL_REVISION,
        "--host",
        "0.0.0.0",
        "--port",
        str(vllm_server.VLLM_PORT),
        "--enforce-eager",
        "--max-num-seqs",
        "16",
        "--max-model-len",
        "40000",
        "--api-key",
        vllm_server.API_KEY,
    ]

    subprocess.Popen(" ".join(cmd), shell=True)


if __name__ == "__main__":
    # For local development
    import uvicorn

    uvicorn.run(web_app, host="0.0.0.0", port=8000)
