"""audio_actions — geração de áudio por IA e manipulação de tracks."""

import logging
import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QTimer

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, AUDIO_DIR
from makevid.core.logger import log_error

_log = logging.getLogger("audio")


class AudioActionsMixin:

    def _import_audio_to_track(self, track_name):
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Audio", "", "Audio (*.wav *.mp3 *.ogg *.flac)")
        if not paths:
            return
        for p in paths:
            src = Path(p)
            dest_dir = AUDIO_DIR / self.project.id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            try:
                if not dest.exists():
                    shutil.copy2(str(src), str(dest))
            except Exception as e:
                _log.error(f"copy2 falhou: {src} → {dest}: {e}")
                continue
            dur = 5.0
            try:
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(str(dest)) or 5.0
            except Exception as e:
                log_error("import_audio", str(e))
            existing = self.project.get_track_items(track_name)
            start = max((i.start_time + i.duration for i in existing), default=self.timeline.playhead_pos)
            self.project.add_track_item(
                name=src.stem[:20], track=track_name, start_time=start,
                duration=dur, file_path=str(dest),
                params={"block_name": src.stem[:20], "source_type": "import"},
            )
            _log.info(f"Audio importado: {src.name} -> {track_name} dur={dur:.1f}s start={start:.1f}")
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        self._show_generator()

    def _clear_track(self, track_name):
        n = len(self.project.get_track_items(track_name))
        sel = self.timeline._selected_track_item_id
        removed_sel = any(i.id == sel for i in self.project.get_track_items(track_name))
        for item in self.project.get_track_items(track_name):
            self.project.remove_track_item(item.id)
        if removed_sel:
            self.timeline._selected_track_item_id = None
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        self._show_generator()
        _log.info(f"Track '{track_name}' limpa ({n} itens removidos)")

    def _add_fx_to_timeline(self, fx_name):
        interaction = self.timeline._scene._interaction
        marked = interaction._marked_diamonds
        if marked:
            for diamond_id in list(marked):
                pos_idx = int(diamond_id.split("_")[1])
                clips = sorted(self.project.clips, key=lambda c: c.position)
                t = sum(c.duration for c in clips if c.position < pos_idx)
                for o in [i for i in self.project.get_track_items("fx") if abs(i.start_time - t) < 0.1]:
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
        idx, ph, current = 0, self.timeline.playhead_pos, 0.0
        for c in clips:
            if current <= ph < current + c.duration:
                idx = c.position; break
            current += c.duration
        clip = clips[min(idx, len(clips) - 1)]
        scene = {"visual": clip.prompt or "", "duration": str(clip.duration)}

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
            icons = {"voices": "\U0001f5e3", "ambience": "\U0001f50a", "music": "\U0001f3b5"}
            for key, track in [("voices", "voice"), ("ambience", "sfx"), ("music", "music")]:
                if key in results:
                    for path in (results[key] if isinstance(results[key], list) else [results[key]]):
                        from makevid.core.audio_utils import get_audio_duration
                        dur = get_audio_duration(path) or 3.0
                        self.project.add_track_item(
                            name=key[:8], track=track, start_time=clip_start,
                            duration=dur, file_path=path, clip_index=idx,
                            params={"block_name": key[:8], "source_type": key},
                        )
            self.project.save(PROJECTS_DIR)
            _log.info(f"Audio cena {idx} gerado: {list(results.keys())}")
            def _done():
                self._audio_progress_timer.stop()
                self.generator._progress.setValue(100)
                self.generator._status.setText("Audio gerado!")
                self.generator._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
                self.timeline.redraw()
                QTimer.singleShot(1500, lambda: self.generator._progress.setValue(0))
            QTimer.singleShot(0, _done)

        def on_error(err):
            def _err():
                self._audio_progress_timer.stop()
                self.generator._progress.setValue(0)
                self.generator._status.setText(f"Erro: {err[:40]}")
                self.generator._status.setStyleSheet("color: #ff4444; font-size: 10pt; border: none;")
                if "API_KEY" in err or "key" in err.lower() or "configurada" in err.lower():
                    self.generator._show_freesound_prompt(on_saved=lambda: self._generate_scene_audio())
            _log.error(f"Erro audio cena {idx}: {err[:80]}")
            QTimer.singleShot(0, _err)

        AudioService().generate_scene_audio(
            project_id=self.project.id, scene_metadata=scene, scene_index=idx,
            on_progress=on_progress, on_done=on_done, on_error=on_error,
            characters=self.project.characters,
        )

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
            icons = {"voices": "\U0001f5e3", "ambience": "\U0001f50a", "music": "\U0001f3b5"}
            for si, (plan, results) in enumerate(all_results):
                for key, track in [("voices", "voice"), ("ambience", "sfx"), ("music", "music")]:
                    if key in results:
                        for path in (results[key] if isinstance(results[key], list) else [results[key]]):
                            from makevid.core.audio_utils import get_audio_duration
                            dur = get_audio_duration(path) or 3.0
                            self.project.add_track_item(
                                name=key[:8], track=track, start_time=t,
                                duration=dur, file_path=path, clip_index=si,
                                params={"block_name": key[:8], "source_type": key},
                            )
                t += plan.scene_duration
            self.project.save(PROJECTS_DIR)
            def _done():
                self._audio_all_progress_timer.stop()
                self.generator._progress.setValue(100)
                self.generator._status.setText(f"{len(all_results)} cenas!")
                self.generator._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
                self.timeline.redraw()
                QTimer.singleShot(1500, lambda: self.generator._progress.setValue(0))
            QTimer.singleShot(0, _done)

        def on_error(err):
            def _err():
                self._audio_all_progress_timer.stop()
                self.generator._progress.setValue(0)
                self.generator._status.setText(f"Erro: {err[:40]}")
                self.generator._status.setStyleSheet("color: #ff4444; font-size: 10pt; border: none;")
                if "API_KEY" in err or "key" in err.lower() or "configurada" in err.lower():
                    self.generator._show_freesound_prompt(on_saved=lambda: self._generate_all_audio())
            QTimer.singleShot(0, _err)

        AudioService().generate_all_scenes(
            project_id=self.project.id, scenes=scenes,
            on_progress=on_progress, on_done=on_done, on_error=on_error,
            characters=self.project.characters,
        )
