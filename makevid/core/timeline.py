"""Timeline - concatena clips em video longo final."""

import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from PIL import Image
import numpy as np


def concat_clips(clip_paths: List[str | Path], output_path: str | Path, fps: int = 16) -> Path:
    """Concatena multiplos videos em um unico video longo."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    valid_paths = [Path(p) for p in clip_paths if Path(p).exists()]
    if not valid_paths:
        raise ValueError("Nenhum clip valido para concatenar")

    if len(valid_paths) == 1:
        shutil.copy(valid_paths[0], output_path)
        return output_path

    if shutil.which("ffmpeg"):
        return _concat_ffmpeg(valid_paths, output_path)
    else:
        return _concat_opencv(valid_paths, output_path, fps)


def _concat_ffmpeg(paths: List[Path], output_path: Path) -> Path:
    """Concatena via FFmpeg (melhor qualidade)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in paths:
            f.write(f"file '{p.resolve()}'\n")
        list_file = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=600)
    Path(list_file).unlink(missing_ok=True)
    return output_path


def _concat_opencv(paths: List[Path], output_path: Path, fps: int) -> Path:
    """Fallback: concatena via OpenCV."""
    import cv2

    # Ler primeiro frame para pegar dimensoes
    cap = cv2.VideoCapture(str(paths[0]))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    for path in paths:
        cap = cv2.VideoCapture(str(path))
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Resize se necessario
            if frame.shape[1] != w or frame.shape[0] != h:
                frame = cv2.resize(frame, (w, h))
            writer.write(frame)
        cap.release()

    writer.release()
    return output_path


def get_video_duration(path: str | Path) -> float:
    """Retorna duracao de um video em segundos."""
    path = Path(path)
    if not path.exists():
        return 0.0

    if shutil.which("ffprobe"):
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass

    # Fallback opencv
    try:
        import cv2
        cap = cv2.VideoCapture(str(path))
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if fps > 0:
            return frames / fps
    except ImportError:
        pass

    return 0.0


def get_thumbnail(video_path: str | Path, size: tuple = (160, 90)) -> Optional[Image.Image]:
    """Extrai primeiro frame como thumbnail."""
    try:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.thumbnail(size)
            return img
    except ImportError:
        pass
    return None
