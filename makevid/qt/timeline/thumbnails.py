"""Thumbnails Qt - Cache de thumbnails e GIF frames para clips."""

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer


class ThumbnailCache:
    """Gerencia cache de thumbnails e frames de GIF para clips."""

    def __init__(self):
        self._thumbs: Dict[str, QPixmap] = {}  # clip_id -> pixmap
        self._gif_frames: Dict[str, List[QPixmap]] = {}  # clip_id -> [pixmaps]
        self._max_gif_frames = 8

    def get_thumb(self, clip, width, height) -> Optional[QPixmap]:
        """Retorna thumbnail do clip (primeiro frame). Cache."""
        key = f"{clip.id}_{width}_{height}"
        if key in self._thumbs:
            return self._thumbs[key]

        if not clip.video_path or not Path(clip.video_path).exists():
            return None

        # Tentar carregar .png com mesmo nome primeiro (mais confiavel)
        try:
            png_path = Path(clip.video_path).with_suffix(".png")
            if png_path.exists():
                pixmap = QPixmap(str(png_path)).scaled(
                    width, height, aspectMode=1, mode=1)
                if not pixmap.isNull():
                    self._thumbs[key] = pixmap
                    return pixmap
        except Exception:
            pass

        # Tentar ler via cv2
        try:
            import cv2
            cap = cv2.VideoCapture(str(clip.video_path))
            if not cap.isOpened():
                cap.release()
            else:
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    frame_rgb = frame[:, :, ::-1].copy()
                    h, w = frame_rgb.shape[:2]
                    img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(img).scaled(
                        width, height, aspectMode=1, mode=1)
                    if not pixmap.isNull():
                        self._thumbs[key] = pixmap
                        return pixmap
        except Exception:
            pass

        # Fallback: QPixmap direto (suporta alguns formatos de imagem/video)
        try:
            pixmap = QPixmap(str(clip.video_path)).scaled(
                width, height, aspectMode=1, mode=1)
            if not pixmap.isNull():
                self._thumbs[key] = pixmap
                return pixmap
        except Exception:
            pass

        return None

    def get_gif_frames(self, clip, width, height) -> List[QPixmap]:
        """Retorna lista de frames para animação GIF. Cache."""
        key = f"{clip.id}_{width}_{height}"
        if key in self._gif_frames:
            return self._gif_frames[key]

        if not clip.video_path or not Path(clip.video_path).exists():
            return []

        try:
            import cv2
            cap = cv2.VideoCapture(str(clip.video_path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total <= 0:
                cap.release()
                return []

            step = max(1, total // self._max_gif_frames)
            frames = []
            for i in range(0, total, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    frame_rgb = frame[:, :, ::-1].copy()
                    h, w = frame_rgb.shape[:2]
                    img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(img).scaled(
                        width, height, aspectMode=1, mode=1)
                    frames.append(pixmap)
                if len(frames) >= self._max_gif_frames:
                    break
            cap.release()

            self._gif_frames[key] = frames
            return frames
        except Exception:
            return []

    def invalidate(self, clip_id):
        """Limpa cache de um clip."""
        keys_to_remove = [k for k in self._thumbs if k.startswith(clip_id)]
        for k in keys_to_remove:
            del self._thumbs[k]
        keys_to_remove = [k for k in self._gif_frames if k.startswith(clip_id)]
        for k in keys_to_remove:
            del self._gif_frames[k]
