"""Video utils - frames para MP4. Funciona sem FFmpeg (fallback imageio)."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List
from PIL import Image
import numpy as np


def frames_to_mp4(frames: List[Image.Image], output_path: str | Path, fps: int = 16) -> Path:
    """Converte frames PIL em MP4. Usa FFmpeg se disponivel, senao imageio."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg"):
        return _encode_ffmpeg(frames, output_path, fps)
    else:
        return _encode_imageio(frames, output_path, fps)


def _encode_ffmpeg(frames: List[Image.Image], output_path: Path, fps: int) -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, frame in enumerate(frames):
            frame.save(Path(tmpdir) / f"{i:06d}.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(Path(tmpdir) / "%06d.png"),
            "-c:v", "libx264",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)

    return output_path


def _encode_imageio(frames: List[Image.Image], output_path: Path, fps: int) -> Path:
    """Fallback: salva como .avi via opencv ou .gif se nada disponivel."""
    try:
        import cv2

        h, w = np.array(frames[0]).shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # opencv precisa extensao .avi ou .mp4
        out_str = str(output_path)
        writer = cv2.VideoWriter(out_str, fourcc, fps, (w, h))

        for frame in frames:
            arr = np.array(frame)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            writer.write(bgr)

        writer.release()
        return output_path

    except ImportError:
        # Ultimo fallback: salvar como GIF
        gif_path = output_path.with_suffix(".gif")
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0,
        )
        return gif_path
