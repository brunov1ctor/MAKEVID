"""Recorder + TTS Qt - Gravação de microfone e geração de voz."""

import time as _time
import threading
import wave
import collections
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen

from makevid.qt.theme import C
from makevid.qt.widgets import GlassButton
from makevid.config import AUDIO_DIR, PROJECTS_DIR


class _LiveWaveformWidget(QWidget):
    """Waveform em tempo real — desenha últimos blocos de áudio."""

    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._color = QColor(color or C["track_voice"])
        self._data = np.zeros(300, dtype=np.float32)
        self._static_mode = False
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def push_block(self, block):
        if len(block) == 0:
            return
        samples = block.flatten().astype(np.float32) / 32768.0
        n_points = min(10, len(samples))
        chunk_size = max(1, len(samples) // n_points)
        envelope = []
        for i in range(0, len(samples), chunk_size):
            seg = samples[i:i+chunk_size]
            envelope.append(float(np.abs(seg).max()))
        n = len(envelope)
        self._data = np.roll(self._data, -n)
        self._data[-n:] = envelope[:n]
        self._static_mode = False
        self.update()

    def set_static(self, audio_data):
        if len(audio_data) == 0:
            return
        samples = audio_data.flatten().astype(np.float32) / 32768.0
        n_points = 300
        chunk_size = max(1, len(samples) // n_points)
        envelope = []
        for i in range(0, len(samples), chunk_size):
            seg = samples[i:i+chunk_size]
            envelope.append(float(np.abs(seg).max()))
        self._data = np.zeros(300, dtype=np.float32)
        self._data[:len(envelope)] = envelope[:300]
        self._static_mode = True
        self.update()

    def clear(self):
        self._data = np.zeros(300, dtype=np.float32)
        self._static_mode = False
        self.update()

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(11, 18, 32, 220))
        p.setPen(QPen(self._color, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(0, 0, w - 1, h - 1, 4, 4)
        mid = h / 2
        n = len(self._data)
        bar_w = max(1.0, (w - 8) / n)
        if np.max(self._data) < 0.001:
            p.setPen(QPen(QColor(C['text3']), 1, Qt.DashLine))
            p.drawLine(8, int(mid), w - 8, int(mid))
            return
        peak = max(float(np.max(self._data)), 0.01)
        color = QColor(self._color)
        color.setAlpha(210)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        for i in range(n):
            amp = self._data[i] / peak
            x = int(4 + i * bar_w)
            bar_h = max(0, int(amp * (mid - 4)))
            if bar_h > 0:
                p.drawRect(x, int(mid - bar_h), max(1, int(bar_w) - 1), bar_h * 2)


class RecorderPanel(QWidget):
    """Gravador de microfone com waveform em tempo real."""

    closed = Signal()
    recorded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recording = False
        self._frames = []
        self._last_block = None
        self._stream = None
        self._start_time = 0
        self._target_track = "voice"
        self._project = None
        self._timeline = None
        self._color = C["track_voice"]

        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(50)
        self._ui_timer.timeout.connect(self._tick)

        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        self._title_lbl = QLabel("\u25cf GRAVAR")
        self._title_lbl.setStyleSheet(f"color: {C['track_voice']}; font-size: 13pt; font-weight: bold;")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Timer display
        self._time_label = QLabel("00:00.0")
        self._time_label.setAlignment(Qt.AlignCenter)
        self._time_label.setStyleSheet(f"color: {C['text']}; font-family: Consolas; font-size: 28pt; font-weight: bold;")
        layout.addWidget(self._time_label)

        # Waveform em tempo real
        self._waveform = _LiveWaveformWidget(C["track_voice"])
        layout.addWidget(self._waveform)

        # Level meter
        self._level = QProgressBar()
        self._level.setFixedHeight(8)
        self._level.setRange(0, 100)
        self._level.setValue(0)
        self._level.setTextVisible(False)
        self._level.setStyleSheet(
            f"QProgressBar {{ background: {C['border']}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {C['track_voice']}; border-radius: 4px; }}")
        layout.addWidget(self._level)

        # Info labels
        info_row = QHBoxLayout()
        self._info_format = QLabel("44100Hz / 16bit / Mono")
        self._info_format.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt;")
        info_row.addWidget(self._info_format)
        info_row.addStretch()
        self._info_size = QLabel("")
        self._info_size.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt;")
        info_row.addWidget(self._info_size)
        layout.addLayout(info_row)

        # Status
        self._status = QLabel("Pronto para gravar")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        layout.addWidget(self._status)

        # REC button
        self._rec_btn = GlassButton("● REC", accent=True, height=44)
        self._rec_btn.clicked.connect(self._toggle_rec)
        layout.addWidget(self._rec_btn)

        layout.addStretch()

    def set_context(self, project, timeline, track="voice"):
        self._project = project
        self._timeline = timeline
        self._target_track = track
        self._color = {"voice": C["track_voice"], "sfx": C["track_sfx"], "music": C["track_music"], "audio": C["track_audio"]}.get(track, C["accent"])
        self._title_lbl.setText(f"\u25cf GRAVAR ({track.upper()})")
        self._title_lbl.setStyleSheet(f"color: {self._color}; font-size: 13pt; font-weight: bold;")
        self._waveform.set_color(self._color)
        self._waveform.clear()
        self._level.setValue(0)
        self._level.setStyleSheet(
            f"QProgressBar {{ background: {C['border']}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {self._color}; border-radius: 4px; }}")
        self._status.setText(f"Track: {track.upper()}")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        self._time_label.setText("00:00.0")
        self._info_size.setText("")

    def _toggle_rec(self):
        if self._recording:
            self._stop_rec()
        else:
            self._start_rec()

    def _start_rec(self):
        try:
            import sounddevice as sd
        except ImportError:
            self._status.setText("Erro: pip install sounddevice")
            self._status.setStyleSheet(f"color: {C['danger']}; font-size: 9pt;")
            return

        self._recording = True
        self._frames = []
        self._last_block = None
        self._start_time = _time.time()
        self._waveform.clear()
        self._status.setText("\u25cf GRAVANDO...")
        self._status.setStyleSheet(f"color: {C['danger']}; font-size: 9pt; font-weight: bold;")
        self._rec_btn.setText("■ PARAR")
        self._rec_btn.setStyleSheet("background: transparent; border: none;")
        self._ui_timer.start()

        def callback(indata, frames, t, status):
            if self._recording:
                self._frames.append(indata.copy())
                self._last_block = indata.copy()

        self._stream = sd.InputStream(
            samplerate=44100, channels=1, dtype="int16", callback=callback)
        self._stream.start()

    def _tick(self):
        if not self._recording:
            return
        elapsed = _time.time() - self._start_time
        m = int(elapsed) // 60
        s = elapsed % 60
        self._time_label.setText(f"{m:02d}:{s:04.1f}")
        if self._last_block is not None:
            block = self._last_block
            self._last_block = None
            self._waveform.push_block(block)
            peak = float(np.abs(block).max())
            level = int(min(100, peak / 32768.0 * 300))
            self._level.setValue(level)
        n_samples = sum(len(f) for f in self._frames)
        size_kb = (n_samples * 2) / 1024
        if size_kb > 1024:
            self._info_size.setText(f"{size_kb/1024:.1f} MB")
        else:
            self._info_size.setText(f"{size_kb:.0f} KB")

    def _stop_rec(self):
        self._recording = False
        self._ui_timer.stop()
        self._level.setValue(0)

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            self._status.setText("Nenhum audio capturado")
            self._status.setStyleSheet(f"color: {C['danger']}; font-size: 9pt;")
            self._reset_btn()
            return

        audio_data = np.concatenate(self._frames, axis=0)
        duration = len(audio_data) / 44100
        self._waveform.set_static(audio_data)

        out_dir = AUDIO_DIR / self._project.id
        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / f"rec_{int(_time.time())}.wav"

        with wave.open(str(filepath), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(audio_data.tobytes())

        size_kb = filepath.stat().st_size / 1024
        self._info_size.setText(f"{size_kb:.0f} KB")

        existing = self._project.get_track_items(self._target_track)
        if existing:
            last = max(existing, key=lambda i: i.start_time + i.duration)
            start = last.start_time + last.duration
        else:
            start = self._timeline.playhead_pos if self._timeline else 0

        self._project.add_track_item(
            name=f"Gravacao ({duration:.1f}s)", track=self._target_track,
            start_time=start, duration=duration, file_path=str(filepath),
            params={"block_name": f"\U0001f3a7 Gravacao"})
        self._project.save(PROJECTS_DIR)

        self._status.setText(f"\u2714 Salvo! {duration:.1f}s \u2192 {self._target_track.upper()} | {filepath.name}")
        self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")
        self._time_label.setText(f"{int(duration)//60:02d}:{duration%60:04.1f}")
        self._rec_btn.setText("● GRAVAR NOVO")
        self._rec_btn.setStyleSheet("background: transparent; border: none;")
        self.recorded.emit()
        QTimer.singleShot(200, self._refresh_browser)

    def _reset_btn(self):
        self._rec_btn.setText("● REC")
        self._rec_btn.setStyleSheet("background: transparent; border: none;")

    def _refresh_browser(self):
        """Atualiza AudioBrowserPanel se estiver visível."""
        try:
            top = self.window()
            if hasattr(top, 'audio_browser'):
                top.audio_browser.refresh()
        except Exception:
            pass


class TTSPanel(QWidget):
    """Gerador de voz TTS (text-to-speech)."""

    closed = Signal()
    generated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project = None
        self._timeline = None
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("\U0001f3a4 GERAR VOZ")
        lbl.setStyleSheet(f"color: {C['track_voice']}; font-size: 13pt; font-weight: bold;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # Texto
        layout.addWidget(self._lbl("Texto:"))
        self._text = QTextEdit()
        self._text.setMinimumHeight(80)
        self._text.setPlaceholderText("Digite o texto para gerar voz...")
        self._text.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 2px solid {C['track_voice']}; "
            f"border-radius: 6px; font-size: 10pt;")
        layout.addWidget(self._text)

        # Waveform (resultado)
        self._waveform = _LiveWaveformWidget(C["track_voice"])
        self._waveform.setMinimumHeight(50)
        layout.addWidget(self._waveform)

        # Status
        self._status = QLabel("Pronto")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        layout.addWidget(self._status)

        # Progress
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            f"QProgressBar {{ background: {C['card']}; border: none; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background: {C['track_voice']}; border-radius: 3px; }}")
        layout.addWidget(self._progress)

        # Gerar button
        gen_btn = GlassButton("GERAR", accent=True, height=36)
        gen_btn.clicked.connect(self._generate)
        layout.addWidget(gen_btn)

        layout.addStretch()

    def set_context(self, project, timeline):
        self._project = project
        self._timeline = timeline
        self._waveform.clear()

    def _generate(self):
        text = self._text.toPlainText().strip()
        if not text:
            return

        self._status.setText("Gerando...")
        self._status.setStyleSheet(f"color: {C['track_voice']}; font-size: 9pt;")
        self._progress.setValue(30)
        self._waveform.clear()

        def run():
            try:
                from makevid.core.tts_provider import generate_voice
                out_dir = AUDIO_DIR / self._project.id
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f"tts_{int(_time.time())}.wav"
                result = generate_voice(text, path)

                if result:
                    with wave.open(str(path), "r") as wf:
                        dur = wf.getnframes() / wf.getframerate()
                    self._load_waveform(str(path))
                    existing = self._project.get_track_items("voice")
                    if existing:
                        last = max(existing, key=lambda i: i.start_time + i.duration)
                        start = last.start_time + last.duration
                    else:
                        start = self._timeline.playhead_pos if self._timeline else 0
                    self._project.add_track_item(
                        name=text[:20], track="voice",
                        start_time=start, duration=dur, file_path=str(path),
                        params={"text": text, "block_name": f"\U0001f5e3 {text[:15]}"})
                    self._project.save(PROJECTS_DIR)
                    QTimer.singleShot(0, lambda: self._on_done(dur))
                else:
                    QTimer.singleShot(0, self._on_error)
            except Exception as e:
                QTimer.singleShot(0, lambda: self._on_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _load_waveform(self, filepath):
        try:
            import soundfile as sf
            data, sr = sf.read(filepath, dtype="int16")
            if len(data.shape) > 1:
                data = data.mean(axis=1).astype(np.int16)
            QTimer.singleShot(0, lambda d=data: self._waveform.set_static(d))
        except Exception:
            pass

    def _on_done(self, dur):
        self._status.setText(f"\u2714 Pronto! {dur:.1f}s")
        self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")
        self._progress.setValue(100)
        self._text.clear()
        self.generated.emit()

    def _on_error(self, msg="Erro na geração"):
        self._status.setText(f"Erro: {msg[:40]}" if msg else "Erro na geração")
        self._status.setStyleSheet(f"color: {C['danger']}; font-size: 9pt;")
        self._progress.setValue(0)

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return l
