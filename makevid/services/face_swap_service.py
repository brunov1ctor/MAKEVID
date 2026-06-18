"""Face Swap Service - Consistencia de rosto entre clips.

Usa InsightFace + inswapper para manter o mesmo rosto em todos os clips.
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Callable, List

import numpy as np
from PIL import Image

from makevid.config import MODELS_DIR

logger = logging.getLogger(__name__)


class FaceSwapService:
    """Aplica face swap para manter consistencia de personagem."""

    def __init__(self):
        self._analyzer = None
        self._swapper = None

    def swap_face_in_frame(
        self,
        frame: np.ndarray,
        reference_face: np.ndarray,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Troca rosto no frame pelo rosto de referencia.

        Args:
            frame: RGB (H, W, 3)
            reference_face: RGB da face de referencia (crop do rosto)
            on_done: Callback com frame resultante
        """
        try:
            self._ensure_models()
            result = self._do_swap(frame, reference_face)
            if on_done:
                on_done(result)
        except Exception as e:
            logger.error(f"Face swap error: {e}")
            if on_error:
                on_error(str(e))

    def swap_face_in_video(
        self,
        video_path: str,
        reference_face_path: str,
        output_path: str,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Aplica face swap em todos os frames de um video.

        Args:
            video_path: Caminho do video original
            reference_face_path: Imagem com rosto de referencia
            output_path: Onde salvar o video processado
        """
        def run():
            try:
                import cv2
                self._ensure_models()

                ref_img = np.array(Image.open(reference_face_path).convert("RGB"))
                ref_face = self._get_face(ref_img)
                if ref_face is None:
                    raise Exception("Nenhum rosto detectado na referencia")

                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_rgb = frame[:, :, ::-1]
                    result = self._do_swap(frame_rgb, ref_img)
                    writer.write(result[:, :, ::-1])
                    frame_idx += 1
                    if on_progress and frame_idx % 10 == 0:
                        on_progress(f"Face swap: {frame_idx}/{total}")

                cap.release()
                writer.release()

                if on_done:
                    on_done(output_path)

            except Exception as e:
                logger.error(f"Face swap video error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _ensure_models(self):
        """Carrega InsightFace + inswapper se necessario."""
        if self._analyzer is not None:
            return

        try:
            from insightface.app import FaceAnalysis
            from insightface.model_zoo import get_model

            self._analyzer = FaceAnalysis(name="buffalo_l",
                                          root=str(MODELS_DIR / "insightface"))
            self._analyzer.prepare(ctx_id=0, det_size=(640, 640))

            model_path = MODELS_DIR / "insightface" / "inswapper_128.onnx"
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Modelo inswapper nao encontrado em {model_path}\n"
                    "Baixe de: https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx"
                )
            self._swapper = get_model(str(model_path))
            logger.info("InsightFace + inswapper carregados")

        except ImportError:
            raise ImportError(
                "insightface nao instalado. Execute: pip install insightface onnxruntime-gpu"
            )

    def _get_face(self, img: np.ndarray):
        """Detecta face principal numa imagem."""
        faces = self._analyzer.get(img[:, :, ::-1])  # BGR para InsightFace
        if not faces:
            return None
        return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    def _do_swap(self, frame: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """Executa swap: detecta faces no frame e troca pela referencia."""
        frame_bgr = frame[:, :, ::-1]
        ref_bgr = reference[:, :, ::-1]

        target_faces = self._analyzer.get(frame_bgr)
        source_face = self._get_face(reference)

        if not target_faces or source_face is None:
            return frame

        result = frame_bgr.copy()
        for face in target_faces:
            result = self._swapper.get(result, face, source_face, paste_back=True)

        return result[:, :, ::-1]  # Volta para RGB
