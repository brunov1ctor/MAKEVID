"""Mixer Panel Qt - Painel de mixagem profissional para items de audio."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR
from makevid.core.audio_utils import process_audio_item


class MixerPanel(QWidget):
    """Painel de mixagem para um TrackItem de audio."""

    closed = Signal()
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item = None
        self._project = None
        self._sliders = {}
        self.setObjectName("mixerPanel")
        self.setMinimumWidth(0)
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
        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 6, 10, 10)
        self._content_layout.setSpacing(4)
        scroll.setWidget(self._content)
        outer.addWidget(scroll)

    def show_item(self, item, project=None):
        """Popula o mixer com controles para o item."""
        self._item = item
        self._project = project or getattr(self.window(), "project", None)
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

    def _on_keyframe_change(self, commit=False):
        """Propaga mudanças do editor e salva o projeto quando a edicao termina."""
        if commit and self._project is not None:
            self._project.save(PROJECTS_DIR)
        self.changed.emit()

    def _preview(self):
        if not self._item:
            return
        audio, sr = process_audio_item(
            self._item.file_path,
            self._collect_params(),
            self._item.volume_keyframes,
            self._item.duration,
            muted_regions=getattr(self._item, 'muted_regions', []),
        )
        if audio is not None:
            try:
                import sounddevice as sd
                sd.stop()
                sd.play(audio, samplerate=sr)
            except Exception:
                pass

    def _collect_params(self) -> dict:
        """Converte os sliders para o formato esperado por process_audio_item."""
        s = self._sliders
        return {
            "volume":   str(s["volume"].value()),
            "pan":      str(s["pan"].value()),
            "speed":    str(s["speed"].value()),
            "pitch":    str(s["pitch"].value()),
            "fade_in":  str(s["fade_in"].value()),
            "fade_out": str(s["fade_out"].value()),
            "eq_low":   str(s["eq_low"].value()),
            "eq_mid":   str(s["eq_mid"].value()),
            "eq_high":  str(s["eq_high"].value()),
            "reverb":   str(s["reverb"].value()),
        }

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
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.wheelEvent = lambda e: e.ignore()
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
