"""Track Editor Panel Qt - Editor de layers de audio por track (voice/sfx/music/audio)."""

import time as _time
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QFrame, QLineEdit, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QMimeData
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QPainterPath, QDrag

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
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item = None
        self._project = None
        self._playing = {}  # item_id -> bool
        self._paused_state = {}  # item_id -> {"ratio": float, "time": float}
        self._pending_range_cut = {}  # item_id -> rel time A
        self._layer_refs = {}
        self._layer_frames = {}
        self._layer_headers = {}
        self._action_grid = None
        self.setMinimumWidth(0)
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
        self._paused_state = {}
        self._pending_range_cut = {}
        self._layer_refs = {}  # item_id -> {waveform, time_lbl, play_btn, color}
        self._layer_frames = {}
        self._layer_headers = {}
        self._action_grid = None
        self._slider_slot_index = 0
        color = TRACK_COLORS.get(item.track, C["cyan"])
        title = TRACK_TITLES.get(item.track, "AUDIO")

        # Limpar tudo
        while self._outer.count():
            child = self._outer.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 8, 10, 6)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-size: 14pt; font-weight: bold; background: transparent; border: none;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self._close)
        hdr_l.addWidget(close_btn)
        self._outer.addLayout(hdr_l)

        # Info
        info = QLabel(f"  {item.name} · {item.duration:.1f}s · Inicio {item.start_time:.1f}s")
        info.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        self._outer.addWidget(info)

        summary = QFrame()
        summary.setStyleSheet(
            "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        summary_l = QHBoxLayout(summary)
        summary_l.setContentsMargins(10, 8, 10, 8)
        summary_l.setSpacing(8)
        summary_l.addWidget(self._chip("TRACK", title, color))
        summary_l.addWidget(self._chip("DURAÇÃO", f"{item.duration:.1f}s", C['cyan']))
        summary_l.addWidget(self._chip("INÍCIO", f"{item.start_time:.1f}s", C['secondary']))
        summary_l.addStretch()
        self._outer.addWidget(summary)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        L = QVBoxLayout(content)
        L.setContentsMargins(10, 6, 10, 10)
        L.setSpacing(8)
        scroll.setWidget(content)
        self._outer.addWidget(scroll)

        # Layers
        group = self._get_group(item)
        layers_lbl = QLabel(f"EDITOR DE SOM · {len(group)} layer(s)")
        layers_lbl.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold; letter-spacing: 1px; border: none;")
        L.addWidget(layers_lbl)

        for layer_item in sorted(group, key=lambda i: i.start_time):
            L.addWidget(self._build_layer(layer_item, color))

        # Botões globais
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.08);")
        L.addWidget(sep)

        # Loop checkbox fora do grid
        from PySide6.QtWidgets import QCheckBox
        self._loop_cb = QCheckBox("  Loop")
        self._loop_cb.setStyleSheet(
            f"QCheckBox {{ color: {C['text2']}; font-size: 9pt; font-weight: bold; spacing: 6px; padding: 6px 0; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px; border: 2px solid {color}; background: rgba(255,255,255,0.04); }}"
            f"QCheckBox::indicator:checked {{ background: {color}; border: 2px solid {color}; }}"
            f"QCheckBox::indicator:hover {{ border: 2px solid {C['secondary']}; }}")
        L.addWidget(self._loop_cb)

        action_grid = _ResponsiveActionGrid()
        self._action_grid = action_grid
        L.addWidget(action_grid)

        # Play All
        play_all_btn = QPushButton("\u25b6 PLAY CONJUNTO")
        play_all_btn.setFixedHeight(28)
        play_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        play_all_btn.setStyleSheet(
            f"background: rgba(255,255,255,0.05); color: {color}; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid {color}; border-radius: 10px; padding: 2px 10px;")
        play_all_btn.clicked.connect(lambda: self._play_all(group, color))
        action_grid.add_widget(play_all_btn)

        rename_btn = QPushButton("✏ RENOMEAR")
        rename_btn.setFixedHeight(28)
        rename_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rename_btn.setStyleSheet(
            f"background: rgba(255,255,255,0.07); color: {color}; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid {color}; border-radius: 10px; padding: 2px 10px;")
        rename_btn.clicked.connect(lambda: self._rename_block(item, color))
        action_grid.add_widget(rename_btn)

        save_btn = QPushButton("SALVAR")
        save_btn.setFixedHeight(28)
        save_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        save_btn.setStyleSheet(
            f"background: {color}; color: {C['dark_text']}; font-weight: bold; font-size: 10pt; border-radius: 10px; padding: 2px 10px;")
        save_btn.clicked.connect(lambda: project.save(PROJECTS_DIR))
        action_grid.add_widget(save_btn)

        L.addStretch()
        self._refresh_action_grid()
        self.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_action_grid()

    def _refresh_action_grid(self):
        if self._action_grid is not None:
            self._action_grid._relayout()
            self._action_grid.updateGeometry()

    def _chip(self, label, value, color):
        chip = QFrame()
        chip.setStyleSheet(
            "background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 999px;"
        )
        chip_l = QHBoxLayout(chip)
        chip_l.setContentsMargins(10, 4, 10, 4)
        chip_l.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;")
        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: 8pt; font-family: Consolas; font-weight: bold; border: none;")
        chip_l.addWidget(lbl)
        chip_l.addWidget(val)
        return chip

    def _pill(self, label, value, color):
        pill = QFrame()
        pill.setStyleSheet(
            "background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 999px;"
        )
        pill_l = QHBoxLayout(pill)
        pill_l.setContentsMargins(8, 3, 8, 3)
        pill_l.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;")
        val = QLabel(str(value))
        val.setStyleSheet(f"color: {color}; font-size: 8pt; font-family: Consolas; font-weight: bold; border: none;")
        pill_l.addWidget(lbl)
        pill_l.addWidget(val)
        return pill

    def _build_layer(self, item, color):
        """Constroi um layer com visual de editor de som."""
        frame = QFrame()
        frame.setStyleSheet(
            "background: rgba(10,16,30,0.94); "
            "border: 1px solid rgba(255,255,255,0.10); border-radius: 16px;"
        )
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        frame.setMinimumWidth(0)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)
        self._layer_frames[item.id] = frame

        # Header (colapsavel)
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(8, 6, 8, 6)
        hdr_layout.setSpacing(8)
        collapse_btn = QPushButton("\u25bc")
        collapse_btn.setFixedSize(24, 24)
        collapse_btn.setStyleSheet(
            f"background: rgba(255,255,255,0.06); color: {color}; font-weight: bold; border: none; border-radius: 8px; padding: 0;"
        )
        hdr_layout.addWidget(collapse_btn)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(0)

        name_lbl = _LayerDragLabel(item.id, item.name[:24])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-weight: bold; font-size: 10pt; border: none;")
        name_lbl.setCursor(Qt.PointingHandCursor)
        name_lbl.mouseDoubleClickEvent = lambda e, i=item, l=name_lbl, f=hdr_frame, c=color: self._inline_rename_layer(i, l, f, c)
        title_box.addWidget(name_lbl)
        meta_lbl = QLabel(f"{item.duration:.1f}s · início {item.start_time:.1f}s")
        meta_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;")
        title_box.addWidget(meta_lbl)
        hdr_layout.addLayout(title_box)
        hdr_layout.addStretch()

        mode_chip = QLabel("EDITOR")
        mode_chip.setAlignment(Qt.AlignCenter)
        mode_chip.setFixedHeight(22)
        mode_chip.setStyleSheet(
            f"background: rgba(255,255,255,0.05); color: {color}; font-size: 7pt; font-weight: bold; padding: 0 8px; border-radius: 11px;"
        )
        hdr_layout.addWidget(mode_chip)

        del_btn = QPushButton("X")
        del_btn.setObjectName("closeBtn")
        del_btn.setFixedSize(22, 22)
        del_btn.clicked.connect(lambda checked=False, i=item: self._delete_layer(i))
        hdr_layout.addWidget(del_btn)
        fl.addWidget(hdr_frame)
        self._layer_headers[item.id] = hdr_frame

        waveform_card = QFrame()
        waveform_card.setStyleSheet(
            "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px;"
        )
        waveform_l = QVBoxLayout(waveform_card)
        waveform_l.setContentsMargins(8, 8, 8, 8)
        waveform_l.setSpacing(5)
        wf_head = QHBoxLayout()
        wf_lbl = QLabel("FORMA DE ONDA")
        wf_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; letter-spacing: 1px; border: none;")
        wf_head.addWidget(wf_lbl)
        wf_head.addStretch()
        wf_hint = QLabel("clique / arraste para keyframes")
        wf_hint.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;")
        wf_head.addWidget(wf_hint)
        waveform_l.addLayout(wf_head)

        # Content (colapsavel)
        content_widget = QWidget()
        cl = QVBoxLayout(content_widget)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)

        # Waveform
        waveform = _WaveformWidget(item, color)
        waveform.setFixedHeight(78)
        waveform.keyframe_changed.connect(lambda commit, i=item: self._on_layer_change(i, commit))
        waveform.setToolTip("Clique para criar keyframe | Arraste para ajustar | Botao direito remove")
        waveform_l.addWidget(waveform)
        cl.addWidget(waveform_card)

        # Quick info row
        quick = QFrame()
        quick.setStyleSheet(
            "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        quick_l = QHBoxLayout(quick)
        quick_l.setContentsMargins(8, 6, 8, 6)
        quick_l.setSpacing(8)
        time_lbl = QLabel(f"00:00.0 / {item.duration:.1f}s")
        time_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        quick_l.addWidget(time_lbl)
        quick_l.addStretch()
        quick_l.addWidget(self._pill("VOL", item.params.get("volume", 80), color))
        quick_l.addWidget(self._pill("PAN", item.params.get("pan", 0), C['cyan']))
        quick_l.addWidget(self._pill("SPD", item.params.get("speed", 100), C['accent']))
        cl.addWidget(quick)

        preset_card = QFrame()
        preset_card.setStyleSheet(
            "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        preset_l = QVBoxLayout(preset_card)
        preset_l.setContentsMargins(8, 8, 8, 8)
        preset_l.setSpacing(6)
        preset_head = QHBoxLayout()
        preset_lbl = QLabel("PRESETS RÁPIDOS")
        preset_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; letter-spacing: 1px; border: none;")
        preset_head.addWidget(preset_lbl)
        preset_head.addStretch()
        preset_note = QLabel("um clique para ajustar")
        preset_note.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;")
        preset_head.addWidget(preset_note)
        preset_l.addLayout(preset_head)

        recommended_key = self._recommended_preset_for_track(item.track)
        recommended_lbl = QLabel(f"Recomendado: {self._preset_label_for_key(recommended_key)}")
        recommended_lbl.setStyleSheet(
            f"color: {color}; font-size: 7pt; font-weight: bold; border: none;"
        )
        preset_l.addWidget(recommended_lbl)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_row.setContentsMargins(0, 0, 0, 0)
        for preset_key, preset_label, preset_desc in self._presets_for_track(item.track):
            btn = QPushButton(preset_label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(preset_desc)
            btn.setMinimumHeight(28)
            if preset_key == recommended_key:
                btn.setStyleSheet(
                    f"background: rgba(255,255,255,0.08); color: {color}; font-size: 8pt; font-weight: bold; "
                    f"border: 1px solid {color}; border-radius: 10px; padding: 3px 8px;"
                )
            else:
                btn.setStyleSheet(
                    f"background: rgba(255,255,255,0.05); color: {C['text2']}; font-size: 8pt; font-weight: bold; "
                    f"border: 1px solid rgba(255,255,255,0.10); border-radius: 10px; padding: 3px 8px;"
                )
            btn.clicked.connect(lambda checked=False, pk=preset_key, i=item, c=color: self._apply_mix_preset(i, pk, c))
            preset_row.addWidget(btn)
        preset_l.addLayout(preset_row)
        cl.addWidget(preset_card)

        # Play + Duplicate row
        play_row = QHBoxLayout()
        play_row.setSpacing(8)
        play_row.setContentsMargins(0, 0, 0, 0)
        play_btn = QPushButton("\u25b6 Play")
        play_btn.setMinimumSize(92, 30)
        play_btn.setStyleSheet(
            f"background: {color}; color: {C['dark_text']}; font-weight: bold; border-radius: 10px; padding: 4px 12px;"
        )
        play_btn.clicked.connect(lambda checked=False, i=item, b=play_btn, c=color: self._toggle_play(i, b, c))
        play_row.addWidget(play_btn)
        dup_btn = QPushButton("Duplicar")
        dup_btn.setMinimumSize(80, 30)
        dup_btn.setStyleSheet(
            "background: rgba(255,255,255,0.05); color: #A9B4C8; font-size: 8pt; font-weight: bold; "
            "border-radius: 10px; padding: 4px 12px;"
        )
        dup_btn.clicked.connect(lambda checked=False, i=item: self._duplicate(i))
        play_row.addWidget(dup_btn)

        split_btn = QPushButton("Quebrar")
        split_btn.setMinimumSize(78, 30)
        split_btn.setStyleSheet(
            "background: rgba(255,255,255,0.05); color: #A9B4C8; font-size: 8pt; font-weight: bold; "
            "border-radius: 10px; padding: 4px 12px;"
        )
        split_btn.clicked.connect(lambda checked=False, i=item: self._split_layer(i))
        play_row.addWidget(split_btn)

        cut_start_btn = QPushButton("Cortar início")
        cut_start_btn.setMinimumSize(92, 30)
        cut_start_btn.setStyleSheet(
            "background: rgba(255,255,255,0.05); color: #A9B4C8; font-size: 8pt; font-weight: bold; "
            "border-radius: 10px; padding: 4px 12px;"
        )
        cut_start_btn.clicked.connect(lambda checked=False, i=item: self._trim_start_to_playhead(i))
        play_row.addWidget(cut_start_btn)

        cut_end_btn = QPushButton("Cortar fim")
        cut_end_btn.setMinimumSize(88, 30)
        cut_end_btn.setStyleSheet(
            "background: rgba(255,255,255,0.05); color: #A9B4C8; font-size: 8pt; font-weight: bold; "
            "border-radius: 10px; padding: 4px 12px;"
        )
        cut_end_btn.clicked.connect(lambda checked=False, i=item: self._trim_end_to_playhead(i))
        play_row.addWidget(cut_end_btn)

        range_btn = QPushButton("Recorte A-B")
        range_btn.setMinimumSize(96, 30)
        range_btn.setStyleSheet(
            "background: rgba(255,255,255,0.05); color: #A9B4C8; font-size: 8pt; font-weight: bold; "
            "border-radius: 10px; padding: 4px 12px;"
        )
        range_info = QLabel("")
        range_info.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;")
        range_info.setMinimumWidth(70)
        range_btn.clicked.connect(lambda checked=False, i=item, b=range_btn, info=range_info: self._range_cut_action(i, b, info))
        play_row.addWidget(range_btn)
        play_row.addWidget(range_info)

        play_row.addStretch()
        start_lbl = QLabel(f"Inicio: {item.start_time:.1f}s")
        start_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        play_row.addWidget(start_lbl)
        cl.addLayout(play_row)

        # Sliders: VOL, PAN, FADE IN, FADE OUT, REVERB, ROOM, SPEED
        params_frame = QFrame()
        params_frame.setStyleSheet(
            "background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px;"
        )
        pl = QVBoxLayout(params_frame)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.setSpacing(8)
        params_lbl = QLabel("CONTROLES DE MIXAGEM")
        params_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; letter-spacing: 1px; border: none;")
        pl.addWidget(params_lbl)
        sliders_grid = QGridLayout()
        sliders_grid.setHorizontalSpacing(8)
        sliders_grid.setVerticalSpacing(8)
        pl.addLayout(sliders_grid)
        vol = int(item.params.get("volume", 80))
        self._add_param_slider(sliders_grid, "VOL", 0, 200, vol, "%", color, item, "volume")
        pan = int(item.params.get("pan", 0))
        self._add_param_slider(sliders_grid, "PAN", -100, 100, pan, "", color, item, "pan")
        fi = int(item.params.get("fade_in", 0))
        self._add_param_slider(sliders_grid, "FADE IN", 0, 100, fi, "%", C["secondary"], item, "fade_in")
        fo = int(item.params.get("fade_out", 0))
        self._add_param_slider(sliders_grid, "FADE OUT", 0, 100, fo, "%", C["secondary"], item, "fade_out")
        reverb = int(item.params.get("reverb", 0))
        self._add_param_slider(sliders_grid, "REVERB", 0, 100, reverb, "%", C["primary"], item, "reverb")
        room = int(item.params.get("room", 0))
        self._add_param_slider(sliders_grid, "ROOM", 0, 100, room, "%", C["primary"], item, "room")
        speed = int(item.params.get("speed", 100))
        self._add_param_slider(sliders_grid, "SPEED", 50, 200, speed, "%", C["accent"], item, "speed")
        sliders_grid.setColumnStretch(0, 1)
        sliders_grid.setColumnStretch(1, 1)
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
            "play_btn": play_btn, "color": color,
            "current_time": 0.0,
        }

        return frame

    def _on_layer_change(self, item, commit=False):
        """Atualiza a timeline quando um layer muda e salva quando a edicao foi concluida."""
        if commit and self._project is not None:
            self._project.save(PROJECTS_DIR)
        self.changed.emit()

    def _add_param_slider(self, layout, label, from_, to, default, unit, color, item, param_key):
        """Slider compacto em card, distribuido em grade de duas colunas."""
        box = QFrame()
        box.setStyleSheet(
            "background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        box_l = QVBoxLayout(box)
        box_l.setContentsMargins(8, 6, 8, 6)
        box_l.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; font-weight: bold; border: none;")
        top.addWidget(lbl)
        top.addStretch()

        slider = QSlider(Qt.Horizontal)
        slider.setRange(from_, to)
        slider.setValue(default)
        slider.setFixedHeight(16)
        slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: rgba(255,255,255,0.08); height: 4px; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; border: 2px solid rgba(255,255,255,0.18); }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 2px; }}")

        val_lbl = QLabel(f"{default}{unit}")
        val_lbl.setFixedWidth(48)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val_lbl.setStyleSheet(f"color: {C['text']}; font-family: Consolas; font-size: 8pt; font-weight: bold; border: none;")
        top.addWidget(val_lbl)

        box_l.addLayout(top)
        box_l.addWidget(slider)

        def on_change(v):
            val_lbl.setText(f"{v}{unit}")
            item.params[param_key] = str(v)

        slider.valueChanged.connect(on_change)
        if isinstance(layout, QGridLayout):
            slot = getattr(self, "_slider_slot_index", 0)
            row = slot // 2
            col = slot % 2
            layout.addWidget(box, row, col)
            self._slider_slot_index = slot + 1
        else:
            layout.addWidget(box)

    def _apply_mix_preset(self, item, preset_key, color):
        """Aplica presets rápidos e recarrega o painel para refletir os novos valores."""
        presets = self._preset_values_for_track(item.track)
        values = presets.get(preset_key, presets["reset"])
        for key, value in values.items():
            item.params[key] = str(value)

        if self._project is not None:
            self._project.save(PROJECTS_DIR)
        self.changed.emit()
        if self._item is not None and self._project is not None:
            self.show_item(self._item, self._project)

    def _presets_for_track(self, track):
        """Retorna os presets visiveis para cada track."""
        banks = {
            "voice": [
                ("voice_clean", "CLEAN", "voz seca e clara"),
                ("voice_broadcast", "BROADCAST", "voz mais presente"),
                ("voice_warm", "WARM", "mais corpo e sala leve"),
                ("reset", "RESET", "padrão"),
            ],
            "sfx": [
                ("sfx_impact", "IMPACT", "mais punch"),
                ("sfx_dry", "DRY", "sem sala"),
                ("sfx_space", "SPACE", "mais ambiente"),
                ("reset", "RESET", "padrão"),
            ],
            "music": [
                ("music_cinema", "CINEMA", "largura e profundidade"),
                ("music_wide", "WIDE", "abertura estéreo"),
                ("music_tight", "TIGHT", "mais focado"),
                ("reset", "RESET", "padrão"),
            ],
            "audio": [
                ("audio_balanced", "BALANCED", "equilíbrio geral"),
                ("audio_air", "AIR", "brilho e leveza"),
                ("audio_focus", "FOCUS", "mais centro"),
                ("reset", "RESET", "padrão"),
            ],
        }
        return banks.get(track, banks["audio"])

    def _recommended_preset_for_track(self, track):
        """Retorna o preset principal recomendado para a faixa atual."""
        return {
            "voice": "voice_clean",
            "sfx": "sfx_impact",
            "music": "music_cinema",
            "audio": "audio_balanced",
        }.get(track, "audio_balanced")

    def _preset_label_for_key(self, preset_key):
        """Retorna o rótulo amigável de um preset pelo identificador interno."""
        labels = {
            "voice_clean": "CLEAN",
            "voice_broadcast": "BROADCAST",
            "voice_warm": "WARM",
            "sfx_impact": "IMPACT",
            "sfx_dry": "DRY",
            "sfx_space": "SPACE",
            "music_cinema": "CINEMA",
            "music_wide": "WIDE",
            "music_tight": "TIGHT",
            "audio_balanced": "BALANCED",
            "audio_air": "AIR",
            "audio_focus": "FOCUS",
            "reset": "RESET",
        }
        return labels.get(preset_key, "RESET")

    def _preset_values_for_track(self, track):
        """Mapa de valores por preset e track."""
        common = {
            "reset": {
                "volume": 80, "pan": 0, "fade_in": 0, "fade_out": 0,
                "reverb": 0, "room": 0, "speed": 100,
            }
        }
        banks = {
            "voice": {
                **common,
                "voice_clean": {
                    "volume": 94, "pan": 0, "fade_in": 0, "fade_out": 2,
                    "reverb": 0, "room": 0, "speed": 100,
                },
                "voice_broadcast": {
                    "volume": 92, "pan": 0, "fade_in": 0, "fade_out": 6,
                    "reverb": 3, "room": 5, "speed": 100,
                },
                "voice_warm": {
                    "volume": 88, "pan": 0, "fade_in": 2, "fade_out": 4,
                    "reverb": 10, "room": 16, "speed": 100,
                },
            },
            "sfx": {
                **common,
                "sfx_impact": {
                    "volume": 110, "pan": 0, "fade_in": 0, "fade_out": 2,
                    "reverb": 6, "room": 8, "speed": 100,
                },
                "sfx_dry": {
                    "volume": 100, "pan": 0, "fade_in": 0, "fade_out": 0,
                    "reverb": 0, "room": 0, "speed": 100,
                },
                "sfx_space": {
                    "volume": 92, "pan": 8, "fade_in": 0, "fade_out": 4,
                    "reverb": 18, "room": 30, "speed": 100,
                },
            },
            "music": {
                **common,
                "music_cinema": {
                    "volume": 78, "pan": 0, "fade_in": 6, "fade_out": 8,
                    "reverb": 16, "room": 24, "speed": 100,
                },
                "music_wide": {
                    "volume": 75, "pan": 10, "fade_in": 4, "fade_out": 6,
                    "reverb": 12, "room": 18, "speed": 100,
                },
                "music_tight": {
                    "volume": 84, "pan": 0, "fade_in": 2, "fade_out": 4,
                    "reverb": 4, "room": 6, "speed": 100,
                },
            },
            "audio": {
                **common,
                "audio_balanced": {
                    "volume": 80, "pan": 0, "fade_in": 0, "fade_out": 0,
                    "reverb": 0, "room": 0, "speed": 100,
                },
                "audio_air": {
                    "volume": 82, "pan": 0, "fade_in": 2, "fade_out": 6,
                    "reverb": 8, "room": 12, "speed": 100,
                },
                "audio_focus": {
                    "volume": 84, "pan": 0, "fade_in": 0, "fade_out": 2,
                    "reverb": 2, "room": 4, "speed": 100,
                },
            },
        }
        return banks.get(track, banks["audio"])

    def _rename_block(self, item, color):
        """Substitui o botão RENOMEAR por um campo inline no próprio painel."""
        if getattr(self, '_rename_block_widget', None):
            self._rename_block_widget.deleteLater()
            self._rename_block_widget = None

        current = item.params.get("block_name", item.name)
        entry = QLineEdit(current)
        entry.setFixedHeight(28)
        entry.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid {color}; border-radius: 6px; padding: 0 8px;")

        ok_btn = QPushButton("\u2713")
        ok_btn.setFixedSize(28, 28)
        ok_btn.setStyleSheet(
            f"QPushButton {{ background: {color}; color: #000; font-weight: bold; font-size: 12pt; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(entry)
        row.addWidget(ok_btn)

        container = QWidget()
        container.setLayout(row)
        self._rename_block_widget = container

        # Insere logo abaixo do summary (índice 3)
        self._outer.insertWidget(3, container)
        entry.setFocus()
        entry.selectAll()

        def _confirm():
            new_name = entry.text().strip()
            if new_name:
                group = self._get_group(item)
                for gi in group:
                    gi.params["block_name"] = new_name
                if self._project:
                    self._project.save(PROJECTS_DIR)
                self.changed.emit()
            container.deleteLater()
            self._rename_block_widget = None

        ok_btn.clicked.connect(_confirm)
        entry.returnPressed.connect(_confirm)

    def _inline_rename_layer(self, item, name_lbl, hdr_frame, color):
        """Double-click no nome: substitui label por entry inline para renomear o layer."""
        name_lbl.hide()
        entry = QLineEdit(item.name)
        entry.setFixedHeight(24)
        entry.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; font-weight: bold; font-size: 9pt; "
            f"border: 1px solid {color}; border-radius: 4px; padding: 0 6px;")

        ok_btn = QPushButton("\u2713")
        ok_btn.setFixedSize(28, 24)
        ok_btn.setStyleSheet(
            f"QPushButton {{ background: {color}; color: #000000; font-weight: bold; font-size: 11pt; "
            f"border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(entry)
        row.addWidget(ok_btn)

        container = QWidget()
        container.setLayout(row)
        hdr_frame.layout().insertWidget(1, container)
        entry.setFocus()
        entry.selectAll()

        def _confirm():
            new_name = entry.text().strip()
            if new_name:
                item.name = new_name  # só renomeia o layer, não o block_name da timeline
                if self._project:
                    self._project.save(PROJECTS_DIR)
            container.deleteLater()
            name_lbl.setText(f"\u266b {item.name[:24]}")
            name_lbl.show()

        ok_btn.clicked.connect(_confirm)
        entry.returnPressed.connect(_confirm)

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
            refs = self._layer_refs.get(item_id)
            if refs:
                self._paused_state[item_id] = {
                    "ratio": max(0.0, min(1.0, refs["waveform"]._playhead_ratio if refs["waveform"]._playhead_ratio >= 0 else 0.0)),
                    "time": float(refs.get("current_time", 0.0)),
                }
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

            paused = self._paused_state.pop(item.id, None)
            start_ratio = max(0.0, min(1.0, float(paused.get("ratio", 0.0)) if paused else 0.0))
            start_sample = int(start_ratio * len(data))
            if start_sample >= len(data):
                start_sample = 0
                start_ratio = 0.0
            data = data[start_sample:]

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
            self._animate_playhead(item.id, start_ratio, item.duration * (1 - start_ratio))
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

    def _split_layer(self, item):
        """Quebra um layer em 2 partes no playhead da timeline (ou no meio)."""
        if item.duration <= 0.08:
            return

        cut_time = item.duration / 2.0
        app = self.window()
        if hasattr(app, "timeline"):
            abs_t = float(getattr(app.timeline, "playhead_pos", item.start_time + cut_time))
            rel_t = abs_t - item.start_time
            if 0.05 < rel_t < item.duration - 0.05:
                cut_time = rel_t

        dur_a = round(max(0.05, cut_time), 3)
        dur_b = round(max(0.05, item.duration - cut_time), 3)
        if dur_a + dur_b > item.duration:
            dur_b = round(max(0.05, item.duration - dur_a), 3)

        base_name = item.name
        params_b = dict(item.params)

        kf_a, kf_b = self._split_volume_keyframes(item.volume_keyframes, item.duration, cut_time)
        item.duration = dur_a
        item.name = f"{base_name} A"
        item.volume_keyframes = kf_a

        new_item = self._project.add_track_item(
            name=f"{base_name} B",
            track=item.track,
            start_time=round(item.start_time + dur_a, 3),
            duration=dur_b,
            file_path=item.file_path,
            params=params_b,
            clip_index=item.clip_index,
        )
        new_item.volume_keyframes = kf_b

        self._project.save(PROJECTS_DIR)
        self.changed.emit()
        self.show_item(item, self._project)

    def _get_playhead_rel_time(self, item):
        """Retorna tempo relativo do playhead no layer selecionado."""
        app = self.window()
        abs_time = item.start_time + (item.duration / 2.0)
        if hasattr(app, "timeline"):
            abs_time = float(getattr(app.timeline, "playhead_pos", abs_time))
        rel = abs_time - item.start_time
        return max(0.0, min(float(item.duration), rel))

    def _commit_layer_edit(self, item):
        self._project.save(PROJECTS_DIR)
        self.changed.emit()
        self.show_item(item, self._project)

    def _trim_start_to_playhead(self, item):
        """Remove o começo do layer até o playhead."""
        cut = self._get_playhead_rel_time(item)
        self._trim_start(item, cut)

    def _trim_end_to_playhead(self, item):
        """Remove o fim do layer a partir do playhead."""
        end_at = self._get_playhead_rel_time(item)
        self._trim_end(item, end_at)

    def _range_cut_action(self, item, btn, info_lbl):
        """Recorte entre dois pontos: primeiro clique marca A, segundo remove A-B."""
        cur = self._get_playhead_rel_time(item)
        mark_a = self._pending_range_cut.get(item.id)
        if mark_a is None:
            self._pending_range_cut[item.id] = cur
            btn.setText("A marcado")
            info_lbl.setText(f"A={cur:.2f}s")
            return

        self._pending_range_cut.pop(item.id, None)
        btn.setText("Recorte A-B")
        info_lbl.setText("")
        a, b = sorted((float(mark_a), float(cur)))
        if b - a < 0.05:
            return

        dur = float(item.duration)
        if a <= 0.01:
            self._trim_start(item, b)
            return
        if b >= dur - 0.01:
            self._trim_end(item, a)
            return

        left_dur = round(max(0.05, a), 3)
        right_dur = round(max(0.05, dur - b), 3)
        params_b = dict(item.params)

        left_kf = self._slice_volume_keyframes(item.volume_keyframes, dur, 0.0, a)
        right_kf = self._slice_volume_keyframes(item.volume_keyframes, dur, b, dur)

        item.duration = left_dur
        item.volume_keyframes = left_kf

        new_item = self._project.add_track_item(
            name=f"{item.name} (parte 2)",
            track=item.track,
            start_time=round(item.start_time + left_dur, 3),
            duration=right_dur,
            file_path=item.file_path,
            params=params_b,
            clip_index=item.clip_index,
        )
        new_item.volume_keyframes = right_kf
        self._commit_layer_edit(item)

    def _trim_start(self, item, cut):
        """Mantem somente trecho [cut, dur] e reposiciona no tempo."""
        dur = float(item.duration)
        cut = max(0.0, min(dur, float(cut)))
        if cut < 0.05 or cut >= dur - 0.01:
            return

        new_dur = round(max(0.05, dur - cut), 3)
        item.start_time = round(item.start_time + cut, 3)
        item.duration = new_dur
        item.volume_keyframes = self._slice_volume_keyframes(item.volume_keyframes, dur, cut, dur)
        self._commit_layer_edit(item)

    def _trim_end(self, item, end_at):
        """Mantem somente trecho [0, end_at]."""
        dur = float(item.duration)
        end_at = max(0.0, min(dur, float(end_at)))
        if end_at <= 0.05 or end_at >= dur - 0.01:
            return

        item.duration = round(max(0.05, end_at), 3)
        item.volume_keyframes = self._slice_volume_keyframes(item.volume_keyframes, dur, 0.0, end_at)
        self._commit_layer_edit(item)

    def _slice_volume_keyframes(self, keyframes, duration, seg_start, seg_end):
        """Recorta keyframes para [seg_start, seg_end] e remapeia tempo para 0..seg_len."""
        if not keyframes:
            return []

        dur = max(0.001, float(duration))
        a = max(0.0, min(dur, float(seg_start)))
        b = max(a, min(dur, float(seg_end)))
        if b - a <= 1e-6:
            return []

        pts = sorted(
            [{"time": float(k.get("time", 0.0)), "value": float(k.get("value", 1.0))} for k in keyframes],
            key=lambda k: k["time"],
        )

        def value_at(t):
            if t <= pts[0]["time"]:
                return pts[0]["value"]
            if t >= pts[-1]["time"]:
                return pts[-1]["value"]
            for i in range(1, len(pts)):
                p0 = pts[i - 1]
                p1 = pts[i]
                if p0["time"] <= t <= p1["time"]:
                    dt = p1["time"] - p0["time"]
                    if dt <= 1e-9:
                        return p1["value"]
                    r = (t - p0["time"]) / dt
                    return p0["value"] + (p1["value"] - p0["value"]) * r
            return pts[-1]["value"]

        sliced = [{"time": 0.0, "value": round(value_at(a), 3)}]
        for p in pts:
            t = p["time"]
            if a < t < b:
                sliced.append({"time": round(t - a, 2), "value": round(p["value"], 3)})
        sliced.append({"time": round(b - a, 2), "value": round(value_at(b), 3)})

        dedup = {}
        for p in sliced:
            dedup[round(float(p["time"]), 2)] = round(float(p["value"]), 3)
        out = [{"time": t, "value": dedup[t]} for t in sorted(dedup.keys())]
        return out

    def _split_volume_keyframes(self, keyframes, duration, cut_time):
        """Divide keyframes em duas listas mantendo continuidade no ponto de corte."""
        cut = max(0.0, min(float(duration), float(cut_time)))
        if not keyframes:
            return [], []

        pts = sorted(
            [{"time": float(k.get("time", 0.0)), "value": float(k.get("value", 1.0))} for k in keyframes],
            key=lambda k: k["time"],
        )

        def value_at(t):
            if t <= pts[0]["time"]:
                return pts[0]["value"]
            if t >= pts[-1]["time"]:
                return pts[-1]["value"]
            for i in range(1, len(pts)):
                a = pts[i - 1]
                b = pts[i]
                if a["time"] <= t <= b["time"]:
                    dt = b["time"] - a["time"]
                    if dt <= 1e-9:
                        return b["value"]
                    r = (t - a["time"]) / dt
                    return a["value"] + (b["value"] - a["value"]) * r
            return pts[-1]["value"]

        v_cut = value_at(cut)

        left = []
        for p in pts:
            if p["time"] < cut - 1e-6:
                left.append({"time": round(p["time"], 2), "value": round(p["value"], 3)})
        left.append({"time": round(cut, 2), "value": round(v_cut, 3)})

        right = [{"time": 0.0, "value": round(v_cut, 3)}]
        for p in pts:
            if p["time"] > cut + 1e-6:
                right.append({"time": round(p["time"] - cut, 2), "value": round(p["value"], 3)})

        left.sort(key=lambda k: k["time"])
        right.sort(key=lambda k: k["time"])
        return left, right

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
                refs["current_time"] = waveform._item.duration
                waveform.set_playhead(-1)
                refs["play_btn"].setText("\u25b6 Play")
                refs["play_btn"].setStyleSheet(f"background: {refs['color']}; color: {C['dark_text']}; font-weight: bold; border-radius: 4px;")
                time_lbl.setText(f"{waveform._item.duration:.1f}s / {waveform._item.duration:.1f}s")
                return
            ratio = start_ratio + (elapsed / waveform._item.duration)
            waveform.set_playhead(min(1.0, ratio))
            current = start_ratio * waveform._item.duration + elapsed
            refs["current_time"] = current
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
    """Widget que desenha waveform do audio com keyframes de volume."""

    keyframe_changed = Signal(bool)  # commit=True quando a edicao termina

    def __init__(self, item, color, parent=None):
        super().__init__(parent)
        self._item = item
        self._color = QColor(color)
        self._waveform_data = None
        self._playhead_ratio = -1  # -1 = hidden
        self._dragging = None
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._ensure_default_keyframes()
        self._load_waveform()

    def _ensure_default_keyframes(self):
        if self._item.volume_keyframes:
            self._item.volume_keyframes.sort(key=lambda k: k.get("time", 0.0))

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

    def _draw_keyframes(self, p, w, h):
        kfs = list(enumerate(self._item.volume_keyframes))
        if len(kfs) < 2:
            return

        dur = max(0.001, float(self._item.duration or 1.0))
        pad_x = 6
        top = 6
        bottom = h - 6
        band_h = max(8, bottom - top)
        draw_w = max(1, w - pad_x * 2)

        sorted_kfs = sorted(kfs, key=lambda pair: pair[1]["time"])
        path = QPainterPath()
        pts = []
        for idx, kf in sorted_kfs:
            ratio = max(0.0, min(1.0, float(kf.get("time", 0.0)) / dur))
            value = max(0.0, min(2.0, float(kf.get("value", 1.0)))) / 2.0
            x = pad_x + ratio * draw_w
            y = bottom - value * band_h
            pts.append((idx, x, y, value))

        if len(pts) < 2:
            return

        path.moveTo(pts[0][1], pts[0][2])
        for _, x, y, _ in pts[1:]:
            path.lineTo(x, y)

        fill = QPainterPath(path)
        fill.lineTo(pts[-1][1], bottom)
        fill.lineTo(pts[0][1], bottom)
        fill.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 42)))
        p.drawPath(fill)

        curve_color = QColor(self._color)
        curve_color.setAlpha(220)
        p.setPen(QPen(curve_color, 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        for idx, x, y, value in pts:
            active = self._dragging == idx
            r = 5 if active else 4
            p.setPen(QPen(QColor("#ffffff"), 1))
            p.setBrush(QBrush(QColor("#00ffee") if active else QColor(self._color)))
            p.drawEllipse(int(x) - r, int(y) - r, r * 2, r * 2)
            p.setPen(QPen(QColor(C["text"])))
            p.setFont(QFont("Consolas", 6))
            p.drawText(int(x) - 10, int(y) - 7, f"{value * 200:.0f}%")

    def _find_nearest_keyframe(self, pos, threshold=10):
        dur = max(0.001, float(self._item.duration or 1.0))
        w, h = self.width(), self.height()
        pad_x = 6
        top = 6
        bottom = h - 6
        band_h = max(8, bottom - top)
        draw_w = max(1, w - pad_x * 2)

        best = None
        best_dist = threshold
        for idx, kf in enumerate(self._item.volume_keyframes):
            ratio = max(0.0, min(1.0, float(kf.get("time", 0.0)) / dur))
            value = max(0.0, min(2.0, float(kf.get("value", 1.0)))) / 2.0
            x = pad_x + ratio * draw_w
            y = bottom - value * band_h
            dist = ((pos.x() - x) ** 2 + (pos.y() - y) ** 2) ** 0.5
            if dist < best_dist:
                best = idx
                best_dist = dist
        return best

    def _pos_to_kf(self, pos):
        w, h = self.width(), self.height()
        pad_x = 6
        top = 6
        bottom = h - 6
        band_h = max(8, bottom - top)
        draw_w = max(1, w - pad_x * 2)
        dur = max(0.001, float(self._item.duration or 1.0))
        t = max(0.0, min(dur, ((pos.x() - pad_x) / draw_w) * dur))
        v = max(0.0, min(2.0, (bottom - pos.y()) / band_h * 2.0))
        return t, v

    def _normalize_keyframes(self):
        self._item.volume_keyframes.sort(key=lambda k: k.get("time", 0.0))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        # Fundo
        p.fillRect(0, 0, w, h, QColor(11, 18, 32, 220))

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

        self._draw_keyframes(p, w, h)

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
            idx = self._find_nearest_keyframe(event.position())
            if idx is None:
                t, v = self._pos_to_kf(event.position())
                new_kf = {"time": round(t, 2), "value": round(v, 3)}
                self._item.volume_keyframes.append(new_kf)
                self._normalize_keyframes()
                self._dragging = self._item.volume_keyframes.index(new_kf)
                self.keyframe_changed.emit(False)
            else:
                self._dragging = idx
            self.setCursor(Qt.SizeAllCursor)
            self.update()
            event.accept()
        elif event.button() == Qt.RightButton:
            idx = self._find_nearest_keyframe(event.position(), threshold=14)
            if idx is not None:
                self._item.volume_keyframes.pop(idx)
                self._normalize_keyframes()
                self.keyframe_changed.emit(True)
                self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging is not None:
            t, v = self._pos_to_kf(event.position())
            kf = self._item.volume_keyframes[self._dragging]
            kf["time"] = round(t, 2)
            kf["value"] = round(v, 3)
            self._normalize_keyframes()
            self._dragging = self._item.volume_keyframes.index(kf)
            self.keyframe_changed.emit(False)
            self.update()

    def mouseReleaseEvent(self, event):
        if self._dragging is not None:
            self._dragging = None
            self.setCursor(Qt.PointingHandCursor)
            self.keyframe_changed.emit(True)
            self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._find_nearest_keyframe(event.position(), threshold=14)
            if idx is not None:
                self._dragging = idx
                self.setCursor(Qt.SizeAllCursor)
                self.update()
            event.accept()


class _LayerDragLabel(QLabel):
    """Label de layer que permite arrastar o item para outra posição/track na timeline."""

    def __init__(self, item_id, display_name, parent=None):
        super().__init__(f"\u266b {display_name}", parent)
        self._item_id = item_id
        self._drag_start = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 8:
            super().mouseMoveEvent(event)
            return

        mime = QMimeData()
        mime.setData("application/x-makevid-track-item", self._item_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)


class _ResponsiveLayerGrid(QWidget):
    """Grid responsivo que redistribui cards conforme a largura disponível."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = []
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(8)
        self._grid.setVerticalSpacing(8)

    def add_card(self, card):
        self._cards.append(card)
        card.setParent(self)
        card.show()
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self)

        if not self._cards:
            return

        available = max(1, self.width())
        card_min = max(280, max(card.minimumWidth() or 280 for card in self._cards))
        cols = max(1, available // (card_min + self._grid.horizontalSpacing()))
        cols = min(cols, len(self._cards))

        for index, card in enumerate(self._cards):
            row = index // cols
            col = index % cols
            self._grid.addWidget(card, row, col)

        for col in range(cols):
            self._grid.setColumnStretch(col, 1)


class _ResponsiveActionGrid(QWidget):
    """Grid responsivo para a barra de ações do editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._widgets = []
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(8)
        self._grid.setVerticalSpacing(8)
        self._grid.setAlignment(Qt.AlignTop)

    def add_widget(self, widget):
        self._widgets.append(widget)
        widget.setParent(self)
        widget.show()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self)

        if not self._widgets:
            return

        available = max(1, self.width())
        min_w = 110
        cols = max(1, available // (min_w + self._grid.horizontalSpacing()))
        cols = min(cols, len(self._widgets))

        for index, widget in enumerate(self._widgets):
            row = index // cols
            col = index % cols
            self._grid.addWidget(widget, row, col)

        for col in range(cols):
            self._grid.setColumnStretch(col, 1)

        self._grid.invalidate()
