"""generation_actions — geração e manipulação de clips."""

import os
import logging
from PySide6.QtCore import QTimer
from makevid.config import PROJECTS_DIR
from makevid.core.project import Project
from makevid.core.logger import log_generation, log_clip_action, log_error

_log = logging.getLogger("gen")


class GenerationActionsMixin:

    def _on_generation_requested(self, params):
        action = params.get("action")

        # Primeira geração: persiste o projeto em disco
        if not (PROJECTS_DIR / f"{self.project.id}.json").exists():
            self.project.save(PROJECTS_DIR)
            self._on_project_opened(self.project)

        if action == "ensure_project":
            return

        if action == "image_done":
            try:
                proj = Project.load(PROJECTS_DIR / f"{self.project.id}.json")
            except Exception as e:
                log_error("image_done", f"erro ao carregar projeto: {e}")
                proj = self.project
            if not proj.name:
                import time as _t
                proj.name = f"Projeto {_t.strftime('%d/%m %H:%M')}"
                proj.save(PROJECTS_DIR)
            # preservar track_items que estão só em memória
            if not proj.track_items and self.project.track_items:
                proj.track_items = self.project.track_items
            _log.info(f"[image_done] projeto sincronizado: id={proj.id} clips={len(proj.clips)}")
            self.project = proj
            self.state.project = proj
            self.generator.project = proj
            self._ctrl.open(proj)
            return

        if action == "empty_clip":
            clip = self.project.add_clip(prompt="", position=len(self.project.clips))
            clip.duration = params.get("duration", 5.0)
            self.project.save(PROJECTS_DIR)
            log_clip_action("create_empty", clip.id, f"dur={clip.duration:.1f}s")
            self.timeline.redraw()
            return

        if self.state.engine == "HuggingFace API" and not os.environ.get("HF_TOKEN", ""):
            from makevid.core.hf_api import _get_token
            if not _get_token():
                self.generator._show_token_prompt(auto_generate=True)
                return

        clip = self.project.add_clip(prompt=params["prompt"])
        clip.duration = params["duration"]
        clip.status = "generating"
        self.project.save(PROJECTS_DIR)
        log_generation(params["prompt"], self.state.engine, params["duration"], "generating")
        self.timeline.redraw()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator.on_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path; clip.duration = dur
            clip.seed = seed_used; clip.status = "done"
            if not self.project.name:
                import time as _t
                self.project.name = f"Projeto {_t.strftime('%d/%m %H:%M')}"
            self.project.save(PROJECTS_DIR)
            log_generation(clip.prompt, self.state.engine, dur, "done")
            log_clip_action("generated", clip.id, f"dur={dur:.1f}s seed={seed_used}")
            from makevid.qt.timeline.clip_item import ClipGraphicsItem
            if ClipGraphicsItem._thumb_cache:
                ClipGraphicsItem._thumb_cache.invalidate(clip.id)
            QTimer.singleShot(0, lambda: [self._on_project_opened(self.project), self.timeline.redraw(), self.generator.on_done(clip)])

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
            log_generation(clip.prompt, self.state.engine, 0, "error", err)
            log_error("generate_clip", err)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_error(err)])

        self._gen_service.generate_clip(
            project_id=self.project.id, clip_id=clip.id,
            prompt=params["prompt"], engine=self.state.engine,
            duration=params["duration"], steps=params["steps"],
            guidance=params["guidance"], seed=params["seed"],
            width=params["width"], height=params["height"],
            fps=self.project.output_fps, negative_prompt=params["negative"],
            ref_images=params.get("ref_images"),
            on_progress=on_progress, on_done=on_done, on_error=on_error,
        )

    def _regenerate_clip(self):
        clip = self.state.selected_clip
        if not clip or not clip.prompt:
            return
        clip.status = "generating"
        self.project.save(PROJECTS_DIR)
        log_generation(clip.prompt, self.state.engine, clip.duration, "generating")
        self.timeline.redraw()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator.on_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path; clip.duration = dur
            clip.seed = seed_used; clip.status = "done"
            if not self.project.name:
                import time as _t
                self.project.name = f"Projeto {_t.strftime('%d/%m %H:%M')}"
            self.project.save(PROJECTS_DIR)
            log_generation(clip.prompt, self.state.engine, dur, "done")
            log_clip_action("regenerated", clip.id, f"dur={dur:.1f}s seed={seed_used}")
            from makevid.qt.timeline.clip_item import ClipGraphicsItem
            if ClipGraphicsItem._thumb_cache:
                ClipGraphicsItem._thumb_cache.invalidate(clip.id)
            QTimer.singleShot(0, lambda: [self._on_project_opened(self.project), self.timeline.redraw(), self.generator.on_done(clip)])

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
            log_generation(clip.prompt, self.state.engine, 0, "error", err)
            log_error("regenerate_clip", err)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_error(err)])

        self._gen_service.generate_clip(
            project_id=self.project.id, clip_id=clip.id,
            prompt=clip.prompt, engine=self.state.engine,
            duration=clip.duration, steps=30, guidance=5.0, seed=None,
            width=self.project.output_width or 832,
            height=self.project.output_height or 480,
            fps=self.project.output_fps, negative_prompt="",
            on_progress=on_progress, on_done=on_done, on_error=on_error,
        )

    def _duplicate_clip(self):
        clip = self.state.selected_clip
        if not clip:
            return
        new_clip = self.project.add_clip(prompt=clip.prompt, position=clip.position + 1)
        new_clip.duration = clip.duration
        new_clip.seed = clip.seed
        new_clip.status = clip.status
        new_clip.video_path = clip.video_path
        self.project.save(PROJECTS_DIR)
        log_clip_action("duplicate", clip.id, f"new_id={new_clip.id}")
        self.timeline.redraw()

    def _split_clip_at_playhead(self):
        self.timeline.enter_split_mode()
