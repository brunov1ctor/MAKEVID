"""Actions do MakeVidWindow - generation, audio, inpaint, export, logs."""

import os
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget
from PySide6.QtCore import Qt, QTimer, Signal

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, AUDIO_DIR
from makevid.core.project import Project


class ActionsMixin:
    """Metodos de acao do MakeVidWindow."""

    # Sinal emitido sempre que o projeto ativo muda
    project_changed = Signal(object)

    # ============================================================
    # GENERATION
    # ============================================================

    def _on_generation_requested(self, params):
        if params.get("action") == "empty_clip":
            self.timeline.redraw()
            return
        if params.get("action") == "image_done":
            self.timeline.redraw()
            return

        # Garantir projeto ativo — cria automaticamente se nao existir
        if self.project is None:
            self.project = Project.create("Novo Projeto")
            self.project.save(PROJECTS_DIR)
            self._on_project_opened(self.project)

        if self._engine == "HuggingFace API" and not os.environ.get("HF_TOKEN", ""):
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
            clip.video_path = path
            clip.duration = dur
            clip.seed = seed_used
            clip.status = "done"
            self.project.save(PROJECTS_DIR)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_done(clip)])

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_error(err)])

        self._gen_service.generate_clip(
            project_id=self.project.id, clip_id=clip.id,
            prompt=params["prompt"], engine=self._engine,
            duration=params["duration"], steps=params["steps"],
            guidance=params["guidance"], seed=params["seed"],
            width=params["width"], height=params["height"],
            fps=self.project.output_fps, negative_prompt=params["negative"],
            ref_images=params.get("ref_images"),
            on_progress=on_progress, on_done=on_done, on_error=on_error,
        )

    def _regenerate_clip(self):
        clip = getattr(self, '_selected_clip', None)
        if not clip or not clip.prompt:
            return
        clip.status = "generating"
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator.on_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path
            clip.duration = dur
            clip.seed = seed_used
            clip.status = "done"
            self.project.save(PROJECTS_DIR)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_done(clip)])

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
            QTimer.singleShot(0, lambda: [self.timeline.redraw(), self.generator.on_error(err)])

        self._gen_service.generate_clip(
            project_id=self.project.id, clip_id=clip.id,
            prompt=clip.prompt, engine=self._engine,
            duration=clip.duration, steps=30, guidance=5.0, seed=None,
            width=self.project.output_width or 832,
            height=self.project.output_height or 480,
            fps=self.project.output_fps, negative_prompt="",
            on_progress=on_progress, on_done=on_done, on_error=on_error,
        )

    def _duplicate_clip(self):
        clip = getattr(self, '_selected_clip', None)
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

    # ============================================================
    # AUDIO
    # ============================================================

    def _import_audio_to_track(self, track_name):
        import shutil
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Audio", "", "Audio (*.wav *.mp3 *.ogg *.flac)")
        if not paths:
            return
        for p in paths:
            src = Path(p)
            dest_dir = AUDIO_DIR / self.project.id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
            dur = 5.0
            try:
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(str(dest)) or 5.0
            except Exception:
                pass
            existing = self.project.get_track_items(track_name)
            start = max((i.start_time + i.duration for i in existing), default=self.timeline.playhead_pos)
            self.project.add_track_item(name=src.stem[:20], track=track_name, start_time=start, duration=dur, file_path=str(dest),
                params={"block_name": f"\U0001f4c2 {src.stem[:12]}"})
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        self._show_generator()

    def _clear_track(self, track_name):
        items = self.project.get_track_items(track_name)
        for item in items:
            self.project.remove_track_item(item.id)
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        self._show_generator()

    def _add_fx_to_timeline(self, fx_name):
        interaction = self.timeline._scene._interaction
        marked = interaction._marked_diamonds
        if marked:
            for diamond_id in list(marked):
                pos_idx = int(diamond_id.split("_")[1])
                clips = sorted(self.project.clips, key=lambda c: c.position)
                t = sum(c.duration for c in clips if c.position < pos_idx)
                old = [i for i in self.project.get_track_items("fx") if abs(i.start_time - t) < 0.1]
                for o in old:
                    self.project.remove_track_item(o.id)
                self.project.add_track_item(name=fx_name, track="fx", start_time=t, duration=2.0)
            marked.clear()
        else:
            self.project.add_track_item(name=fx_name, track="fx", start_time=self.timeline.playhead_pos, duration=2.0)
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        self._show_generator()

    def _generate_scene_audio(self):
        from makevid.services.audio_service import AudioService
        from makevid.core import freesound_provider

        if not freesound_provider.FREESOUND_API_KEY:
            self.generator._show_freesound_prompt(on_saved=lambda: self._generate_scene_audio())
            return

        clips = sorted(self.project.clips, key=lambda c: c.position)
        if not clips:
            return
        idx = 0
        ph = self.timeline.playhead_pos
        current = 0.0
        for c in clips:
            if current <= ph < current + c.duration:
                idx = c.position
                break
            current += c.duration
        clip = clips[min(idx, len(clips) - 1)]
        scene = {"visual": clip.prompt or "", "duration": str(clip.duration)}
        svc = AudioService()
        self.generator._status.setText("Gerando audio...")
        self.generator._status.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; border: none;")
        self.generator._progress.setValue(15)

        self._audio_progress_timer = QTimer(self)
        self._audio_progress_value = 15
        def _animate():
            if self._audio_progress_value < 85:
                self._audio_progress_value += 2
                self.generator._progress.setValue(self._audio_progress_value)
        self._audio_progress_timer.timeout.connect(_animate)
        self._audio_progress_timer.setInterval(200)
        self._audio_progress_timer.start()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator._status.setText(msg))

        def on_done(plan, results):
            clip_start = sum(c.duration for c in clips[:idx])
            for key, track in [("voices", "voice"), ("ambience", "sfx"), ("music", "music")]:
                if key in results:
                    paths = results[key] if isinstance(results[key], list) else [results[key]]
                    icons = {"voices": "\U0001f5e3", "ambience": "\U0001f50a", "music": "\U0001f3b5"}
                    for path in paths:
                        from makevid.core.audio_utils import get_audio_duration
                        dur = get_audio_duration(path) or 3.0
                        self.project.add_track_item(name=key[:8], track=track,
                            start_time=clip_start, duration=dur, file_path=path, clip_index=idx,
                            params={"block_name": f"{icons.get(key, '')} {key[:8]}"})
            self.project.save(PROJECTS_DIR)
            def _on_audio_done():
                self._audio_progress_timer.stop()
                self.generator._progress.setValue(100)
                self.generator._status.setText("Audio gerado!")
                self.generator._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
                self.timeline.redraw()
                QTimer.singleShot(1500, lambda: self.generator._progress.setValue(0))
            QTimer.singleShot(0, _on_audio_done)

        def on_error(err):
            def _on_audio_err():
                self._audio_progress_timer.stop()
                self.generator._progress.setValue(0)
                self.generator._status.setText(f"Erro: {err[:40]}")
                self.generator._status.setStyleSheet(f"color: #ff4444; font-size: 10pt; border: none;")
                if "API_KEY" in err or "key" in err.lower() or "configurada" in err.lower():
                    self.generator._show_freesound_prompt(on_saved=lambda: self._generate_scene_audio())
            QTimer.singleShot(0, _on_audio_err)

        svc.generate_scene_audio(project_id=self.project.id, scene_metadata=scene,
            scene_index=idx, on_progress=on_progress, on_done=on_done,
            on_error=on_error, characters=self.project.characters)

    def _generate_all_audio(self):
        from makevid.services.audio_service import AudioService
        from makevid.core import freesound_provider

        if not freesound_provider.FREESOUND_API_KEY:
            self.generator._show_freesound_prompt(on_saved=lambda: self._generate_all_audio())
            return

        clips = sorted(self.project.clips, key=lambda c: c.position)
        if not clips:
            return
        scenes = self.project.world.scenes or [{"visual": c.prompt or "", "duration": str(c.duration)} for c in clips]
        svc = AudioService()
        self.generator._status.setText(f"Gerando {len(scenes)} cenas...")
        self.generator._status.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; border: none;")
        self.generator._progress.setValue(15)

        self._audio_all_progress_timer = QTimer(self)
        self._audio_all_progress_value = 15
        def _animate():
            if self._audio_all_progress_value < 85:
                self._audio_all_progress_value += 1
                self.generator._progress.setValue(self._audio_all_progress_value)
        self._audio_all_progress_timer.timeout.connect(_animate)
        self._audio_all_progress_timer.setInterval(300)
        self._audio_all_progress_timer.start()

        def on_progress(msg):
            QTimer.singleShot(0, lambda: self.generator._status.setText(msg))

        def on_done(all_results):
            t = 0.0
            for si, (plan, results) in enumerate(all_results):
                for key, track in [("voices", "voice"), ("ambience", "sfx"), ("music", "music")]:
                    if key in results:
                        paths = results[key] if isinstance(results[key], list) else [results[key]]
                        icons = {"voices": "\U0001f5e3", "ambience": "\U0001f50a", "music": "\U0001f3b5"}
                        for path in paths:
                            from makevid.core.audio_utils import get_audio_duration
                            dur = get_audio_duration(path) or 3.0
                            self.project.add_track_item(name=key[:8], track=track,
                                start_time=t, duration=dur, file_path=path, clip_index=si,
                                params={"block_name": f"{icons.get(key, '')} {key[:8]}"})
                t += plan.scene_duration
            self.project.save(PROJECTS_DIR)
            def _on_all_done():
                self._audio_all_progress_timer.stop()
                self.generator._progress.setValue(100)
                self.generator._status.setText(f"{len(all_results)} cenas!")
                self.generator._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
                self.timeline.redraw()
                QTimer.singleShot(1500, lambda: self.generator._progress.setValue(0))
            QTimer.singleShot(0, _on_all_done)

        def on_error(err):
            def _on_all_err():
                self._audio_all_progress_timer.stop()
                self.generator._progress.setValue(0)
                self.generator._status.setText(f"Erro: {err[:40]}")
                self.generator._status.setStyleSheet(f"color: #ff4444; font-size: 10pt; border: none;")
                if "API_KEY" in err or "key" in err.lower() or "configurada" in err.lower():
                    self.generator._show_freesound_prompt(on_saved=lambda: self._generate_all_audio())
            QTimer.singleShot(0, _on_all_err)

        svc.generate_all_scenes(project_id=self.project.id, scenes=scenes,
            on_progress=on_progress, on_done=on_done, on_error=on_error,
            characters=self.project.characters)

    # ============================================================
    # INPAINT
    # ============================================================

    def _show_inpaint(self):
        import cv2
        clips = sorted(self.project.clips, key=lambda c: c.position)
        t = self.timeline.playhead_pos
        current = 0.0
        for clip in clips:
            if current <= t < current + clip.duration and clip.video_path and Path(clip.video_path).exists():
                cap = cv2.VideoCapture(str(clip.video_path))
                fps = cap.get(cv2.CAP_PROP_FPS) or 16
                frame_idx = int((t - current) * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    self.inpaint_panel.set_frame(frame[:, :, ::-1])
                    self._left_stack.setCurrentWidget(self.inpaint_panel)
                    return
            current += clip.duration
        self.generator._status.setText("Nenhum frame no playhead")

    def _do_inpaint(self, params):
        from makevid.services.inpainting_service import InpaintingService
        svc = InpaintingService()
        svc.inpaint_region(
            frame=params["frame"], mask=params["mask"], prompt=params["prompt"],
            project_id=self.project.id,
            on_progress=lambda msg: QTimer.singleShot(0, lambda: self.inpaint_panel._status.setText(msg)),
            on_done=lambda result: QTimer.singleShot(0, lambda: self.inpaint_panel.on_done(result)),
            on_error=lambda err: QTimer.singleShot(0, lambda: self.inpaint_panel.on_error(err)),
        )

    # ============================================================
    # EXPORT
    # ============================================================

    def _export_game_engine(self):
        from makevid.core.export import PRESETS, RESOLUTIONS, FPS_OPTIONS, export_video
        from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("Export Game Engine")
        dlg.setStyleSheet(f"background: {C['panel']}; color: {C['text']};")
        form = QFormLayout(dlg)

        preset_cb = QComboBox()
        preset_cb.addItems([p["label"] for p in PRESETS.values()])
        form.addRow("Preset:", preset_cb)

        res_cb = QComboBox()
        res_cb.addItems(list(RESOLUTIONS.keys()))
        res_cb.setCurrentText("1080p")
        form.addRow("Resolucao:", res_cb)

        fps_cb = QComboBox()
        fps_cb.addItems([str(f) for f in FPS_OPTIONS])
        fps_cb.setCurrentText("30")
        form.addRow("FPS:", fps_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() != QDialog.Accepted:
            return

        from makevid.core.export import get_preset_key
        preset_key = get_preset_key(preset_cb.currentText())
        res_name = res_cb.currentText()
        resolution = RESOLUTIONS.get(res_name, (1920, 1080))
        if resolution is None:
            resolution = (1920, 1080)
        fps = int(fps_cb.currentText())

        clips = sorted(self.project.clips, key=lambda c: c.position)
        source = None
        for c in clips:
            if c.video_path and Path(c.video_path).exists():
                source = c.video_path
                break
        if not source:
            return

        try:
            out_dir = Path.home() / "Downloads"
            result = export_video(source, out_dir, self.project.name or "export",
                                  preset=preset_key, resolution=resolution, fps=fps)
            self.generator._status.setText(f"Exportado: {result.name}")
        except Exception as e:
            self.generator._status.setText(f"Erro export: {str(e)[:40]}")

    # ============================================================
    # LOGS
    # ============================================================

    def _open_logs(self):
        from makevid.core.logger import get_log_content, clear_logs
        from PySide6.QtWidgets import QComboBox

        dlg = QDialog(self)
        dlg.setWindowTitle("Logs - MAKEVID")
        dlg.resize(750, 450)
        dlg.setStyleSheet(f"background: {C['panel']}; color: {C['text']};")
        layout = QVBoxLayout(dlg)

        hdr = QHBoxLayout()
        lbl = QLabel("LOGS")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        filter_cb = QComboBox()
        filter_cb.addItems(["Todos", "Erros", "Audio", "Export", "Clip", "Geracao"])
        filter_cb.setStyleSheet(f"background: {C['card']}; color: {C['text']}; border: 1px solid {C['purple']}; border-radius: 3px; padding: 2px 8px;")
        hdr.addWidget(filter_cb)
        layout.addLayout(hdr)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet(f"background: #0a0c14; color: #88cc88; font-family: Consolas; font-size: 9pt; border: 1px solid {C['border']};")
        layout.addWidget(txt)

        def refresh():
            content = get_log_content(500)
            f = filter_cb.currentText()
            if f == "Erros":
                content = "\n".join(l for l in content.split("\n") if "ERROR" in l or "FALHA" in l or "Erro" in l)
            elif f == "Audio":
                content = "\n".join(l for l in content.split("\n") if "audio" in l.lower() or "sound" in l.lower() or "tts" in l.lower())
            elif f == "Export":
                content = "\n".join(l for l in content.split("\n") if "export" in l.lower())
            elif f == "Clip":
                content = "\n".join(l for l in content.split("\n") if "clip" in l.lower())
            elif f == "Geracao":
                content = "\n".join(l for l in content.split("\n") if "gen" in l.lower() or "INICIO" in l or "OK [" in l)
            txt.setPlainText(content or "(nenhum log para este filtro)")

        refresh()
        filter_cb.currentTextChanged.connect(lambda: refresh())

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("Atualizar")
        btn_refresh.setStyleSheet(f"background: {C['card']}; color: {C['text2']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 4px 10px;")
        btn_refresh.clicked.connect(refresh)
        btn_row.addWidget(btn_refresh)
        btn_clear = QPushButton("Limpar Logs")
        btn_clear.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; border: 1px solid #ff4444; border-radius: 4px; padding: 4px 10px;")
        btn_clear.clicked.connect(lambda: [clear_logs(), refresh()])
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        dlg.exec()

    # ============================================================
    # PROJECT
    # ============================================================

    def _clear_project(self):
        """Remove todos os clips e track items da timeline do projeto atual."""
        self.project.clips.clear()
        self.project.track_items.clear()
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

    def _show_projects_panel(self):
        self.preview.show_projects_panel()

    def _on_project_opened(self, proj):
        self.project = proj
        self.project_changed.emit(proj)
        self.timeline.redraw()
        if hasattr(self, '_project_badge'):
            self._update_project_badge()

    def _load_project(self) -> Project:
        files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            try:
                return Project.load(files[0])
            except Exception:
                pass
        proj = Project.create("meu_projeto")
        proj.save(PROJECTS_DIR)
        return proj
