import numpy as np
import audioop
from scipy import signal


def mulaw_to_pcm16k(data: bytes) -> bytes:
    """Convert 8 kHz μ-law → 16 kHz linear PCM16."""
    if not data:
        return b""

    # μ-law → PCM16 @8 kHz
    pcm8k = audioop.ulaw2lin(data, 2)

    # Resample 8kHz → 16kHz using proper anti-aliasing filter
    pcm_arr = np.frombuffer(pcm8k, dtype=np.int16)
    if pcm_arr.size == 0:
        return b""

    pcm16k = signal.resample_poly(pcm_arr, up=2, down=1)
    return pcm16k.astype(np.int16).tobytes()


def chunk_mulaw_20ms(mulaw_bytes: bytes) -> list[bytes]:
    """Split μ-law stream into 20 ms (160 byte) frames."""
    frame = 160  # 8000 samples/s * 0.02 s
    return [mulaw_bytes[i : i + frame] for i in range(0, len(mulaw_bytes), frame)]
