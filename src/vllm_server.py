# ruff: noqa: PLC0415
# https://modal.com/docs/examples/vllm_inference
import os
import modal
from dotenv import load_dotenv

load_dotenv()

vllm_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "vllm==0.8.2",
        "transformers==4.50.3",
        "huggingface_hub[hf_transfer]==0.26.2",
        "flashinfer-python==0.2.0.post2",  # pinning, very unstable
        extra_index_url="https://flashinfer.ai/whl/cu124/torch2.5",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})  # faster model transfers
)
vllm_image = vllm_image.env({"VLLM_USE_V1": "0"})


MODELS_DIR = "/llamas"
MODEL_NAME = "google/gemma-3-4b-it"
MODEL_REVISION = "093f9f388b31de276ce2de164bdc2081324b9767"

hf_cache_vol = modal.Volume.from_name(
    "huggingface-cache", create_if_missing=True, environment_name="NE_LECTURE"
)
vllm_cache_vol = modal.Volume.from_name(
    "vllm-cache", create_if_missing=True, environment_name="NE_LECTURE"
)

app = modal.App(
    "gemma-3-4b-it",
    secrets=[modal.Secret.from_name("huggingface", required_keys=["HF_TOKEN"])],
)

GPU = "A100"
N_GPU = 1
API_KEY = os.environ["VLLM_API_KEY"]

MINUTES = 60  # seconds
VLLM_PORT = 8000
