import audioop
import numpy as np
import asyncio
import time
from utils import chunk_mulaw_20ms
import base64
from fastapi import WebSocket


async def send_to_twilio(
    ws: WebSocket,
    stream_sid: str,
    end_call: asyncio.Event,
    user_interrupt: asyncio.Event,
    send_twililo_queue: asyncio.Queue,
):
    while True and not end_call.is_set():
        if user_interrupt.is_set():
            await asyncio.sleep(0.05)
            continue
        part = await send_twililo_queue.get()
        if not part.inline_data or not part.inline_data.data:
            continue
        mime = part.inline_data.mime_type or ""
        if not mime.startswith("audio/"):
            continue

        # Convert Gemini 24 kHz PCM → 8 kHz PCM → μ-law
        pcm24 = np.frombuffer(part.inline_data.data, dtype=np.int16)
        pcm8 = pcm24[::3].tobytes()
        mulaw = audioop.lin2ulaw(pcm8, 2)

        # ---- Frame into 20 ms chunks for Twilio ----
        last_send = time.perf_counter()
        for frame in chunk_mulaw_20ms(mulaw):
            if user_interrupt.is_set():
                # stop mid-playback immediately
                break
            now = time.perf_counter()
            delta = now - last_send
            if delta < 0.02:  # noqa
                await asyncio.sleep(0.02 - delta)
            b64_audio = base64.b64encode(frame).decode("ascii")
            await ws.send_json(
                {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": b64_audio},
                }
            )
