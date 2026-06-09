"""Export - Presets de exportacao para game engines (Unreal, Unity, etc)."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from PIL import Image
import numpy as np


# ============================================================
# PRESETS
# ============================================================

PRESETS = {
    "unreal_mp4": {
        "label": "Unreal Engine (MP4 H.264)",
        "ext": ".mp4",
        "codec": "libx264",
        "pix_fmt": "yuv420p",
        "crf": 15,
        "preset": "slow",
        "extra": ["-movflags", "+faststart"],
    },
    "unreal_webm": {
        "label": "Unreal Engine (WebM VP9)",
        "ext": ".webm",
        "codec": "libvpx-vp9",
        "pix_fmt": "yuv420p",
        "crf": 20,
        "preset": None,
        "extra": ["-b:v", "0"],
    },
    "unreal_prores": {
        "label": "Unreal (ProRes 422 - Master)",
        "ext": ".mov",
        "codec": "prores_ks",
        "pix_fmt": "yuv422p10le",
        "crf": None,
        "preset": None,
        "extra": ["-profile:v", "2"],  # ProRes 422
    },
    "unity_mp4": {
        "label": "Unity (MP4 H.264)",
        "ext": ".mp4",
        "codec": "libx264",
        "pix_fmt": "yuv420p",
        "crf": 16,
        "preset": "slow",
        "extra": ["-movflags", "+faststart"],
    },
    "unity_webm": {
        "label": "Unity (WebM VP8)",
        "ext": ".webm",
        "codec": "libvpx",
        "pix_fmt": "yuv420p",
        "crf": 18,
        "preset": None,
        "extra": ["-b:v", "4M"],
    },
    "png_sequence": {
        "label": "Image Sequence (PNG)",
        "ext": "_frames",
        "codec": None,
        "pix_fmt": None,
        "crf": None,
        "preset": None,
        "extra": [],
    },
    "exr_sequence": {
        "label": "Image Sequence (EXR - HDR)",
        "ext": "_frames",
        "codec": None,
        "pix_fmt": None,
        "crf": None,
        "preset": None,
        "extra": [],
    },
    "alpha_webm": {
        "label": "Com Alpha (WebM VP9 RGBA)",
        "ext": ".webm",
        "codec": "libvpx-vp9",
        "pix_fmt": "yuva420p",
        "crf": 18,
        "preset": None,
        "extra": ["-b:v", "0", "-auto-alt-ref", "0"],
    },
}

RESOLUTIONS = {
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4K": (3840, 2160),
    "720p": (1280, 720),
    "480p": (832, 480),
    "Custom": None,
}

FPS_OPTIONS = [24, 30, 60]


def get_preset_names() -> List[str]:
    return [p["label"] for p in PRESETS.values()]


def get_preset_key(label: str) -> str:
    for key, val in PRESETS.items():
        if val["label"] == label:
            return key
    return "unreal_mp4"


# ============================================================
# EXPORT
# ============================================================

def export_video(
    input_path: str | Path,
    output_dir: str | Path,
    filename: str,
    preset: str = "unreal_mp4",
    resolution: tuple = (1920, 1080),
    fps: int = 30,
) -> Path:
    """
    Exporta video com preset especifico para game engine.

    Args:
        input_path: Video fonte (clip ou final concatenado)
        output_dir: Pasta de destino
        filename: Nome do arquivo sem extensao
        preset: Key do preset (ex: 'unreal_mp4')
        resolution: (width, height)
        fps: FPS de saida
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = PRESETS[preset]

    # Image sequence export
    if preset in ("png_sequence", "exr_sequence"):
        return _export_image_sequence(input_path, output_dir, filename, preset, resolution, fps)

    # Video export via FFmpeg
    ext = cfg["ext"]
    output_path = output_dir / f"{filename}{ext}"

    if not shutil.which("ffmpeg"):
        # Fallback: copiar original
        fallback = output_dir / f"{filename}.mp4"
        shutil.copy(input_path, fallback)
        return fallback

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", cfg["codec"],
        "-pix_fmt", cfg["pix_fmt"],
    ]

    if cfg["crf"] is not None:
        cmd.extend(["-crf", str(cfg["crf"])])

    if cfg["preset"]:
        cmd.extend(["-preset", cfg["preset"]])

    # Resolution
    w, h = resolution
    cmd.extend(["-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"])

    # FPS
    cmd.extend(["-r", str(fps)])

    # Extra flags
    cmd.extend(cfg["extra"])

    cmd.append(str(output_path))

    subprocess.run(cmd, capture_output=True, check=True, timeout=600)
    return output_path


def _export_image_sequence(
    input_path: Path,
    output_dir: Path,
    filename: str,
    preset: str,
    resolution: tuple,
    fps: int,
) -> Path:
    """Exporta como sequencia de frames (PNG ou EXR)."""
    frames_dir = output_dir / f"{filename}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    ext = "png" if preset == "png_sequence" else "exr"
    w, h = resolution

    if shutil.which("ffmpeg"):
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={fps}",
            str(frames_dir / f"frame_%06d.{ext}"),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=600)
    else:
        # Fallback opencv
        import cv2
        cap = cv2.VideoCapture(str(input_path))
        i = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (w, h))
            cv2.imwrite(str(frames_dir / f"frame_{i:06d}.{ext}"), frame)
            i += 1
        cap.release()

    return frames_dir


def export_with_alpha(
    frames: List[Image.Image],
    output_path: str | Path,
    fps: int = 30,
    resolution: tuple = (1920, 1080),
) -> Path:
    """Exporta frames com canal alpha (RGBA) como WebM VP9."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not shutil.which("ffmpeg"):
        # Fallback sem alpha
        from makevid.core.video import frames_to_mp4
        return frames_to_mp4(frames, output_path.with_suffix(".mp4"), fps=fps)

    with tempfile.TemporaryDirectory() as tmpdir:
        w, h = resolution
        for i, frame in enumerate(frames):
            # Converter para RGBA se necessario
            if frame.mode != "RGBA":
                frame = frame.convert("RGBA")
            frame = frame.resize((w, h), Image.LANCZOS)
            frame.save(Path(tmpdir) / f"{i:06d}.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(Path(tmpdir) / "%06d.png"),
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-crf", "18",
            "-b:v", "0",
            "-auto-alt-ref", "0",
            str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)

    return output_path
