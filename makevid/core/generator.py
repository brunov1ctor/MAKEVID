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
    lora_path: Optional[str] = None,
) -> VideoResult:
    """Text-to-Video."""
    model_key = "wan_t2v_cpu" if force_cpu else "wan_t2v"
    pipe = model_manager.get(model_key)

    if lora_path:
        from makevid.core.lora_trainer import load_lora_into_pipeline
        pipe = load_lora_into_pipeline(pipe, lora_path)

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
    """Image-to-Video."""
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
# LTX VIDEO 2.3 (Text-to-Video)
# ============================================================

def generate_ltx(
    model_manager,
    prompt: str,
    num_frames: int = 97,
    height: int = 480,
    width: int = 832,
    steps: int = 30,
    guidance: float = 3.0,
    seed: Optional[int] = None,
    fps: int = 24,
    negative_prompt: str = NEGATIVE_PROMPT,
    callback=None,
) -> VideoResult:
    """LTX Video 2.3 - Text-to-Video."""
    pipe = model_manager.get("ltx_video")
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0

    if callback:
        callback(f"Gerando {num_frames} frames (LTX Video)...")

    output = pipe(
        prompt=prompt,
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
# CONTROLNET (Motion-guided generation)
# ============================================================

def generate_with_controlnet(
    model_manager,
    prompt: str,
    control_frames: List[Image.Image],
    control_type: str = "pose",
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
    """Gera video guiado por frames de controle (pose/depth)."""
    gen = _make_gen(seed)
    actual_seed = gen.initial_seed() if gen else 0

    if callback:
        callback(f"ControlNet ({control_type}): {len(control_frames)} frames...")

    # Estrategia: usar img2img com control image como guia
    # O control frame eh mesclado com ruido para guiar a composicao
    try:
        from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel
        from makevid.config import MODELS_DIR

        controlnet_ids = {
            "pose": "thibaud/controlnet-openpose-sdxl-1.0",
            "depth": "diffusers/controlnet-depth-sdxl-1.0-small",
        }
        cn_id = controlnet_ids.get(control_type, controlnet_ids["pose"])

        if callback:
            callback(f"Carregando ControlNet ({control_type})...")

        controlnet = ControlNetModel.from_pretrained(
            cn_id, torch_dtype=torch.float16, cache_dir=str(MODELS_DIR))
        pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            controlnet=controlnet,
            torch_dtype=torch.float16,
            cache_dir=str(MODELS_DIR))
        pipe.enable_model_cpu_offload()

        frames = []
        total = len(control_frames)
        for i, ctrl_img in enumerate(control_frames):
            ctrl_img = ctrl_img.resize((width, height), Image.LANCZOS)
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=ctrl_img,
                num_inference_steps=min(steps, 20),
                guidance_scale=guidance,
                generator=gen,
                controlnet_conditioning_scale=0.7,
            ).images[0]
            frames.append(result)
            if callback and (i + 1) % 5 == 0:
                callback(f"ControlNet: frame {i+1}/{total}")

        return VideoResult(frames=frames, fps=fps, seed=actual_seed, duration=len(frames) / fps)

    except ImportError:
        # Fallback: usar control frames como base para img2img simples
        if callback:
            callback("ControlNet nao disponivel, usando I2V com primeiro frame...")
        return generate_i2v(model_manager, prompt, control_frames[0],
                           num_frames=num_frames, steps=steps, guidance=guidance,
                           seed=seed, fps=fps, negative_prompt=negative_prompt, callback=callback)



