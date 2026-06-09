"""Thumbnails - Cache de thumbs e animacao gif para clips na timeline."""

from tkinter import PhotoImage
from typing import Optional, Dict, List


class ThumbnailManager:
    def __init__(self):
        self._thumb_cache: Dict[str, any] = {}
        self._gif_frames: Dict[str, List] = {}

    def get_thumb(self, clip, width: int, height: int):
        """Retorna thumbnail estatica do clip no tamanho especificado."""
        if width <= 0 or height <= 0:
            return None

        cache_key = f"{clip.id}_{width}_{height}"
        if cache_key in self._thumb_cache:
            return self._thumb_cache[cache_key]

        # Limpar cache antigo deste clip
        self._thumb_cache = {k: v for k, v in self._thumb_cache.items() if not k.startswith(clip.id)}

        try:
            import cv2
            from PIL import Image, ImageTk, ImageEnhance

            cap = cv2.VideoCapture(str(clip.video_path))
            ret, frame = cap.read()
            cap.release()

            if ret:
                img = Image.fromarray(frame[:, :, ::-1])
                img = _fit_cover(img, width, height)
                img = ImageEnhance.Brightness(img).enhance(0.5)
                photo = ImageTk.PhotoImage(img)
                self._thumb_cache[cache_key] = photo
                return photo
        except Exception:
            pass
        return None

    def get_gif_frames(self, clip, width: int, height: int) -> List:
        """Retorna lista de frames para animacao. Carrega se necessario."""
        cache_key = f"{clip.id}_{width}_{height}"
        if cache_key in self._gif_frames:
            return self._gif_frames[cache_key]

        # Limpar gif antigo deste clip
        self._gif_frames = {k: v for k, v in self._gif_frames.items() if not k.startswith(clip.id)}

        try:
            import cv2
            from PIL import Image, ImageTk

            cap = cv2.VideoCapture(str(clip.video_path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total <= 0:
                cap.release()
                return []

            n = min(12, total)
            indices = [int(i * total / n) for i in range(n)]
            frames = []

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    img = Image.fromarray(frame[:, :, ::-1])
                    img = _fit_cover(img, width, height)
                    frames.append(ImageTk.PhotoImage(img))

            cap.release()
            self._gif_frames[cache_key] = frames
            return frames
        except Exception:
            self._gif_frames[cache_key] = []
            return []

    def invalidate(self, clip_id: str):
        """Remove cache de um clip."""
        self._thumb_cache = {k: v for k, v in self._thumb_cache.items() if not k.startswith(clip_id)}
        self._gif_frames = {k: v for k, v in self._gif_frames.items() if not k.startswith(clip_id)}


def _fit_cover(img, target_w: int, target_h: int):
    """Resize para preencher target (cover + crop center)."""
    from PIL import Image
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))
