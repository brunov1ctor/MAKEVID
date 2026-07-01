"""Track Editor Panel Qt - Editor de layers de audio por track (voice/sfx/music/audio)."""

import time as _time
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPainter, QColor, QPen

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR


TRACK_COLORS = {
    "voice": C["track_voice"], "sfx": C["track_sfx"],
    "music": C["track_music"], "audio": C["track_audio"]
}
TRACK_TITLES = {
    "voice": "\U0001f3a4 VOZ", "sfx": "\U0001f50a SFX",
    "music": "\U0001f3b5 MUSICA", "audio": "\U0001f3a7 AUDIO"
}


class TrackEditorPanel(QWidget):
    """Editor de layers para tracks de audio."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item = None
        self._project = None
        self._playing = {}  # item_id -> bool
        self._layer_refs = {}
        self.setMinimumWidth(250)
        self.setObjectName("trackEditorPanel")
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_shell()

    def _build_shell(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

    def show_item(self, item, project):
        """Popula editor com layers do grupo do item."""
        self._item = item
        self._project = project
        self._playing = {}
        self._layer_refs = {}  # item_id -> {waveform, time_lbl, play_btn, color}
        color = TRACK_COLORS.get(item.track, C["cyan"])
        title = TRACK_TITLES.get(item.track, "AUDIO")

        # Limpar tudo
        while self._outer.count():
            child = self._outer.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 6, 10, 4)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: bold; background: transparent; border: none;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self._close)
        hdr_l.addWidget(close_btn)
        self._outer.addLayout(hdr_l)

        # Info
        info = QLabel(f"  {item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s")
        info.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        self._outer.addWidget(info)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        L = QVBoxLayout(content)
        L.setContentsMargins(10, 6, 10, 10)
        L.setSpacing(4)
        scroll.setWidget(content)
        self._outer.addWidget(scroll)

        # Layers
        group = self._get_group(item)
        layers_lbl = QLabel(f"LAYERS ({len(group)})")
        layers_lbl.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold; border: none;")
        L.addWidget(layers_lbl)

        for layer_item in sorted(group, key=lambda i: i.start_time):
            self._build_layer(L, layer_item, color)

        # Botões globais
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {color};")
        L.addWidget(sep)

        # Loop checkbox
        from PySide6.QtWidgets import QCheckBox
        self._loop_cb = QCheckBox("  Loop")
        self._loop_cb.setStyleSheet(
            f"QCheckBox {{ color: {C['text']}; font-size: 9pt; font-weight: bold; spacing: 6px; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 2px solid {color}; background: {C['card']}; }}"
            f"QCheckBox::indicator:checked {{ background: {color}; border: 2px solid {color}; }}"
            f"QCheckBox::indicator:hover {{ border: 2px solid {C['secondary']}; }}")
        L.addWidget(self._loop_cb)

        # Play All
        play_all_btn = QPushButton("\u25b6 PLAY CONJUNTO")
        play_all_btn.setFixedHeight(28)
        play_all_btn.setStyleSheet(
            f"background: {C['card']}; color: {color}; font-weight: bold; font-size: 10pt; "
            f"border: 2px solid {color}; border-radius: 5px;")
        play_all_btn.clicked.connect(lambda: self._play_all(group, color))
        L.addWidget(play_all_btn)

        # Renomear
        rename_btn = QPushButton("\u270f RENOMEAR")
        rename_btn.setFixedHeight(26)
        rename_btn.setStyleSheet(
            f"background: {C['card']}; color: {C['text']}; font-weight: bold; "
            f"border: 1px solid {color}; border-radius: 4px;")
        rename_btn.clicked.connect(lambda: self._rename_item(item, L))
        L.addWidget(rename_btn)

        # Salvar
        save_btn = QPushButton("SALVAR")
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet(
            f"background: {color}; color: {C['dark_text']}; font-weight: bold; font-size: 10pt; border-radius: 5px;")
        save_btn.clicked.connect(lambda: project.save(PROJECTS_DIR))
        L.addWidget(save_btn)

        L.addStretch()
        self.show()

    def _build_layer(self, layout, item, color):
        """Constroi um layer com header colapsavel, waveform, controles e botões."""
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['dark']}; border: 2px solid {color}; border-radius: 6px;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(4, 4, 4, 6)
        fl.setSpacing(3)

        # Header (colapsavel) - fundo totalmente colorido
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(4, 3, 4, 3)
        hdr_layout.setSpacing(4)
        collapse_btn = QPushButton("\u25bc")
        collapse_btn.setFixedSize(18, 18)
        collapse_btn.setStyleSheet(f"background: transparent; color: {C['dark_text']}; font-weight: bold; border: none;")
        hdr_layout.addWidget(collapse_btn)
        name_lbl = QLabel(f"\u266b {item.name[:20]}")
        name_lbl.setStyleSheet(f"color: {C['dark_text']}; font-weight: bold; font-size: 9pt; border: none;")
        name_lbl.setCursor(Qt.PointingHandCursor)
        name_lbl.mouseDoubleClickEvent = lambda e, i=item, l=name_lbl, f=hdr_frame, c=color: self._inline_rename_layer(i, l, f, c)
        hdr_layout.addWidget(name_lbl)
        hdr_layout.addStretch()
        dur_lbl = QLabel(f"{item.duration:.1f}s")
        dur_lbl.setStyleSheet(f"color: {C['dark_text']}; font-family: Consolas; font-size: 9pt; font-weight: bold; border: none;")
        hdr_layout.addWidget(dur_lbl)
        del_btn = QPushButton("X")
        del_btn.setObjectName("closeBtn")
        del_btn.setFixedSize(18, 18)
        del_btn.clicked.connect(lambda checked=False, i=item: self._delete_layer(i))
        hdr_layout.addWidget(del_btn)
        fl.addWidget(hdr_frame)

        # Content (colapsavel)
        content_widget = QWidget()
        cl = QVBoxLayout(content_widget)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(3)

        # Waveform
        waveform = _WaveformWidget(item, color)
        waveform.setFixedHeight(44)
        waveform.seek_requested.connect(lambda ratio, i=item, c=color: self._seek_play(i, ratio, c))
        cl.addWidget(waveform)

        # Tempo label
        time_lbl = QLabel(f"0.0s / {item.duration:.1f}s")
        time_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        cl.addWidget(time_lbl)

        # Play + Duplicate row
        play_row = QHBoxLayout()
        play_btn = QPushButton("\u25b6 Play")
        play_btn.setFixedSize(60, 22)
        play_btn.setStyleSheet(
            f"background: {color}; color: {C['dark_text']}; font-weight: bold; border-radius: 4px;")
        play_btn.clicked.connect(lambda checked=False, i=item, b=play_btn, c=color: self._toggle_play(i, b, c))
        play_row.addWidget(play_btn)
        dup_btn = QPushButton("Duplicar")
        dup_btn.setFixedSize(55, 22)
        dup_btn.setStyleSheet(f"background: {C['card']}; color: {C['text2']}; font-size: 8pt; font-weight: bold; border-radius: 4px;")
        dup_btn.clicked.connect(lambda checked=False, i=item: self._duplicate(i))
        play_row.addWidget(dup_btn)
        play_row.addStretch()
        start_lbl = QLabel(f"Inicio: {item.start_time:.1f}s")
        start_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        play_row.addWidget(start_lbl)
        cl.addLayout(play_row)

        # Sliders: VOL, PAN, FADE IN, FADE OUT, REVERB, ROOM, SPEED
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background: {C['bg']}; border: 1px solid {C['border']}; border-radius: 4px;")
        pl = QVBoxLayout(params_frame)
        pl.setContentsMargins(6, 4, 6, 4)
        pl.setSpacing(1)
        vol = int(item.params.get("volume", 80))
        self._add_param_slider(pl, "VOL", 0, 200, vol, "%", color, item, "volume")
        pan = int(item.params.get("pan", 0))
        self._add_param_slider(pl, "PAN", -100, 100, pan, "", color, item, "pan")
        fi = int(item.params.get("fade_in", 0))
        self._add_param_slider(pl, "FADE IN", 0, 100, fi, "%", C["secondary"], item, "fade_in")
        fo = int(item.params.get("fade_out", 0))
        self._add_param_slider(pl, "FADE OUT", 0, 100, fo, "%", C["secondary"], item, "fade_out")
        reverb = int(item.params.get("reverb", 0))
        self._add_param_slider(pl, "REVERB", 0, 100, reverb, "%", C["primary"], item, "reverb")
        room = int(item.params.get("room", 0))
        self._add_param_slider(pl, "ROOM", 0, 100, room, "%", C["primary"], item, "room")
        speed = int(item.params.get("speed", 100))
        self._add_param_slider(pl, "SPEED", 50, 200, speed, "%", C["accent"], item, "speed")
        cl.addWidget(params_frame)

        fl.addWidget(content_widget)

        # Collapse toggle
        def _toggle_collapse():
            if content_widget.isVisible():
                content_widget.hide()
                collapse_btn.setText("\u25b6")
            else:
                content_widget.show()
                collapse_btn.setText("\u25bc")
        collapse_btn.clicked.connect(_toggle_collapse)

        # Store refs for playhead animation
        self._layer_refs[item.id] = {
            "waveform": waveform, "time_lbl": time_lbl,
            "play_btn": play_btn, "color": color
        }

        layout.addWidget(frame)

    def _add_param_slider(self, layout, label, from_, to, default, unit, color, item, param_key):
        """Slider compacto otimizado — label + slider + valor em 1 linha minimal."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        lbl = QLabel(label)
        lbl.setFixedWidth(52)
        lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; font-weight: bold; border: none;")
        row.addWidget(lbl)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(from_, to)
        slider.setValue(default)
        slider.setFixedHeight(14)
        slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['border']}; height: 3px; border-radius: 1px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 8px; height: 8px; margin: -3px 0; border-radius: 4px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 1px; }}")
        row.addWidget(slider)

        val_lbl = QLabel(f"{default}{unit}")
        val_lbl.setFixedWidth(38)
        val_lbl.setStyleSheet(f"color: {C['text']}; font-family: Consolas; font-size: 8pt; font-weight: bold; border: none;")
        row.addWidget(val_lbl)

        def on_change(v):
            val_lbl.setText(f"{v}{unit}")
            item.params[param_key] = str(v)

        slider.valueChanged.connect(on_change)
        layout.addLayout(row)

    def _inline_rename_layer(self, item, name_lbl, hdr_frame, color):
        """Double-click no nome: substitui label por entry inline para renomear o layer."""
        name_lbl.hide()
        entry = QLineEdit(item.name)
        entry.setFixedHeight(20)
        entry.setStyleSheet(
            f"background: {C['text']}; color: {C['dark_text']}; font-weight: bold; font-size: 9pt; "
            f"border: 1px solid {color}; border-radius: 3px; padding: 0 4px;")
        hdr_frame.layout().insertWidget(1, entry)
        entry.setFocus()
        entry.selectAll()

        def _confirm():
            new_name = entry.text().strip()
            if new_name:
                item.name = new_name
                self._project.save(PROJECTS_DIR)
            entry.deleteLater()
            name_lbl.setText(f"\u266b {item.name[:20]}")
            name_lbl.show()

        entry.returnPressed.connect(_confirm)
        entry.editingFinished.connect(_confirm)

    # ============================================================
    # ACTIONS
    # ============================================================

    def _toggle_play(self, item, btn, color):
        """Play/Pause de um layer individual. Pause mantém posição."""
        item_id = item.id
        if self._playing.get(item_id, False):
            # PAUSE: para imediatamente sem resetar
            try:
                import sounddevice as sd
                sd.stop()
            except Exception:
                pass
            self._playing[item_id] = False
            btn.setText("\u25b6 Play")
            btn.setStyleSheet(f"background: {color}; color: {C['dark_text']}; font-weight: bold; border-radius: 4px;")
            # NÃO reseta playhead — mantém posição visual
        else:
            self._start_play(item, btn, color)

    def _start_play(self, item, btn, color):
        """Reproduz audio do layer."""
        if not item.file_path or not Path(item.file_path).exists():
            return
        try:
            import sounddevice as sd
            import numpy as np
            import soundfile as sf

            data, sr = sf.read(item.file_path, dtype="float32")
            if len(data.shape) == 1:
                data = np.column_stack([data, data])

            vol = int(item.params.get("volume", 80)) / 100.0
            data *= vol

            pan = int(item.params.get("pan", 0)) / 100.0
            if pan != 0:
                data[:, 0] *= max(0, 1.0 - pan)
                data[:, 1] *= max(0, 1.0 + pan)

            # Speed
            speed = int(item.params.get("speed", 100)) / 100.0
            play_sr = int(sr * speed) if speed > 0 else sr

            # Loop
            loop = getattr(self, '_loop_cb', None) and self._loop_cb.isChecked()
            if loop:
                duration = len(data) / play_sr
                repeats = max(2, int(60.0 / max(0.1, duration)))
                data = np.tile(data, (repeats, 1))

            audio = np.ascontiguousarray(np.clip(data, -1, 1).astype(np.float32))
            sd.stop()
            sd.play(audio, samplerate=play_sr)

            self._playing[item.id] = True
            btn.setText("\u25a0 Stop")
            btn.setStyleSheet(f"background: {C['danger']}; color: {C['text']}; font-weight: bold; border-radius: 4px;")

            # Iniciar animação do playhead
            self._animate_playhead(item.id, 0.0, item.duration)
        except Exception:
            pass

    def _stop_play(self, item_id, btn, color):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self._playing[item_id] = False
        btn.setText("\u25b6 Play")
        btn.setStyleSheet(f"background: {color}; color: {C['dark_text']}; font-weight: bold; border-radius: 4px;")
        # Limpar playhead
        refs = self._layer_refs.get(item_id)
        if refs:
            refs["waveform"].set_playhead(-1)

    def _play_all(self, group, color):
        """Reproduz todos os layers mixados."""
        import threading
        import numpy as np

        def run():
            try:
                import sounddevice as sd
                import soundfile as sf
                sr = 44100
                base = min(i.start_time for i in group)
                end = max(i.start_time + i.duration for i in group)
                total_samples = int((end - base) * sr)
                if total_samples <= 0:
                    return
                mix = np.zeros((total_samples, 2), dtype=np.float32)
                for item in group:
                    if not item.file_path or not Path(item.file_path).exists():
                        continue
                    data, item_sr = sf.read(item.file_path, dtype="float32")
                    if len(data.shape) == 1:
                        data = np.column_stack([data, data])
                    if item_sr != sr:
                        new_len = int(len(data) * sr / item_sr)
                        data = np.column_stack([
                            np.interp(np.linspace(0, len(data)-1, new_len), np.arange(len(data)), data[:, 0]),
                            np.interp(np.linspace(0, len(data)-1, new_len), np.arange(len(data)), data[:, 1]),
                        ])
                    vol = int(item.params.get("volume", 80)) / 100.0
                    data *= vol
                    s = int((item.start_time - base) * sr)
                    e = min(s + len(data), total_samples)
                    mix[s:e] += data[:e-s]
                sd.stop()
                sd.play(np.ascontiguousarray(np.clip(mix, -1, 1).astype(np.float32)), samplerate=sr)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _duplicate(self, item):
        """Duplica layer."""
        self._project.add_track_item(
            name=item.name, track=item.track,
            start_time=item.start_time, duration=item.duration,
            file_path=item.file_path, params=dict(item.params),
            clip_index=item.clip_index)
        self._project.save(PROJECTS_DIR)
        self.show_item(self._item, self._project)

    def _delete_layer(self, item):
        """Remove layer."""
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self._project.remove_track_item(item.id)
        self._project.save(PROJECTS_DIR)
        remaining = self._project.get_track_items(item.track)
        if remaining:
            self.show_item(remaining[0], self._project)
        else:
            self._close()

    def _close(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self.closed.emit()
        self.hide()

    # ============================================================
    # HELPERS
    # ============================================================

    def _get_group(self, item):
        """Retorna items do mesmo grupo (clip_index ou posição)."""
        all_track = self._project.get_track_items(item.track)
        if item.clip_index >= 0:
            return [i for i in all_track if i.clip_index == item.clip_index]
        return [i for i in all_track if abs(i.start_time - item.start_time) < 0.05]

    def _seek_play(self, item, ratio, color):
        """Play a partir de uma posição na waveform."""
        if not item.file_path or not Path(item.file_path).exists():
            return
        try:
            import sounddevice as sd
            import numpy as np
            import soundfile as sf

            data, sr = sf.read(item.file_path, dtype="float32")
            if len(data.shape) == 1:
                data = np.column_stack([data, data])
            vol = int(item.params.get("volume", 80)) / 100.0
            data *= vol
            start_sample = int(ratio * len(data))
            audio = np.ascontiguousarray(np.clip(data[start_sample:], -1, 1).astype(np.float32))
            sd.stop()
            sd.play(audio, samplerate=sr)
            self._playing[item.id] = True
            refs = self._layer_refs.get(item.id)
            if refs:
                refs["play_btn"].setText("\u25a0 Stop")
                refs["play_btn"].setStyleSheet(f"background: {C['danger']}; color: {C['text']}; font-weight: bold; border-radius: 4px;")
                self._animate_playhead(item.id, ratio, item.duration * (1 - ratio))
        except Exception:
            pass

    def _animate_playhead(self, item_id, start_ratio, duration):
        """Anima playhead na waveform em tempo real."""
        refs = self._layer_refs.get(item_id)
        if not refs:
            return
        waveform = refs["waveform"]
        time_lbl = refs["time_lbl"]
        start_time = _time.time()
        total_dur = duration

        def _tick():
            if not self._playing.get(item_id, False):
                waveform.set_playhead(-1)
                return
            elapsed = _time.time() - start_time
            if elapsed >= total_dur:
                self._playing[item_id] = False
                waveform.set_playhead(-1)
                refs["play_btn"].setText("\u25b6 Play")
                refs["play_btn"].setStyleSheet(f"background: {refs['color']}; color: {C['dark_text']}; font-weight: bold; border-radius: 4px;")
                time_lbl.setText(f"{waveform._item.duration:.1f}s / {waveform._item.duration:.1f}s")
                return
            ratio = start_ratio + (elapsed / waveform._item.duration)
            waveform.set_playhead(min(1.0, ratio))
            current = start_ratio * waveform._item.duration + elapsed
            time_lbl.setText(f"{current:.1f}s / {waveform._item.duration:.1f}s")
            QTimer.singleShot(33, _tick)

        QTimer.singleShot(33, _tick)

    def _rename_item(self, item, layout):
        """Mostra campo inline para renomear."""
        rename_frame = QFrame()
        rename_frame.setStyleSheet(f"background: {C['card']}; border-radius: 4px;")
        rl = QHBoxLayout(rename_frame)
        rl.setContentsMargins(4, 4, 4, 4)
        entry = QLineEdit(item.name)
        entry.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {TRACK_COLORS.get(item.track, C['cyan'])}; border-radius: 3px; padding: 2px;")
        rl.addWidget(entry)
        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(30, 24)
        ok_btn.setStyleSheet(f"background: {TRACK_COLORS.get(item.track, C['accent'])}; color: {C['dark_text']}; font-weight: bold; border-radius: 3px;")

        def _confirm():
            new_name = entry.text().strip()
            if new_name:
                group = self._get_group(item)
                rep = sorted(group, key=lambda i: i.start_time)[0] if group else item
                rep.name = new_name
                self._project.save(PROJECTS_DIR)
            rename_frame.deleteLater()
            self.show_item(self._item, self._project)

        ok_btn.clicked.connect(_confirm)
        entry.returnPressed.connect(_confirm)
        rl.addWidget(ok_btn)
        # Inserir antes do stretch
        count = layout.count()
        layout.insertWidget(count - 1, rename_frame)
        entry.setFocus()
        entry.selectAll()


# ============================================================
# WAVEFORM WIDGET
# ============================================================

class _WaveformWidget(QWidget):
    """Widget que desenha waveform do audio com playhead e seek."""

    seek_requested = Signal(float)  # ratio 0-1

    def __init__(self, item, color, parent=None):
        super().__init__(parent)
        self._item = item
        self._color = QColor(color)
        self._waveform_data = None
        self._playhead_ratio = -1  # -1 = hidden
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._load_waveform()

    def _load_waveform(self):
        """Carrega dados da waveform do arquivo de audio."""
        if not self._item.file_path or not Path(self._item.file_path).exists():
            return
        try:
            import numpy as np
            import soundfile as sf
            data, sr = sf.read(self._item.file_path, dtype="float32")
            if len(data.shape) > 1:
                data = data.mean(axis=1)
            # Reduzir para ~200 pontos
            n_points = 200
            chunk = max(1, len(data) // n_points)
            self._waveform_data = []
            for i in range(0, len(data), chunk):
                segment = data[i:i+chunk]
                self._waveform_data.append(float(np.abs(segment).max()))
        except Exception:
            self._waveform_data = None

    def set_playhead(self, ratio):
        self._playhead_ratio = ratio
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        # Fundo
        p.fillRect(0, 0, w, h, QColor(C["dark"]))

        # Waveform
        if self._waveform_data:
            n = len(self._waveform_data)
            bar_w = max(1, w / n)
            mid = h / 2
            color_dark = QColor(self._color)
            color_dark.setAlpha(180)
            for i, amp in enumerate(self._waveform_data):
                x = int(i * bar_w)
                bar_h = max(1, int(amp * mid * 0.9))
                p.setPen(Qt.NoPen)
                p.setBrush(color_dark)
                p.drawRect(x, int(mid - bar_h), max(1, int(bar_w) - 1), bar_h * 2)
        else:
            p.setPen(QPen(self._color, 1))
            p.drawLine(0, h // 2, w, h // 2)

        # Playhead
        if 0 <= self._playhead_ratio <= 1:
            px = int(self._playhead_ratio * w)
            p.setPen(QPen(QColor(C["playhead"]), 2))
            p.drawLine(px, 0, px, h)
            # Triangulo no topo
            from PySide6.QtGui import QPolygon
            from PySide6.QtCore import QPoint
            p.setBrush(QColor(C["playhead"]))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygon([QPoint(px - 4, 0), QPoint(px + 4, 0), QPoint(px, 5)]))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ratio = max(0.0, min(1.0, event.position().x() / self.width()))
            self.seek_requested.emit(ratio)
