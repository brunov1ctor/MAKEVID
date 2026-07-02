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
        self._active_project_id = None

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
        motion_ref_path: Optional[str] = None,
        motion_mode: str = "pose",
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """Gera clip em background thread. Callbacks sao chamados na thread."""
        self._active_project_id = project_id

        # Auto-injetar ref_image de personagem se detectado no prompt
        if not ref_images:
            ref_images = self._get_character_ref_images(prompt)

        # Auto-selecionar imagem de ambientacao se disponivel
        if not ref_images:
            ref_images = self._get_ambience_ref(prompt, engine)

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

                # ControlNet: se tem motion_ref, extrair controles e gerar
                if motion_ref_path:
                    result = self._generate_controlnet(
                        prompt, motion_ref_path, motion_mode,
                        duration, steps, guidance, seed,
                        width, height, fps, negative_prompt, on_progress)
                    from makevid.core.video import frames_to_mp4
                    if on_progress:
                        on_progress("Salvando MP4...")
                    frames_to_mp4(result.frames, out_path, fps=result.fps)
                    log_generation(prompt, engine, result.duration, "done")
                    if on_done:
                        on_done(str(out_path), result.duration, result.seed)
                    return

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
            proj = self._load_active_project()
            if proj:
                for char in proj.characters:
                    if char.reference_image and Path(char.reference_image).exists():
                        refs.append(Image.open(char.reference_image).convert("RGB"))
        except Exception as _e:
            logger.debug(f"Suppressed: {_e}")

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
        try:
            proj = self._load_active_project()
            if not proj:
                return None
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
        try:
            proj = self._load_active_project()
            if proj:

                # Detectar nomes de personagens no prompt e injetar descricao
                char_descriptions = []
                prompt_lower = prompt.lower()
                for char in proj.characters:
                    if char.name and char.name.lower() in prompt_lower:
                        desc = char.to_prompt()
                        if desc:
                            char_descriptions.append(f"{char.name}: {desc}")

                if char_descriptions:
                    return f"{'; '.join(char_descriptions)}, {prompt}"
        except Exception as _e:
            logger.debug(f"Suppressed: {_e}")
        return prompt

    def _get_character_ref_images(self, prompt: str) -> Optional[List[str]]:
        """Detecta personagens no prompt e retorna suas ref images se existirem."""
        from pathlib import Path
        try:
            proj = self._load_active_project()
            if proj:
                prompt_lower = prompt.lower()
                refs = []
                for char in proj.characters:
                    if char.name and char.name.lower() in prompt_lower:
                        if char.reference_image and Path(char.reference_image).exists():
                            refs.append(char.reference_image)
                if refs:
                    return refs
        except Exception as _e:
            logger.debug(f"Suppressed: {_e}")
        return None

    def _load_active_project(self):
        """Carrega o projeto selecionado pela UI para evitar misturar JSONs salvos."""
        from makevid.config import PROJECTS_DIR
        from makevid.core.project import Project

        if self._active_project_id:
            path = PROJECTS_DIR / f"{self._active_project_id}.json"
            if path.exists():
                return Project.load(path)

        project_files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if project_files:
            return Project.load(project_files[0])
        return None

    def _get_ambience_ref(self, prompt: str, engine: str = "") -> Optional[List[str]]:
        try:
            from makevid.core.ambience_matcher import find_best_match, find_dynamic_references
            pid = self._active_project_id or ""
            if "VACE" in engine:
                refs = find_dynamic_references(prompt, max_refs=4, min_score=0.20, project_id=pid)
                if refs:
                    return refs
            else:
                match = find_best_match(prompt, project_id=pid)
                if match:
                    return [match]
        except Exception as _e:
            logger.debug(f"Suppressed: {_e}")
        return None

    def _generate_controlnet(self, prompt, motion_ref_path, motion_mode,
                              duration, steps, guidance, seed,
                              width, height, fps, neg, on_progress):
        """Gera video guiado por ControlNet (pose/depth de video de referencia)."""
        from makevid.services.controlnet_service import ControlNetService
        from makevid.core.generator import generate_with_controlnet
        from makevid.config import OUTPUTS_DIR
        import tempfile

        mm = self._get_mm()
        styled_prompt = self._apply_style(prompt)
        cn_svc = ControlNetService()

        # Extrair frames de controle do video de referencia
        tmp_dir = tempfile.mkdtemp(prefix="makevid_cn_")
        control_frames = []
        extract_done = [False]
        extract_fps = [fps]

        if on_progress:
            on_progress(f"Extraindo {motion_mode} do video de referencia...")

        def on_extract_done(paths, video_fps):
            for p in paths:
                control_frames.append(Image.open(p).convert("RGB"))
            extract_fps[0] = video_fps
            extract_done[0] = True

        def on_extract_error(err):
            raise Exception(f"Extracao {motion_mode} falhou: {err}")

        # Extrair sincrono (dentro da thread de geracao)
        import cv2
        if motion_mode == "depth":
            cn_svc._ensure_depth_model()
            cap = cv2.VideoCapture(motion_ref_path)
            extract_fps[0] = cap.get(cv2.CAP_PROP_FPS) or fps
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # Limitar frames pela duracao desejada
            max_frames = int(duration * extract_fps[0])
            idx = 0
            while idx < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                depth = cn_svc._extract_depth_frame(frame[:, :, ::-1])
                # Converter depth grayscale para RGB
                control_frames.append(Image.fromarray(depth).convert("RGB"))
                idx += 1
                if on_progress and idx % 10 == 0:
                    on_progress(f"Depth: {idx}/{min(max_frames, total)}")
            cap.release()
        else:
            cn_svc._ensure_pose_model()
            cap = cv2.VideoCapture(motion_ref_path)
            extract_fps[0] = cap.get(cv2.CAP_PROP_FPS) or fps
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            max_frames = int(duration * extract_fps[0])
            idx = 0
            while idx < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                pose = cn_svc._extract_pose_frame(frame)
                control_frames.append(Image.fromarray(pose))
                idx += 1
                if on_progress and idx % 10 == 0:
                    on_progress(f"Pose: {idx}/{min(max_frames, total)}")
            cap.release()

        if not control_frames:
            raise Exception("Nenhum frame de controle extraido")

        if on_progress:
            on_progress(f"Gerando {len(control_frames)} frames com ControlNet...")

        return generate_with_controlnet(
            mm, styled_prompt, control_frames,
            control_type=motion_mode,
            num_frames=len(control_frames),
            height=height, width=width,
            steps=steps, guidance=guidance,
            seed=seed, fps=int(extract_fps[0]),
            negative_prompt=neg, callback=on_progress,
        )

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
            except Exception as _e:
                logger.debug(f"Suppressed: {_e}")

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
