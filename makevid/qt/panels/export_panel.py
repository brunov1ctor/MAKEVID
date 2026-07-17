"""Export Panel Qt - Configuração e execução de export."""

import re
import logging
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QProgressBar, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

from makevid.qt.theme import C
from makevid.config import OUTPUTS_DIR, PROJECTS_DIR
from makevid.core.logger import log_export, log_export_error

_log = logging.getLogger("export")


class ExportPanel(QWidget):
    """Painel de configuração e execução de export."""

    closed = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(0)
        self._format = None
        self._track_checks = {}
        self._syncing_export_ui = False
        self._est_dur = self._est_size = self._est_res = self._est_clips = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("EXPORTAR")
        title.setStyleSheet(f"color: {C['primary']}; font-size: 10pt; font-weight: bold; letter-spacing: 1px;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("\u2715")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Nome
        layout.addWidget(self._sub("Nome:"))
        self._name_entry = QLineEdit(self.project.name or "")
        self._name_entry.setStyleSheet(
            f"background: {C['dark']}; color: {C['text']}; border: 2px solid {C['primary']}; "
            f"border-radius: 10px; padding: 4px; font-size: 11pt; font-weight: bold;")
        layout.addWidget(self._name_entry)

        # Tracks
        sel_hdr = QHBoxLayout()
        sel_hdr.addWidget(self._sub("Selecionar"))
        sel_hdr.addStretch()
        self._sel_all_btn = QPushButton("Todas")
        self._sel_all_btn.setFixedHeight(18)
        self._sel_all_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 7pt; "
            f"border: 1px solid {C['border']}; border-radius: 3px; padding: 0 5px; }}"
            f"QPushButton:hover {{ color: {C['text']}; border-color: {C['primary']}; }}")
        self._sel_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self._track_checks.values()])
        sel_hdr.addWidget(self._sel_all_btn)
        layout.addLayout(sel_hdr)

        tracks_frame = QFrame()
        tracks_frame.setStyleSheet(
            f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        tracks_layout = QVBoxLayout(tracks_frame)
        tracks_layout.setContentsMargins(8, 6, 8, 6)
        tracks_layout.setSpacing(3)
        self._track_checks = {}
        self._count_labels = {}
        _TRACKS = [
            ("video", "\U0001f3ac VIDEO",  C["primary"]),
            ("voice", "\U0001f3a4 VOZ",    C["track_voice"]),
            ("sfx",   "\U0001f50a SFX",    C["track_sfx"]),
            ("music", "\U0001f3b5 MUSICA", C["track_music"]),
            ("audio", "\U0001f3a7 AUDIO",  C["track_audio"]),
        ]
        for key, label, color in _TRACKS:
            row = QHBoxLayout()
            row.setSpacing(6)
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(
                f"QCheckBox {{ color: {color}; font-family: Consolas; font-size: 9pt; "
                f"font-weight: bold; spacing: 6px; background: transparent; }}"
                f"QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; "
                f"border: 2px solid {color}; background: {C['card']}; }}"
                f"QCheckBox::indicator:checked {{ background: {color}; }}"
                f"QCheckBox::indicator:hover {{ border-color: {C['text']}; }}")
            cb.stateChanged.connect(self._on_export_pref_changed)
            row.addWidget(cb)
            row.addStretch()
            n = len(self.project.get_track_items(key)) if key != "video" else len(self.project.clips)
            count_lbl = QLabel(f"{n}")
            count_lbl.setFixedWidth(20)
            count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            count_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 8pt; background: transparent;")
            row.addWidget(count_lbl)
            tracks_layout.addLayout(row)
            self._track_checks[key] = cb
            self._count_labels[key] = count_lbl
        layout.addWidget(tracks_frame)

        # Formato
        layout.addWidget(self._sub("Formato:"))
        self._format = QComboBox()
        self._format.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; "
            f"border-radius: 3px; padding: 2px 6px;")
        self._format.currentIndexChanged.connect(self._on_export_pref_changed)
        layout.addWidget(self._format)
        self._refresh_format_options()

        # Estimativas
        est_frame = QFrame()
        est_frame.setStyleSheet(
            f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        est_layout = QVBoxLayout(est_frame)
        est_layout.setContentsMargins(8, 6, 8, 6)
        est_layout.setSpacing(2)
        est_title = QLabel("Estimativas")
        est_title.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold; background: transparent;")
        est_layout.addWidget(est_title)
        self._est_dur   = QLabel()
        self._est_size  = QLabel()
        self._est_res   = QLabel()
        self._est_clips = QLabel()
        for lbl in (self._est_dur, self._est_size, self._est_res, self._est_clips):
            lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; background: transparent;")
            est_layout.addWidget(lbl)
        layout.addWidget(est_frame)
        self._update_estimate()

        # Progress
        self._progress = QProgressBar()
        self._progress.setFixedHeight(14)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            f"QProgressBar {{ background: {C['card']}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {C['primary']}; border-radius: 4px; }}")
        layout.addWidget(self._progress)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._export_btn = None
        layout.addStretch()
        self._load_export_prefs_from_project()

    _FORMATS_VIDEO = ["MP4 (H.264)", "MP4 (H.265/HEVC)", "MOV (ProRes)", "WEBM (VP9)", "MKV (H.264)"]
    _FORMATS_AUDIO = ["WAV (audio 16bit)", "MP3 (320kbps)", "FLAC (lossless)"]

    def _refresh_format_options(self):
        """Atualiza o dropdown de formato conforme video/audio marcados."""
        if not self._format or not self._track_checks:
            return
        video_on = bool(self._track_checks.get("video") and self._track_checks["video"].isChecked())
        audio_on = any(cb.isChecked() for k, cb in self._track_checks.items() if k != "video")

        # video marcado -> formatos de video; audio marcado -> formatos de audio
        # ambos -> video + audio; nenhum -> video como fallback
        if video_on and audio_on:
            options = self._FORMATS_VIDEO + self._FORMATS_AUDIO
        elif video_on:
            options = self._FORMATS_VIDEO
        elif audio_on:
            options = self._FORMATS_AUDIO
        else:
            options = []

        current = self._format.currentText()
        self._format.blockSignals(True)
        self._format.clear()
        self._format.addItems(options)
        idx = self._format.findText(current)
        self._format.setCurrentIndex(idx if idx >= 0 else 0)
        self._format.blockSignals(False)

    def _sub(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return lbl

    def _update_estimate(self):
        if not self._format or not self._est_dur:
            return
        p = self.project
        fps    = p.output_fps or 16
        width  = p.output_width or 832
        height = p.output_height or 480

        # duracao de video = soma dos clips, igual ao que a timeline exibe na regua
        video_dur  = sum(c.duration for c in p.clips) if p.clips else 0.0
        clips_done = sum(1 for c in p.clips if c.status == "done")

        # tracks de audio habilitadas
        enabled_audio = {k for k, cb in self._track_checks.items() if k != "video" and cb.isChecked()}
        video_cb  = self._track_checks.get("video")
        has_video = bool(video_cb and video_cb.isChecked())
        has_audio = bool(enabled_audio)

        # itens de audio apenas das tracks marcadas
        audio_items_all     = [i for i in p.track_items if i.track != "fx"]
        audio_items_enabled = [i for i in audio_items_all if i.track in enabled_audio]
        audio_end = max((i.start_time + i.duration for i in audio_items_enabled), default=0.0)

        # duracao final = max entre video (se marcado) e audio das tracks marcadas
        candidates = []
        if has_video:
            candidates.append(video_dur)
        if has_audio:
            candidates.append(audio_end)
        export_dur = max(candidates) if candidates else 0.0

        if export_dur == 0.0:
            self._est_dur.setText("Duracao:    --")
            self._est_size.setText("Tamanho:   --")
            self._est_res.setText(f"Resolucao: {width}x{height}  {fps}fps")
            self._est_clips.setText("Nenhuma faixa selecionada")
            return

        _bitrates_video = {
            "MP4 (H.264)": 4.0, "MP4 (H.265/HEVC)": 2.5, "MOV (ProRes)": 45.0,
            "WEBM (VP9)": 2.0, "MKV (H.264)": 4.0,
        }
        _bitrates_audio_only = {
            "WAV (audio 16bit)": 1.4, "MP3 (320kbps)": 0.32, "FLAC (lossless)": 3.0,
        }
        fmt = self._format.currentText()
        is_audio_only_fmt = fmt in _bitrates_audio_only

        # formatos so-audio ignoram a track de video
        if is_audio_only_fmt:
            has_video = False
            audio_mbps = _bitrates_audio_only[fmt]
        else:
            audio_mbps = 0.17  # AAC/Opus embutido no container

        mbps     = _bitrates_video.get(fmt, 4.0)
        video_mb = (export_dur * mbps / 8) if has_video else 0
        audio_mb = (export_dur * audio_mbps) if has_audio else 0
        est_mb   = video_mb + audio_mb

        m, s = int(export_dur) // 60, export_dur % 60
        dur_detail = f"  (video {video_dur:.1f}s)" if has_audio and audio_end > video_dur else ""
        self._est_dur.setText(f"Duracao:    {m:02d}:{s:04.1f}{dur_detail}")
        if est_mb >= 1:
            self._est_size.setText(f"Tamanho:   ~{est_mb:.0f} MB")
        else:
            self._est_size.setText(f"Tamanho:   ~{est_mb*1024:.0f} KB")
        self._est_res.setText(f"Resolucao: {width}x{height}  {fps}fps")
        n_enabled = len(audio_items_enabled)
        self._est_clips.setText(f"Clips:     {clips_done}/{len(p.clips)} prontos  |  audio: {n_enabled} item(s)")

    def _on_export_pref_changed(self):
        self._refresh_format_options()
        self._persist_export_prefs()
        self._update_estimate()

    def _load_export_prefs_from_project(self):
        if not self.project or not self._format:
            return
        self._syncing_export_ui = True
        try:
            fmt = getattr(self.project, "export_format", "MP4 (H.264)")
            idx = self._format.findText(fmt)
            self._format.setCurrentIndex(idx if idx >= 0 else 0)
            saved = getattr(self.project, "export_tracks", {}) or {}
            for key, cb in self._track_checks.items():
                cb.setChecked(bool(saved.get(key, True)))
        finally:
            self._syncing_export_ui = False
        self._update_estimate()

    def _persist_export_prefs(self):
        if self._syncing_export_ui or not self.project:
            return
        self.project.export_format = self._format.currentText() if self._format else "MP4 (H.264)"
        self.project.export_tracks = {key: cb.isChecked() for key, cb in self._track_checks.items()}
        self.project.save(PROJECTS_DIR)

    def get_enabled_tracks(self):
        return [k for k, cb in self._track_checks.items() if cb.isChecked() and k != "video"]

    def _on_project_changed(self, proj):
        self.project = proj
        self._name_entry.setText(proj.name or "")
        self._load_export_prefs_from_project()

    def refresh(self, project=None):
        """Atualiza estimativas e contagens com o projeto atual."""
        if project is not None:
            self.project = project
        for key, lbl in self._count_labels.items():
            n = len(self.project.get_track_items(key)) if key != "video" else len(self.project.clips)
            lbl.setText(str(n))
        self._update_estimate()

    def _do_export(self):
        """Executa export completo."""
        import numpy as np

        name = self._name_entry.text().strip()
        if not name:
            self._status.setText("Digite um nome")
            return

        video_cb  = self._track_checks.get("video")
        has_video = bool(video_cb and video_cb.isChecked())
        has_audio = bool(self.get_enabled_tracks())
        if not has_video and not has_audio:
            self._status.setText("Selecione ao menos uma faixa para exportar")
            return

        project = self.project
        clips = sorted(project.clips, key=lambda x: x.position)
        video_dur  = sum(c.duration for c in clips) if clips else 0.0
        audio_items = [i for i in project.track_items if i.track != "fx"]
        audio_end   = max((i.start_time + i.duration for i in audio_items), default=0.0)
        total_dur   = max(video_dur, audio_end)

        if total_dur <= 0:
            self._status.setText("Nada para exportar")
            return

        if self._export_btn is not None:
            self._export_btn.setEnabled(False)
        self._status.setText("Exportando...")
        self._status.setStyleSheet(f"color: {C['primary']}; font-size: 9pt;")
        self._progress.setValue(0)

        fmt = self._format.currentText() if self._format else "MP4"
        _log.info(f"Export iniciado: '{name}' fmt={fmt} video={has_video} audio={has_audio} dur={total_dur:.1f}s")

        try:
            safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') or "video_final"
            fps    = project.output_fps or 16
            width  = project.output_width or 832
            height = project.output_height or 480

            import cv2
            from makevid.core.fx_processor import apply_fx_to_frame

            tmp_video = OUTPUTS_DIR / project.id / f"_tmp_{safe_name}.mp4"
            tmp_video.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(tmp_video), fourcc, fps, (width, height))
            fx_items    = project.get_track_items("fx")
            frame_count = 0
            total_frames = int(video_dur * fps)

            for clip in clips:
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    cap = cv2.VideoCapture(str(clip.video_path))
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame = cv2.resize(frame, (width, height))
                        t = frame_count / fps
                        if fx_items:
                            rgb = frame[:, :, ::-1]
                            rgb = apply_fx_to_frame(rgb, fx_items, t, total_dur)
                            frame = rgb[:, :, ::-1]
                        writer.write(frame)
                        frame_count += 1
                        if frame_count % 30 == 0 and total_frames > 0:
                            self._progress.setValue(int(frame_count / total_frames * 70))
                    cap.release()
                else:
                    black = np.zeros((height, width, 3), dtype=np.uint8)
                    for _ in range(int(clip.duration * fps)):
                        writer.write(black)
                        frame_count += 1
            writer.release()

            self._progress.setValue(75)
            self._status.setText("Mixando audio...")
            tmp_audio = self._mix_audio(project, total_dur, safe_name)

            self._progress.setValue(90)
            self._status.setText("Finalizando...")
            output_path = OUTPUTS_DIR / project.id / f"{safe_name}.mp4"
            has_ffmpeg  = shutil.which("ffmpeg")

            if tmp_audio and has_ffmpeg:
                cmd = [
                    "ffmpeg", "-y", "-i", str(tmp_video), "-i", str(tmp_audio),
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest",
                    str(output_path),
                ]
                subprocess.run(cmd, capture_output=True, check=True, timeout=300)
                tmp_video.unlink(missing_ok=True)
                tmp_audio.unlink(missing_ok=True)
            else:
                shutil.move(str(tmp_video), str(output_path))

            downloads = Path.home() / "Downloads"
            shutil.copy2(str(output_path), str(downloads / f"{safe_name}.mp4"))

            size_mb = output_path.stat().st_size / 1e6
            self._progress.setValue(100)
            self._status.setText(f"\u2714 Salvo! ({size_mb:.1f} MB) em Downloads")
            self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; font-weight: bold;")
            log_export(fmt, str(output_path), total_dur, size_mb)

        except Exception as e:
            log_export_error("do_export", str(e))
            self._status.setText(f"Erro: {str(e)[:50]}")
            self._status.setStyleSheet(f"color: {C['red']}; font-size: 9pt;")
            self._progress.setValue(0)
        finally:
            if self._export_btn is not None:
                self._export_btn.setEnabled(True)

    def _mix_audio(self, project, total_dur, safe_name):
        """Mixa audio de todas as tracks habilitadas."""
        import numpy as np
        import wave
        from makevid.core.audio_utils import render_audio_item

        enabled   = self.get_enabled_tracks()
        all_items = []
        for t in enabled:
            all_items.extend(project.get_track_items(t))
        if not all_items:
            return None

        sr             = 44100
        total_samples  = int(total_dur * sr)
        mix            = np.zeros((total_samples, 2), dtype=np.float32)

        for item in all_items:
            if not item.file_path or not Path(item.file_path).exists():
                continue
            try:
                raw, item_sr = render_audio_item(item)
                if raw is None or len(raw) == 0:
                    continue
                if item_sr != sr:
                    new_len = int(len(raw) * sr / item_sr)
                    raw = np.column_stack([
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 0]),
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 1]),
                    ])
                start_sample = int(item.start_time * sr)
                end_sample   = min(start_sample + len(raw), total_samples)
                audio_len    = end_sample - start_sample
                if audio_len > 0:
                    mix[start_sample:end_sample] += raw[:audio_len]
            except Exception as e:
                _log.warning(f"Audio item ignorado ({item.track}): {e}")
                continue

        mix        = np.clip(mix, -1.0, 1.0)
        audio_int16 = (mix * 32767).astype(np.int16)
        tmp_audio   = OUTPUTS_DIR / project.id / f"_tmp_{safe_name}.wav"
        with wave.open(str(tmp_audio), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())
        return tmp_audio
