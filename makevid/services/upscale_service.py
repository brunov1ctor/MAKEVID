"""Upscale Service - Refinamento em 2 estagios.

Estagio 1: Gera video em baixa resolucao (rapido)
Estagio 2: Upscale + refinamento com Real-ESRGAN ou img2img
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Callable

import numpy as np
from PIL import Image

from makevid.config import MODELS_DIR, OUTPUTS_DIR

logger = logging.getLogger(__name__)


class UpscaleService:
    """Refina video com upscale inteligente."""

    def __init__(self):
        self._model = None

    def upscale_video(
        self,
        video_path: str,
        output_path: str,
        scale: int = 2,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Upscale video frame a frame com Real-ESRGAN.

        Args:
            video_path: Video original (baixa res)
            output_path: Onde salvar video em alta res
            scale: Fator de upscale (2x ou 4x)
        """
        def run():
            try:
                import cv2
                self._ensure_model(scale)

                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                out_w, out_h = w * scale, h * scale
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    upscaled = self._upscale_frame(frame)
                    writer.write(upscaled)
                    frame_idx += 1
                    if on_progress and frame_idx % 5 == 0:
                        pct = frame_idx / max(total, 1)
                        on_progress(f"Upscale: {int(pct*100)}% ({frame_idx}/{total})")

                cap.release()
                writer.release()

                if on_done:
                    on_done(output_path)

            except Exception as e:
                logger.error(f"Upscale error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def upscale_frame(self, frame: np.ndarray, scale: int = 2) -> np.ndarray:
        """Upscale um unico frame (sincrono)."""
        self._ensure_model(scale)
        frame_bgr = frame[:, :, ::-1] if frame.shape[2] == 3 else frame
        result = self._upscale_frame(frame_bgr)
        return result[:, :, ::-1]

    def _ensure_model(self, scale: int = 2):
        """Carrega Real-ESRGAN se necessario."""
        if self._model is not None:
            return

        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            import torch

            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                           num_block=23, num_grow_ch=32, scale=scale)

            model_path = MODELS_DIR / f"RealESRGAN_x{scale}plus.pth"
            if not model_path.exists():
                # Tentar download
                self._download_model(scale, model_path)

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = RealESRGANer(
                scale=scale,
                model_path=str(model_path),
                model=model,
                tile=400,
                tile_pad=10,
                pre_pad=0,
                device=device,
            )
            logger.info(f"Real-ESRGAN x{scale} carregado em {device}")

        except ImportError:
            raise ImportError(
                "Real-ESRGAN nao instalado. Execute:\n"
                "pip install realesrgan basicsr"
            )

    def _upscale_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Aplica upscale num frame BGR."""
        output, _ = self._model.enhance(frame_bgr, outscale=self._model.scale)
        return output

    def _download_model(self, scale: int, path: Path):
        """Baixa modelo Real-ESRGAN do GitHub (URLs verificadas)."""
        import hashlib
        import urllib.request

        # URLs oficiais do repositorio Real-ESRGAN (GitHub releases)
        models = {
            2: {
                "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
                "sha256": None,  # Skip verificacao por enquanto
            },
            4: {
                "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
                "sha256": None,
            },
        }
        model_info = models.get(scale)
        if not model_info:
            raise FileNotFoundError(f"Modelo x{scale} nao disponivel (apenas 2x e 4x)")

        url = model_info["url"]
        # Validar que URL eh do dominio esperado
        if not url.startswith("https://github.com/xinntao/Real-ESRGAN/"):
            raise ValueError("URL do modelo invalida")

        logger.info(f"Baixando Real-ESRGAN x{scale} de {url}...")
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, str(path))
        logger.info(f"Modelo salvo em {path} ({path.stat().st_size / 1e6:.1f} MB)")
