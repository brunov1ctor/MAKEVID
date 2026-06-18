"""Export Panel Qt - Configuração e execução de export."""

import re
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QProgressBar, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

from makevid.qt.theme import C
from makevid.config import OUTPUTS_DIR


class ExportPanel(QWidget):
    """Painel de configuração e execução de export."""

    closed = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setFixedWidth(300)
        self.setStyleSheet(f"background: {C['panel']};")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("EXPORTAR")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        close_btn = QPushButton("X")
        close_btn.setFixedSize(24, 20)
        close_btn.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Separador
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['gold']};")
        layout.addWidget(sep)

        # Nome
        layout.addWidget(self._sub("Nome:"))
        self._name_entry = QLineEdit(self.project.name or "meu_video")
        self._name_entry.setStyleSheet(
            f"background: #141828; color: #ffffff; border: 2px solid {C['gold']}; "
            f"border-radius: 4px; padding: 4px; font-size: 11pt; font-weight: bold;")
        layout.addWidget(self._name_entry)

        # Tracks
        layout.addWidget(self._sub("Tracks:"))
        tracks_frame = QFrame()
        tracks_frame.setStyleSheet(f"background: {C['card']}; border-radius: 4px;")
        tracks_layout = QVBoxLayout(tracks_frame)
        tracks_layout.setContentsMargins(6, 6, 6, 6)
        self._track_checks = {}
        for key, label, color in [
            ("video", "VIDEO", "#3399ff"), ("voice", "VOICE", "#ff9944"),
            ("sfx", "SFX", "#44cc88"), ("music", "MUSIC", "#cc44aa"),
            ("audio", "AUDIO", "#0ac8b9"),
        ]:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {C['text']}; font-family: Consolas; font-size: 9pt; font-weight: bold;")
            tracks_layout.addWidget(cb)
            self._track_checks[key] = cb
        layout.addWidget(tracks_frame)

        # Formato
        layout.addWidget(self._sub("Formato:"))
        self._format = QComboBox()
        self._format.addItems([
            "MP4 (H.264)", "MP4 (H.265/HEVC)", "MOV (ProRes)",
            "WEBM (VP9)", "MKV (H.264)", "WAV (audio 16bit)",
            "MP3 (320kbps)", "FLAC (lossless)",
        ])
        self._format.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; "
            f"border-radius: 3px; padding: 2px 6px;")
        layout.addWidget(self._format)

        # Progress
        self._progress = QProgressBar()
        self._progress.setFixedHeight(14)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            f"QProgressBar {{ background: #1a1a2e; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {C['gold']}; border-radius: 4px; }}")
        layout.addWidget(self._progress)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Botão exportar
        self._export_btn = QPushButton("EXPORTAR")
        self._export_btn.setFixedHeight(36)
        self._export_btn.setStyleSheet(
            f"background: {C['gold']}; color: #0a0a0f; font-size: 12pt; "
            f"font-weight: bold; border-radius: 4px;")
        self._export_btn.clicked.connect(self._do_export)
        layout.addWidget(self._export_btn)

        layout.addStretch()

    def _sub(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return lbl

    def get_enabled_tracks(self):
        return [k for k, cb in self._track_checks.items() if cb.isChecked() and k != "video"]

    def _do_export(self):
        """Executa export completo."""
        import time as _time
        import numpy as np

        name = self._name_entry.text().strip()
        if not name:
            self._status.setText("Digite um nome")
            return

        project = self.project
        clips = sorted(project.clips, key=lambda x: x.position)
        total_dur = project.total_duration()

        if total_dur <= 0:
            self._status.setText("Nada para exportar")
            return

        self._export_btn.setEnabled(False)
        self._status.setText("Exportando...")
        self._status.setStyleSheet(f"color: {C['gold']}; font-size: 9pt;")
        self._progress.setValue(0)

        try:
            safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') or "video_final"
            fps = project.output_fps or 16
            width = project.output_width or 832
            height = project.output_height or 480

            import cv2
            from makevid.core.fx_processor import apply_fx_to_frame

            tmp_video = OUTPUTS_DIR / project.id / f"_tmp_{safe_name}.mp4"
            tmp_video.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(tmp_video), fourcc, fps, (width, height))
            fx_items = project.get_track_items("fx")
            frame_count = 0
            total_frames = int(total_dur * fps)

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

            # Audio mix
            self._progress.setValue(75)
            self._status.setText("Mixando audio...")
            tmp_audio = self._mix_audio(project, total_dur, safe_name)

            # Combinar
            self._progress.setValue(90)
            self._status.setText("Finalizando...")
            output_path = OUTPUTS_DIR / project.id / f"{safe_name}.mp4"
            has_ffmpeg = shutil.which("ffmpeg")

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

            # Copiar para Downloads
            downloads = Path.home() / "Downloads"
            shutil.copy2(str(output_path), str(downloads / f"{safe_name}.mp4"))

            size_mb = output_path.stat().st_size / 1e6
            self._progress.setValue(100)
            self._status.setText(f"\u2714 Salvo! ({size_mb:.1f} MB) em Downloads")
            self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; font-weight: bold;")

        except Exception as e:
            self._status.setText(f"Erro: {str(e)[:50]}")
            self._status.setStyleSheet(f"color: {C['red']}; font-size: 9pt;")
            self._progress.setValue(0)
        finally:
            self._export_btn.setEnabled(True)

    def _mix_audio(self, project, total_dur, safe_name):
        """Mixa audio de todas as tracks habilitadas."""
        import numpy as np
        import wave

        enabled = self.get_enabled_tracks()
        all_items = []
        for t in enabled:
            all_items.extend(project.get_track_items(t))
        if not all_items:
            return None

        sr = 44100
        total_samples = int(total_dur * sr)
        mix = np.zeros((total_samples, 2), dtype=np.float32)

        for item in all_items:
            if not item.file_path or not Path(item.file_path).exists():
                continue
            try:
                import soundfile as sf
                data, item_sr = sf.read(item.file_path, dtype="float32")
                if len(data.shape) == 1:
                    raw = np.column_stack([data, data])
                else:
                    raw = data if data.shape[1] == 2 else np.column_stack([data[:, 0], data[:, 0]])
                if item_sr != sr:
                    new_len = int(len(raw) * sr / item_sr)
                    raw = np.column_stack([
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 0]),
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 1]),
                    ])
                # Volume keyframes
                if item.volume_keyframes and len(item.volume_keyframes) >= 2:
                    from makevid.core.audio_utils import apply_volume_keyframes
                    raw = apply_volume_keyframes(raw, sr, item.volume_keyframes, item.duration)
                start_sample = int(item.start_time * sr)
                end_sample = min(start_sample + len(raw), total_samples)
                audio_len = end_sample - start_sample
                if audio_len > 0:
                    mix[start_sample:end_sample] += raw[:audio_len]
            except Exception:
                continue

        mix = np.clip(mix, -1.0, 1.0)
        audio_int16 = (mix * 32767).astype(np.int16)
        tmp_audio = OUTPUTS_DIR / project.id / f"_tmp_{safe_name}.wav"
        with wave.open(str(tmp_audio), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())
        return tmp_audio
