"""ControlNet Service - Controle de movimento por video de referencia.

Permite importar um video de referencia, extrair poses/depth,
e usar como guia na geracao de video.
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Callable, List

import numpy as np
from PIL import Image

from makevid.config import MODELS_DIR, OUTPUTS_DIR

logger = logging.getLogger(__name__)


class ControlNetService:
    """Extrai controles de movimento e aplica na geracao."""

    def __init__(self):
        self._pose_model = None
        self._depth_model = None

    def extract_poses(
        self,
        video_path: str,
        output_dir: str,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Extrai esqueletos de pose de cada frame do video.

        Args:
            video_path: Video de referencia de movimento
            output_dir: Pasta para salvar frames de pose
            on_done: Callback com lista de paths dos frames de pose
        """
        def run():
            try:
                import cv2
                self._ensure_pose_model()

                cap = cv2.VideoCapture(video_path)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)

                pose_frames = []
                idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    pose_img = self._extract_pose_frame(frame)
                    path = out / f"pose_{idx:04d}.png"
                    Image.fromarray(pose_img).save(str(path))
                    pose_frames.append(str(path))
                    idx += 1
                    if on_progress and idx % 10 == 0:
                        on_progress(f"Poses: {idx}/{total}")

                cap.release()

                if on_done:
                    on_done(pose_frames, fps)

            except Exception as e:
                logger.error(f"Pose extraction error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def extract_depth(
        self,
        video_path: str,
        output_dir: str,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Extrai mapa de profundidade de cada frame.

        Args:
            video_path: Video de referencia
            output_dir: Pasta para salvar depth maps
            on_done: Callback com lista de paths
        """
        def run():
            try:
                import cv2
                self._ensure_depth_model()

                cap = cv2.VideoCapture(video_path)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)

                depth_frames = []
                idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    depth_img = self._extract_depth_frame(frame[:, :, ::-1])
                    path = out / f"depth_{idx:04d}.png"
                    Image.fromarray(depth_img).save(str(path))
                    depth_frames.append(str(path))
                    idx += 1
                    if on_progress and idx % 10 == 0:
                        on_progress(f"Depth: {idx}/{total}")

                cap.release()

                if on_done:
                    on_done(depth_frames, fps)

            except Exception as e:
                logger.error(f"Depth extraction error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _ensure_pose_model(self):
        """Carrega modelo de pose (MediaPipe ou OpenPose)."""
        if self._pose_model is not None:
            return
        try:
            import mediapipe as mp
            self._pose_model = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5)
            self._mp_draw = mp.solutions.drawing_utils
            self._mp_pose = mp.solutions.pose
            logger.info("MediaPipe Pose carregado")
        except ImportError:
            raise ImportError("mediapipe nao instalado. Execute: pip install mediapipe")

    def _ensure_depth_model(self):
        """Carrega modelo de depth (MiDaS)."""
        if self._depth_model is not None:
            return
        try:
            import torch
            self._depth_model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
            self._depth_model.eval()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._depth_model.to(device)
            self._depth_device = device

            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self._depth_transform = midas_transforms.small_transform
            logger.info(f"MiDaS depth carregado em {device}")
        except Exception as e:
            raise ImportError(f"MiDaS nao disponivel: {e}\nExecute: pip install timm")

    def _extract_pose_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Extrai esqueleto de pose de um frame BGR."""
        import cv2
        frame_rgb = frame_bgr[:, :, ::-1]
        h, w = frame_rgb.shape[:2]
        result = self._pose_model.process(frame_rgb)

        # Canvas preto com esqueleto
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        if result.pose_landmarks:
            self._mp_draw.draw_landmarks(
                canvas, result.pose_landmarks, self._mp_pose.POSE_CONNECTIONS,
                self._mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                self._mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2))
        return canvas

    def _extract_depth_frame(self, frame_rgb: np.ndarray) -> np.ndarray:
        """Extrai depth map de um frame RGB."""
        import torch
        import cv2

        input_batch = self._depth_transform(frame_rgb).to(self._depth_device)
        with torch.no_grad():
            prediction = self._depth_model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=frame_rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth = prediction.cpu().numpy()
        # Normalizar para 0-255
        depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8) * 255
        return depth.astype(np.uint8)
