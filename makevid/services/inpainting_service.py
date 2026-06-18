"""Inpainting Service - Edicao por regiao (Angelo-style).

Permite selecionar uma area do frame e regenerar apenas aquela regiao.
Providers: Flux Fill (HF API), SDXL Inpaint (local).
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Tuple

import numpy as np
from PIL import Image

from makevid.config import OUTPUTS_DIR

logger = logging.getLogger(__name__)


class InpaintingService:
    """Regenera regioes selecionadas de um frame."""

    def inpaint_region(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
        prompt: str,
        project_id: str,
        engine: str = "hf_flux_fill",
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Regenera regiao mascarada do frame em background.

        Args:
            frame: RGB numpy array (H, W, 3)
            mask: Binary mask (H, W) - 255 = regiao a regenerar
            prompt: Descricao do que gerar na regiao
            project_id: ID do projeto para salvar resultado
            engine: Provider a usar (hf_flux_fill, sdxl_inpaint)
            on_done: Callback com frame resultante (np.ndarray)
        """
        def run():
            try:
                if on_progress:
                    on_progress("Preparando inpainting...")

                if engine == "hf_flux_fill":
                    result = self._inpaint_hf(frame, mask, prompt, on_progress)
                else:
                    result = self._inpaint_local(frame, mask, prompt, on_progress)

                if result is not None and on_done:
                    on_done(result)
                elif on_error:
                    on_error("Inpainting falhou")

            except Exception as e:
                logger.error(f"Inpainting error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _inpaint_hf(self, frame: np.ndarray, mask: np.ndarray, prompt: str, on_progress) -> Optional[np.ndarray]:
        """Inpainting via HuggingFace API (Flux Fill)."""
        import requests
        import os
        import io
        import base64

        if on_progress:
            on_progress("Enviando para Flux Fill API...")

        token = os.environ.get("HF_TOKEN", "")
        if not token:
            from makevid.core.hf_api import _get_token
            token = _get_token() or ""
        if not token:
            raise Exception("HF_TOKEN nao configurado. Configure em Engine > HuggingFace API.")

        # Preparar imagem e mascara
        img = Image.fromarray(frame)
        mask_img = Image.fromarray(mask).convert("L")

        # Encode
        buf_img = io.BytesIO()
        img.save(buf_img, format="PNG")
        buf_mask = io.BytesIO()
        mask_img.save(buf_mask, format="PNG")

        url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-Fill-dev"
        headers = {"Authorization": f"Bearer {token}"}

        # Multipart form
        files = {
            "image": ("image.png", buf_img.getvalue(), "image/png"),
            "mask": ("mask.png", buf_mask.getvalue(), "image/png"),
        }
        data = {"prompt": prompt}

        if on_progress:
            on_progress("Gerando regiao...")

        r = requests.post(url, headers=headers, files=files, data=data, timeout=120)

        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            result_img = Image.open(io.BytesIO(r.content)).convert("RGB")
            return np.array(result_img)

        raise Exception(f"API retornou {r.status_code}: {r.text[:100]}")

    def _inpaint_local(self, frame: np.ndarray, mask: np.ndarray, prompt: str, on_progress) -> Optional[np.ndarray]:
        """Inpainting local via diffusers (SDXL Inpaint)."""
        import torch
        from diffusers import StableDiffusionXLInpaintPipeline
        from makevid.config import MODELS_DIR

        if on_progress:
            on_progress("Carregando modelo inpaint...")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=dtype,
            cache_dir=str(MODELS_DIR),
        )
        if device == "cuda":
            pipe.enable_model_cpu_offload()

        img = Image.fromarray(frame).resize((1024, 1024))
        mask_img = Image.fromarray(mask).convert("L").resize((1024, 1024))

        if on_progress:
            on_progress("Gerando regiao...")

        result = pipe(
            prompt=prompt,
            image=img,
            mask_image=mask_img,
            num_inference_steps=20,
        ).images[0]

        # Resize back
        result = result.resize((frame.shape[1], frame.shape[0]))
        return np.array(result)
