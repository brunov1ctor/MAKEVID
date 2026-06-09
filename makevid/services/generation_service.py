"""Generation Service - Orquestra geracao de video entre UI e Core."""

import logging
import threading
from pathlib import Path
from typing import Optional, List, Callable
from PIL import Image

from makevid.config import OUTPUTS_DIR, MODELS_DIR
from makevid.core.logger import log_generation

logger = logging.getLogger(__name__)


class GenerationService:
    def __init__(self):
        self._model_manager = None

    def _get_mm(self):
        if self._model_manager is None:
            from makevid.core.models import ModelManager
            self._model_manager = ModelManager(cache_dir=MODELS_DIR)
        return self._model_manager

    def generate_clip(
        self,
        project_id: str,
        clip_id: str,
        prompt: str,
        engine: str,
        duration: float = 5.0,
        steps: int = 30,
        guidance: float = 5.0,
        seed: Optional[int] = None,
        width: int = 832,
        height: int = 480,
        fps: int = 16,
        negative_prompt: str = "",
        ref_images: Optional[List[str]] = None,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Gera clip em background thread. Callbacks sao chamados na thread."""

        # Auto-injetar ref_image de personagem se detectado no prompt
        if not ref_images:
            ref_images = self._get_character_ref_images(prompt)

        def run():
            try:
                import re
                safe_name = re.sub(r'[^\w\s-]', '', prompt)[:50].strip().replace(' ', '_')
                if not safe_name:
                    safe_name = f"clip_{clip_id}"
                out_path = OUTPUTS_DIR / project_id / f"{safe_name}.mp4"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                if out_path.exists():
                    out_path = OUTPUTS_DIR / project_id / f"{safe_name}_{clip_id[:4]}.mp4"

                if on_progress:
                    on_progress("Preparando...")

                gen_params = dict(
                    prompt=prompt, ref_images=ref_images, duration=duration,
                    steps=steps, guidance=guidance, seed=seed,
                    width=width, height=height, fps=fps,
                    neg=negative_prompt, on_progress=on_progress
                )

                # Dispatch por engine
                if engine == "HuggingFace API":
                    result_path = self._generate_hf(prompt, ref_images, on_progress)
                    if result_path and result_path.exists():
                        import shutil
                        shutil.move(str(result_path), str(out_path))
                        log_generation(prompt, engine, duration, "done")
                        if on_done:
                            on_done(str(out_path), duration, 0)
                    else:
                        log_generation(prompt, engine, 0, "error", "API nao retornou video")
                        if on_error:
                            on_error("API nao retornou video")
                    return

                # Engines locais que produzem VideoResult
                engine_dispatch = {
                    "Wan 2.2 TI2V": self._generate_wan22_ti2v,
                    "Local (CPU)": self._generate_cpu,
                    "VACE (Referencia)": self._generate_vace,
                    "V2V (Refinar)": self._generate_v2v,
                }
                gen_fn = engine_dispatch.get(engine, self._generate_local)
                result = gen_fn(**gen_params)

                from makevid.core.video import frames_to_mp4
                if on_progress:
                    on_progress("Salvando MP4...")
                frames_to_mp4(result.frames, out_path, fps=result.fps if hasattr(result, 'fps') else fps)
                log_generation(prompt, engine, result.duration, "done")
                if on_done:
                    on_done(str(out_path), result.duration, result.seed)

            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Generation failed: {e}")
                log_generation(prompt, engine, 0, "error", str(e))
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def _generate_cpu(self, prompt, ref_images, duration, steps, guidance, seed, width, height, fps, neg, on_progress, **_):
        """Gera video REAL em CPU com parametros reduzidos."""
        from makevid.core.generator import generate_t2v
        from makevid.config import CPU_MAX_FRAMES, CPU_MAX_STEPS, CPU_WIDTH, CPU_HEIGHT, CPU_FPS

        mm = self._get_mm()
        styled_prompt = self._apply_style(prompt)

        num_frames = min(CPU_MAX_FRAMES, max(9, int(duration * CPU_FPS)))
        num_frames = ((num_frames - 1) // 4) * 4 + 1
        actual_steps = min(steps, CPU_MAX_STEPS)

        if on_progress:
            on_progress(f"CPU: {num_frames}f, {CPU_WIDTH}x{CPU_HEIGHT}, {actual_steps} steps")
            on_progress("Carregando modelo (pode demorar na 1a vez)...")

        return generate_t2v(
            mm, styled_prompt,
            num_frames=num_frames,
            height=CPU_HEIGHT,
            width=CPU_WIDTH,
            steps=actual_steps,
            guidance=guidance,
            seed=seed,
            fps=CPU_FPS,
            negative_prompt=neg,
            callback=on_progress,
            force_cpu=True,
        )

    def _generate_vace(self, prompt, ref_images, duration, steps, guidance, seed, width, height, fps, neg, on_progress, **_):
        """Gera video com VACE usando reference images para consistencia."""
        from makevid.core.generator import generate_vace
        from makevid.config import PROJECTS_DIR

        mm = self._get_mm()
        styled_prompt = self._apply_style(prompt)
        raw = int(duration * fps)
        num_frames = ((raw - 1) // 4) * 4 + 1
        num_frames = max(num_frames, 17)

        # Coletar reference images: das ref_images passadas + personagens do projeto
        refs = []
        if ref_images:
            refs = [Image.open(p).convert("RGB") for p in ref_images if Path(p).exists()]

        # Adicionar references de personagens do projeto
        try:
            from makevid.core.project import Project
            project_files = list(PROJECTS_DIR.glob("*.json"))
            if project_files:
                proj = Project.load(project_files[0])
                for char in proj.characters:
                    if char.reference_image and Path(char.reference_image).exists():
                        refs.append(Image.open(char.reference_image).convert("RGB"))
        except Exception:
            pass

        if not refs:
            if on_progress:
                on_progress("VACE: sem referencia, usando T2V normal...")
            return self._generate_local(prompt, None, duration, steps, guidance, seed, width, height, fps, neg, on_progress)

        if on_progress:
            on_progress(f"VACE: {len(refs)} ref(s), {num_frames}f...")

        return generate_vace(
            mm, styled_prompt, refs,
            num_frames=num_frames,
            height=height, width=width,
            steps=steps, guidance=guidance,
            seed=seed, fps=fps,
            negative_prompt=neg,
            callback=on_progress,
        )

    def _generate_v2v(self, prompt, ref_images, duration, steps, guidance, seed, width, height, fps, neg, on_progress, **_):
        """Refina o ultimo clip na timeline com novo prompt/estilo."""
        from makevid.core.generator import generate_v2v
        from makevid.config import PROJECTS_DIR

        mm = self._get_mm()
        styled_prompt = self._apply_style(prompt)

        # Pegar frames do ultimo clip done
        video_frames = self._get_last_clip_frames()
        if not video_frames:
            if on_progress:
                on_progress("V2V: sem video anterior, usando T2V...")
            return self._generate_local(prompt, ref_images, duration, steps, guidance, seed, width, height, fps, neg, on_progress)

        if on_progress:
            on_progress(f"V2V: refinando {len(video_frames)} frames (strength=0.6)...")

        return generate_v2v(
            mm, styled_prompt, video_frames,
            strength=0.6,
            steps=steps, guidance=guidance,
            seed=seed, fps=fps,
            negative_prompt=neg,
            callback=on_progress,
        )

    def _get_last_clip_frames(self):
        """Extrai frames do ultimo clip pronto na timeline."""
        from makevid.config import PROJECTS_DIR
        try:
            from makevid.core.project import Project
            project_files = list(PROJECTS_DIR.glob("*.json"))
            if not project_files:
                return None
            proj = Project.load(project_files[0])
            clips = sorted(proj.clips, key=lambda c: c.position)
            last_done = None
            for c in reversed(clips):
                if c.status == "done" and c.video_path and Path(c.video_path).exists():
                    last_done = c
                    break
            if not last_done:
                return None

            import cv2
            cap = cv2.VideoCapture(str(last_done.video_path))
            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgb = frame[:, :, ::-1]
                frames.append(Image.fromarray(frame_rgb))
            cap.release()
            return frames if frames else None
        except Exception:
            return None

    def _apply_style(self, prompt: str) -> str:
        """Inject character descriptions ao prompt quando detectados."""
        from makevid.config import PROJECTS_DIR
        try:
            project_files = list(PROJECTS_DIR.glob("*.json"))
            if project_files:
                from makevid.core.project import Project
                proj = Project.load(project_files[0])

                # Detectar nomes de personagens no prompt e injetar descricao
                char_descriptions = []
                prompt_lower = prompt.lower()
                for char in proj.characters:
                    if char.name and char.name.lower() in prompt_lower:
                        desc = char.to_prompt()
                        if desc:
                            char_descriptions.append(f"{char.name}: {desc}")

                if char_descriptions:
                    return f"{"; ".join(char_descriptions)}, {prompt}"
        except Exception:
            pass
        return prompt

    def _get_character_ref_images(self, prompt: str) -> Optional[List[str]]:
        """Detecta personagens no prompt e retorna suas ref images se existirem."""
        from makevid.config import PROJECTS_DIR
        from pathlib import Path
        try:
            project_files = list(PROJECTS_DIR.glob("*.json"))
            if project_files:
                from makevid.core.project import Project
                proj = Project.load(project_files[0])
                prompt_lower = prompt.lower()
                refs = []
                for char in proj.characters:
                    if char.name and char.name.lower() in prompt_lower:
                        if char.reference_image and Path(char.reference_image).exists():
                            refs.append(char.reference_image)
                if refs:
                    return refs
        except Exception:
            pass
        return None

    def _generate_local(self, prompt, ref_images, duration, steps, guidance, seed, width, height, fps, neg, on_progress, **_):
        from makevid.core.generator import generate_t2v, generate_i2v, generate_ti2v

        mm = self._get_mm()
        raw = int(duration * fps)
        num_frames = ((raw - 1) // 4) * 4 + 1
        num_frames = max(num_frames, 17)

        styled_prompt = self._apply_style(prompt)

        if on_progress:
            on_progress("Gerando frames...")

        if ref_images:
            img = self._load_ref_images(ref_images)
            return generate_i2v(mm, styled_prompt, img, num_frames=num_frames,
                                steps=steps, guidance=guidance, seed=seed,
                                fps=fps, negative_prompt=neg)
        else:
            return generate_t2v(mm, styled_prompt, num_frames=num_frames,
                                height=height, width=width, steps=steps,
                                guidance=guidance, seed=seed, fps=fps,
                                negative_prompt=neg)

    def _generate_wan22_ti2v(self, prompt, ref_images, duration, steps, guidance, seed, width, height, fps, neg, on_progress, **_):
        from makevid.core.generator import generate_ti2v

        mm = self._get_mm()
        raw = int(duration * fps)
        num_frames = ((raw - 1) // 4) * 4 + 1
        num_frames = max(num_frames, 17)

        styled_prompt = self._apply_style(prompt)

        img = self._load_ref_images(ref_images) if ref_images else None
        if img is None:
            from PIL import Image
            img = Image.new("RGB", (width, height), (0, 0, 0))

        if on_progress:
            on_progress("Carregando Wan 2.2 TI2V...")

        return generate_ti2v(mm, styled_prompt, img, num_frames=num_frames,
                             height=height, width=width, steps=steps,
                             guidance=guidance, seed=seed, fps=fps,
                             negative_prompt=neg, callback=on_progress)

    def _generate_hf(self, prompt, ref_images, on_progress):
        from makevid.core import hf_api

        styled_prompt = self._apply_style(prompt)

        def cb(msg):
            if on_progress:
                on_progress(msg)

        if ref_images:
            img = self._load_ref_images(ref_images)
            return hf_api.generate_i2v(prompt=styled_prompt, image=img, callback=cb)
        else:
            return hf_api.generate_t2v(prompt=styled_prompt, callback=cb)

    def _load_ref_images(self, paths: List[str]) -> Image.Image:
        images = []
        for p in paths:
            try:
                images.append(Image.open(p).convert("RGB"))
            except Exception:
                pass

        if not images:
            return Image.new("RGB", (512, 512), (0, 0, 0))
        if len(images) == 1:
            img = images[0]
            img.thumbnail((512, 512))
            return img

        # Grid
        cols = 2
        rows = (len(images) + 1) // 2
        cw, ch = 512 // cols, 512 // rows
        grid = Image.new("RGB", (512, 512), (0, 0, 0))
        for i, img in enumerate(images):
            img.thumbnail((cw, ch))
            grid.paste(img, ((i % cols) * cw, (i // cols) * ch))
        return grid
