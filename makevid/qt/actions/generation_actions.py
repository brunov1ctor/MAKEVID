"""generation_actions — geração e manipulação de clips."""

import os
from PySide6.QtCore import QTimer
from makevid.config import PROJECTS_DIR
from makevid.core.project import Project


class GenerationActionsMixin:

    def _on_generation_requested(self, params):
        if params.get("action") in ("empty_clip", "image_done"):
            self.timeline.redraw()
            return

        if self.project is None:
            self.project = Project.create("Novo Projeto")
            self.project.save(PROJECTS_DIR)
            self._on_project_opened(self.project)

        if self.state.engine == "HuggingFace API" and not os.environ.get("HF_TOKEN", ""):
            from makevid.core.hf_api import _get_token
            if not _get_token():
                self.generator._show_token_prompt(auto_generate=True)
                return

        clip = self.project.add_clip(prompt=params["prompt"])
        clip.duration = params["duration"]
        clip.status = "generating"
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator.on_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path; clip.duration = dur
            clip.seed = seed_used; clip.status = "done"
            self.project.save(PROJECTS_DIR)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_done(clip)])

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
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
        self.timeline.redraw()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator.on_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path; clip.duration = dur
            clip.seed = seed_used; clip.status = "done"
            self.project.save(PROJECTS_DIR)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_done(clip)])

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
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
        self.timeline.redraw()

    def _split_clip_at_playhead(self):
        self.timeline.enter_split_mode()
