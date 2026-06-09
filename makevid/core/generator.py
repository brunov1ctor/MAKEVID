"""Video Generator - T2V, I2V, VACE, V2V. Mock mode sem GPU."""

import time
import logging
from typing import Optional, List
from dataclasses import dataclass

import torch
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

NEGATIVE_PROMPT = (
    "blurry, low quality, distorted, deformed, watermark, text, "
    "static, frozen, flickering, oversaturated"
)


# ============================================================
# DATA
# ============================================================

@dataclass
class VideoResult:
    frames: List[Image.Image]
    fps: int
    seed: int
    duration: float


# ============================================================
# UTILS
# ============================================================

def is_gpu_available() -> bool:
    return torch.cuda.is_available()


def _make_gen(seed: Optional[int]) -> Optional[torch.Generator]:
    if seed is None:
        return None
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)
    return g


def _step_callback(callback, steps):
    """Cria callback para mostrar tempo restante por step."""
    start = [time.time()]

    def on_step(pipe_obj, step, timestep, kwargs):
        elapsed = time.time() - start[0]
        if step > 0 and callback:
            per_step = elapsed / step
            remaining = per_step * (steps - step)
            m, s = int(remaining) // 60, int(remaining) % 60
            callback(f"Step {step}/{steps} | Falta ~{m:02d}:{s:02d}")
        return kwargs

    return on_step


# ============================================================
# TEXT-TO-VIDEO
# ============================================================

def generate_t2v(
    model_manager,
    prompt: str,
    num_frames: int = 81,
    height: int = 480,
    width: int = 832,
    steps: int = 30,
    guidance: float = 5.0,
    seed: Optional[int] = None,
    fps: int = 16,
    negative_prompt: str = NEGATIVE_PROMPT,
    callback=None,
    force_cpu: bool = False,
) -> VideoResult:
    """Text-to-Video. Usa mock se nao tem GPU e force_cpu=False."""
    if not is_gpu_available() and not force_cpu:
        return _mock_generate(prompt, num_frames, width, height, fps, seed, callback)

    model_key = "wan_t2v_cpu" if force_cpu else "wan_t2v"
    pipe = model_manager.get(model_key)
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0

    if callback:
        callback(f"Gerando {num_frames} frames ({'CPU' if force_cpu else 'GPU'})...")

    output = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_frames=num_frames,
        height=height,
        width=width,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
        callback_on_step_end=_step_callback(callback, steps),
    )

    frames = output.frames[0]
    return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)


# ============================================================
# IMAGE-TO-VIDEO
# ============================================================

def generate_i2v(
    model_manager,
    prompt: str,
    image: Image.Image,
    num_frames: int = 81,
    steps: int = 30,
    guidance: float = 5.0,
    seed: Optional[int] = None,
    fps: int = 16,
    negative_prompt: str = NEGATIVE_PROMPT,
    callback=None,
    last_image: Optional[Image.Image] = None,
) -> VideoResult:
    """Image-to-Video. last_image permite video extend (interpolacao)."""
    if not is_gpu_available():
        return _mock_generate(prompt, num_frames, image.size[0], image.size[1], fps, seed, callback, base_image=image)

    pipe = model_manager.get("wan_i2v")
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0

    max_area = 480 * 832
    w, h = image.size
    scale = (max_area / (w * h)) ** 0.5
    new_w = int(w * scale) // 16 * 16
    new_h = int(h * scale) // 16 * 16
    image = image.resize((new_w, new_h), Image.LANCZOS)

    if callback:
        callback("Gerando frames (I2V)...")

    kwargs = dict(
        prompt=prompt,
        image=image,
        negative_prompt=negative_prompt,
        num_frames=num_frames,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
    )
    if last_image is not None:
        kwargs["last_image"] = last_image.resize((new_w, new_h), Image.LANCZOS)

    output = pipe(**kwargs)
    frames = output.frames[0]
    return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)


# ============================================================
# TEXT+IMAGE TO VIDEO (Wan 2.2)
# ============================================================

def generate_ti2v(
    model_manager,
    prompt: str,
    image: Image.Image,
    num_frames: int = 81,
    height: int = 480,
    width: int = 832,
    steps: int = 30,
    guidance: float = 5.0,
    seed: Optional[int] = None,
    fps: int = 16,
    negative_prompt: str = NEGATIVE_PROMPT,
    callback=None,
) -> VideoResult:
    """Text+Image to Video com Wan 2.2 TI2V 5B."""
    if not is_gpu_available():
        return _mock_generate(prompt, num_frames, width, height, fps, seed, callback, base_image=image)

    pipe = model_manager.get("wan22_ti2v")
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0
    image = image.resize((width, height), Image.LANCZOS)

    if callback:
        callback("Gerando frames (Wan 2.2 TI2V)...")

    output = pipe(
        prompt=prompt,
        image=image,
        negative_prompt=negative_prompt,
        num_frames=num_frames,
        height=height,
        width=width,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
    )

    frames = output.frames[0]
    return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)


# ============================================================
# VACE (Reference Images - consistencia de personagem)
# ============================================================

def generate_vace(
    model_manager,
    prompt: str,
    reference_images: List[Image.Image],
    num_frames: int = 81,
    height: int = 480,
    width: int = 832,
    steps: int = 30,
    guidance: float = 5.0,
    seed: Optional[int] = None,
    fps: int = 16,
    negative_prompt: str = NEGATIVE_PROMPT,
    callback=None,
) -> VideoResult:
    """VACE - Video com reference images para consistencia de personagem."""
    if not is_gpu_available():
        return _mock_generate(prompt, num_frames, width, height, fps, seed, callback,
                              base_image=reference_images[0] if reference_images else None)

    pipe = model_manager.get("wan_vace")
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0
    refs = [img.resize((width, height), Image.LANCZOS) for img in reference_images]

    if callback:
        callback(f"Gerando com {len(refs)} referencia(s) (VACE)...")

    output = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        reference_images=refs,
        num_frames=num_frames,
        height=height,
        width=width,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
    )

    frames = output.frames[0]
    return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)


# ============================================================
# VIDEO-TO-VIDEO (Refinamento)
# ============================================================

def generate_v2v(
    model_manager,
    prompt: str,
    video_frames: List[Image.Image],
    strength: float = 0.6,
    steps: int = 30,
    guidance: float = 5.0,
    seed: Optional[int] = None,
    fps: int = 16,
    negative_prompt: str = NEGATIVE_PROMPT,
    callback=None,
) -> VideoResult:
    """Video-to-Video - Re-estiliza video existente. strength 0=identico, 1=novo."""
    if not is_gpu_available():
        return _mock_generate(prompt, len(video_frames),
                              video_frames[0].size[0], video_frames[0].size[1],
                              fps, seed, callback, base_image=video_frames[0])

    pipe = model_manager.get("wan_v2v")
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0

    if callback:
        callback(f"Refinando video (strength={strength:.1f})...")

    output = pipe(
        video=video_frames,
        prompt=prompt,
        negative_prompt=negative_prompt,
        strength=strength,
        num_inference_steps=steps,
        guidance_scale=guidance,
        generator=gen,
    )

    frames = output.frames[0]
    return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)


# ============================================================
# MOCK (desenvolvimento sem GPU)
# ============================================================

def _mock_generate(
    prompt: str,
    num_frames: int,
    width: int,
    height: int,
    fps: int,
    seed: Optional[int],
    callback=None,
    base_image: Optional[Image.Image] = None,
) -> VideoResult:
    """Gera video placeholder para desenvolvimento sem GPU."""
    if callback:
        callback("[MOCK] Gerando video de teste...")

    actual_seed = seed or int(time.time()) % 100000
    np.random.seed(actual_seed)

    frames = []
    for i in range(num_frames):
        if base_image:
            frame = base_image.copy().resize((width, height))
        else:
            t = i / num_frames
            r = int(40 + 60 * np.sin(t * 3.14))
            g = int(40 + 40 * np.cos(t * 2.5))
            b = int(80 + 80 * t)
            arr = np.full((height, width, 3), [r, g, b], dtype=np.uint8)
            noise = np.random.randint(-10, 10, (height, width, 3), dtype=np.int16)
            arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            frame = Image.fromarray(arr)

        draw = ImageDraw.Draw(frame)
        draw.rectangle([(10, height - 70), (width - 10, height - 10)], fill=(0, 0, 0, 180))
        draw.text((20, height - 60), f"[MOCK] Frame {i+1}/{num_frames}", fill=(255, 255, 255))
        draw.text((20, height - 35), prompt[:60], fill=(200, 200, 200))
        bar_w = int((i / num_frames) * (width - 40))
        draw.rectangle([(20, height - 75), (20 + bar_w, height - 72)], fill=(0, 200, 100))
        frames.append(frame)

    time.sleep(0.5)
    return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)
