"""HuggingFace API Generator - gera video via API gratuita (T2V e I2V)."""

import os
import requests
import tempfile
import base64
import time
import io
import logging
from pathlib import Path
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

HF_API_URL = "https://router.huggingface.co/hf-inference/models/"

MODELS_T2V = {
    "wan": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
    "ltx": "Lightricks/LTX-Video",
}

MODELS_I2V = {
    "wan": "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
}


def _image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _get_token() -> str:
    """Busca token do HF da variavel de ambiente."""
    return os.environ.get("HF_TOKEN", "")


def generate_t2v(
    prompt: str,
    token: str = "",
    model: str = "wan",
    callback=None,
) -> Optional[Path]:
    """Text-to-Video via HF API."""
    model_id = MODELS_T2V.get(model, MODELS_T2V["wan"])
    url = f"{HF_API_URL}{model_id}"

    actual_token = token or _get_token()
    headers = {"Content-Type": "application/json"}
    if actual_token:
        headers["Authorization"] = f"Bearer {actual_token}"

    payload = {"inputs": prompt}

    return _send_request(url, headers, payload, callback)


def generate_i2v(
    prompt: str,
    image: Image.Image,
    token: str = "",
    model: str = "wan",
    callback=None,
) -> Optional[Path]:
    """Image-to-Video via HF API. Envia imagem como base64."""
    model_id = MODELS_I2V.get(model, MODELS_I2V["wan"])
    url = f"{HF_API_URL}{model_id}"

    actual_token = token or _get_token()
    headers = {"Content-Type": "application/json"}
    if actual_token:
        headers["Authorization"] = f"Bearer {actual_token}"

    # Resize imagem para nao estourar payload
    image.thumbnail((512, 512))
    img_b64 = _image_to_base64(image)

    payload = {
        "inputs": {
            "prompt": prompt,
            "image": img_b64,
        }
    }

    return _send_request(url, headers, payload, callback)


def _send_request(url: str, headers: dict, payload: dict, callback=None) -> Optional[Path]:
    """Envia request e retorna path do video ou None."""
    if callback:
        callback("Enviando para HuggingFace...")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=300)

            if response.status_code == 503:
                wait = response.json().get("estimated_time", 60)
                if callback:
                    callback(f"Modelo carregando... aguarde ~{int(wait)}s (tentativa {attempt+1})")
                time.sleep(min(wait, 60))
                continue

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "video" in content_type or "octet" in content_type or len(response.content) > 10000:
                    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                    tmp.write(response.content)
                    tmp.close()
                    if callback:
                        callback("Video recebido!")
                    return Path(tmp.name)
                else:
                    if callback:
                        callback("Resposta inesperada da API")
                    return None

            else:
                try:
                    error = response.json().get("error", "")
                except Exception:
                    error = response.text[:100]
                if callback:
                    callback(f"Erro {response.status_code}: {error[:80]}")
                return None

        except requests.exceptions.Timeout:
            if callback:
                callback(f"Timeout (tentativa {attempt+1}/{max_retries})")
            continue
        except Exception as e:
            if callback:
                callback(f"Erro: {str(e)[:80]}")
            return None

    if callback:
        callback("Falhou apos todas tentativas")
    return None
