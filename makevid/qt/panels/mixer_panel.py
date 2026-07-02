"""Mixer Panel Qt - Painel de mixagem profissional para items de audio."""

import numpy as np
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal

from makevid.qt.theme import C


class MixerPanel(QWidget):
    """Painel de mixagem para um TrackItem de audio."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item = None
        self._sliders = {}
        self.setObjectName("mixerPanel")
        self.setMinimumWidth(250)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 6, 10, 4)
        lbl = QLabel("MIXER")
        lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 13pt; font-weight: bold; background: transparent; border: none;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        outer.addLayout(hdr_l)

        # Info
        self._info_label = QLabel()
        self._info_label.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        outer.addWidget(self._info_label)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 6, 10, 10)
        self._content_layout.setSpacing(4)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    def show_item(self, item):
        """Popula o mixer com controles para o item."""
        self._item = item
        self._sliders = {}
        self._info_label.setText(f"  {item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s")

        # Limpar conteudo anterior
        L = self._content_layout
        while L.count():
            child = L.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # VOLUME (0-200%)
        self._sliders["volume"] = self._add_slider(L, "VOLUME", 0, 200, 100, "%", C["cyan"])

        # PAN (-100 a 100)
        self._sliders["pan"] = self._add_slider(L, "PAN (L/R)", -100, 100, 0, "", C["cyan"],
                                                 fmt_fn=lambda v: "Centro" if v == 0 else f"L{abs(v)}%" if v < 0 else f"R{v}%")

        # FADES
        L.addWidget(self._section("FADES"))
        self._sliders["fade_in"] = self._add_slider(L, "Fade In", 0, 50, 0, "s", C["secondary"], divisor=10)
        self._sliders["fade_out"] = self._add_slider(L, "Fade Out", 0, 50, 0, "s", C["secondary"], divisor=10)

        # PITCH
        self._sliders["pitch"] = self._add_slider(L, "PITCH (semitons)", -12, 12, 0, "st", C["gold"])

        # SPEED
        self._sliders["speed"] = self._add_slider(L, "VELOCIDADE", 25, 400, 100, "", C["gold"],
                                                   fmt_fn=lambda v: f"{v/100:.2f}x")

        # EQ
        L.addWidget(self._section("EQUALIZADOR"))
        self._sliders["eq_low"] = self._add_slider(L, "Low", -12, 12, 0, "dB", C["danger"])
        self._sliders["eq_mid"] = self._add_slider(L, "Mid", -12, 12, 0, "dB", C["track_voice"])
        self._sliders["eq_high"] = self._add_slider(L, "High", -12, 12, 0, "dB", C["accent"])

        # REVERB
        self._sliders["reverb"] = self._add_slider(L, "REVERB", 0, 100, 0, "%", C["primary"])

        # KEYFRAMES DE VOLUME
        from makevid.qt.panels.keyframe_editor import KeyframeEditorWidget
        self._keyframe_editor = KeyframeEditorWidget(item)
        self._keyframe_editor.changed.connect(self._on_keyframe_change)
        L.addWidget(self._keyframe_editor)

        # PREVIEW button
        preview_btn = QPushButton("\u25b6 PREVIEW")
        preview_btn.setFixedHeight(28)
        preview_btn.setStyleSheet(
            f"background: {C['card']}; color: {C['cyan']}; font-weight: bold; "
            f"border: 1px solid {C['cyan']}; border-radius: 4px;")
        preview_btn.clicked.connect(self._preview)
        L.addWidget(preview_btn)

        L.addStretch()
        self.show()

    def _on_keyframe_change(self):
        """Salva keyframes automaticamente."""
        from makevid.config import PROJECTS_DIR
        # item.volume_keyframes ja foi modificado in-place pelo editor
        # Precisamos salvar o projeto
        # Nota: o mixer nao tem referencia direta ao projeto aqui,
        # mas o item e compartilhado - sera salvo quando o painel fechar

    def get_values(self):
        """Retorna valores atuais do mixer."""
        s = self._sliders
        divisors = {"fade_in": 10, "fade_out": 10}
        vals = {}
        for key, slider in s.items():
            v = slider.value()
            if key in divisors:
                vals[key] = v / divisors[key]
            elif key == "volume":
                vals[key] = v / 100.0
            elif key == "speed":
                vals[key] = v / 100.0
            elif key == "pan":
                vals[key] = v / 100.0
            elif key == "reverb":
                vals[key] = v / 100.0
            else:
                vals[key] = v
        return vals

    def _preview(self):
        """Reproduz audio com efeitos aplicados."""
        if not self._item:
            return
        audio, sr = self._process_audio(self._item)
        if audio is not None:
            try:
                import sounddevice as sd
                sd.stop()
                sd.play(audio, samplerate=sr)
            except Exception:
                pass

    def _process_audio(self, item):
        """Processa audio com todos os efeitos. Retorna (stereo_array, sr)."""
        import wave
        if not item.file_path or not Path(item.file_path).exists():
            return None, 0

        try:
            import soundfile as sf
            data, sr = sf.read(item.file_path, dtype="float32")
            if len(data.shape) > 1:
                audio = data.mean(axis=1)
            else:
                audio = data
        except Exception:
            return None, 0

        vals = self.get_values()

        # Speed
        if vals["speed"] != 1.0:
            new_len = int(len(audio) / vals["speed"])
            audio = np.interp(np.linspace(0, len(audio) - 1, new_len), np.arange(len(audio)), audio)

        # Pitch
        pitch = vals.get("pitch", 0)
        if pitch != 0:
            factor = 2.0 ** (pitch / 12.0)
            stretched_len = int(len(audio) / factor)
            pitched = np.interp(np.linspace(0, len(audio) - 1, stretched_len), np.arange(len(audio)), audio)
            if len(pitched) > len(audio):
                pitched = pitched[:len(audio)]
            else:
                pitched = np.pad(pitched, (0, len(audio) - len(pitched)))
            audio = pitched

        # EQ
        eq_low, eq_mid, eq_high = vals.get("eq_low", 0), vals.get("eq_mid", 0), vals.get("eq_high", 0)
        if eq_low != 0 or eq_mid != 0 or eq_high != 0:
            try:
                from scipy.signal import butter, lfilter
                b, a = butter(2, 300 / (sr / 2), btype='low')
                low = lfilter(b, a, audio)
                b, a = butter(2, 3000 / (sr / 2), btype='high')
                high = lfilter(b, a, audio)
                mid = audio - low - high
                audio = (low * 10 ** (eq_low / 20.0) +
                         mid * 10 ** (eq_mid / 20.0) +
                         high * 10 ** (eq_high / 20.0))
            except ImportError:
                pass

        # Volume
        audio = audio * vals["volume"]

        # Volume Keyframes
        if item.volume_keyframes and len(item.volume_keyframes) >= 2:
            from makevid.core.audio_utils import apply_volume_keyframes
            audio = apply_volume_keyframes(audio, sr, item.volume_keyframes, item.duration)

        # Fade In/Out
        fade_in = vals.get("fade_in", 0)
        if fade_in > 0:
            n = min(int(fade_in * sr), len(audio))
            audio[:n] *= np.linspace(0, 1, n)
        fade_out = vals.get("fade_out", 0)
        if fade_out > 0:
            n = min(int(fade_out * sr), len(audio))
            audio[-n:] *= np.linspace(1, 0, n)

        # Pan → stereo
        pan = vals.get("pan", 0)
        stereo = np.column_stack([audio * min(1.0, 1.0 - pan), audio * min(1.0, 1.0 + pan)])

        # Reverb
        reverb = vals.get("reverb", 0)
        if reverb > 0:
            reverb_len = int(0.3 * sr)
            impulse = np.exp(-np.linspace(0, 5, reverb_len))
            impulse = impulse / impulse.sum()
            wet_l = np.convolve(stereo[:, 0], impulse)[:len(audio)]
            wet_r = np.convolve(stereo[:, 1], impulse)[:len(audio)]
            stereo[:, 0] = stereo[:, 0] * (1 - reverb) + wet_l * reverb
            stereo[:, 1] = stereo[:, 1] * (1 - reverb) + wet_r * reverb

        return np.clip(stereo, -1.0, 1.0), sr

    # ============================================================
    # UI HELPERS
    # ============================================================

    def _section(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        return lbl

    def _add_slider(self, layout, label, from_, to, default, unit, color, fmt_fn=None, divisor=1):
        """Cria label + slider + valor."""
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(from_, to)
        slider.setValue(default)
        slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['border']}; height: 4px; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 12px; margin: -4px 0; border-radius: 6px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 2px; }}")
        row.addWidget(slider)

        val_lbl = QLabel(self._format_val(default, unit, fmt_fn, divisor))
        val_lbl.setFixedWidth(50)
        val_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 9pt; border: none;")
        row.addWidget(val_lbl)

        slider.valueChanged.connect(lambda v: val_lbl.setText(self._format_val(v, unit, fmt_fn, divisor)))

        layout.addLayout(row)
        return slider

    def _format_val(self, v, unit, fmt_fn, divisor):
        if fmt_fn:
            return fmt_fn(v)
        if divisor != 1:
            return f"{v/divisor:.1f}{unit}"
        return f"{v}{unit}"
