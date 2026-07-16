"""Widget de UI completo para um layer de áudio no editor de tracks."""

import logging

import numpy as np

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QLineEdit, QGridLayout, QSizePolicy, QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR
from makevid.qt.panels.layer_ui_components import (
    _GlowButton, _SplitConfirmWidget, _LayerDragLabel, _ResponsiveActionGrid,
)
from makevid.qt.panels.waveform_widget import _WaveformWidget, _DbAxisWidget
from makevid.core.audio_utils import compute_normalize_gain
from makevid.qt.panels.layer_audio_player import _file_exists

_log = logging.getLogger(__name__)


class LayerWidget(QFrame):
    """UI completa de um layer de áudio — extraída de _build_layer."""

    # Sinais públicos — eliminam closures capturando item
    play_requested    = Signal(object)   # item
    seek_requested    = Signal(object, float)  # item, ratio
    cut_applied       = Signal(object, object, object)  # item, waveform, cut_btn
    changed           = Signal(object, bool)   # item, commit
    delete_requested  = Signal(object)   # item
    duplicate_requested = Signal(object) # item
    rename_requested  = Signal(object)   # item (inline rename do layer)

    def __init__(self, item, project, color, cut_service, layer_refs, parent=None):
        super().__init__(parent)
        self._item        = item
        self._project     = project
        self._color       = color
        self._cut_service = cut_service
        self._layer_refs  = layer_refs  # dict compartilhado com o painel

        self.setStyleSheet(
            "background: rgba(10,16,30,0.94); "
            "border: 1px solid rgba(255,255,255,0.10); border-radius: 16px;"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumWidth(0)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 10, 10, 10)
        self._root.setSpacing(8)

        self._content = QWidget()
        self._content_l = QVBoxLayout(self._content)
        self._content_l.setContentsMargins(0, 0, 0, 0)
        self._content_l.setSpacing(8)

        self._hdr_frame = self._build_header()
        self._root.addWidget(self._hdr_frame)
        self._root.addWidget(self._content)

        self._build_waveform_card()
        self._build_quick_row()
        self._build_preset_card()
        self._build_action_row()
        self._build_params_card()
        self._build_norm_card()

        self._register_refs()

    # ── header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = QFrame()
        hdr.setStyleSheet(
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(8, 6, 8, 6)
        hl.setSpacing(8)

        self._collapse_btn = QPushButton("▼")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setStyleSheet(
            f"background: rgba(255,255,255,0.06); color: {self._color}; "
            "font-weight: bold; border: none; border-radius: 8px; padding: 0;"
        )
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        hl.addWidget(self._collapse_btn)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(0)

        self._name_lbl = _LayerDragLabel(self._item.id, self._item.name[:24])
        self._name_lbl.setStyleSheet(
            f"color: {C['text']}; font-weight: bold; font-size: 10pt; border: none;"
        )
        self._name_lbl.setCursor(Qt.PointingHandCursor)
        self._name_lbl.mouseDoubleClickEvent = lambda e: self._inline_rename_layer()
        title_box.addWidget(self._name_lbl)

        meta = QLabel(f"{self._item.duration:.1f}s · início {self._item.start_time:.1f}s")
        meta.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;"
        )
        title_box.addWidget(meta)
        hl.addLayout(title_box)
        hl.addStretch()

        mode_chip = QLabel("EDITOR")
        mode_chip.setAlignment(Qt.AlignCenter)
        mode_chip.setFixedHeight(22)
        mode_chip.setStyleSheet(
            f"background: rgba(255,255,255,0.05); color: {self._color}; "
            "font-size: 7pt; font-weight: bold; padding: 0 8px; border-radius: 11px;"
        )
        hl.addWidget(mode_chip)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(24, 24)
        del_btn.setObjectName("closeBtn")
        del_btn.setToolTip("Remover layer")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self._item))
        hl.addWidget(del_btn)

        return hdr

    def _toggle_collapse(self):
        if self._content.isVisible():
            self._content.hide()
            self._collapse_btn.setText("▶")
        else:
            self._content.show()
            self._collapse_btn.setText("▼")

    # ── waveform card ─────────────────────────────────────────────────────────

    def _build_waveform_card(self):
        card = QFrame()
        card.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 14px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(5)

        head = QHBoxLayout()
        wf_lbl = QLabel("FORMA DE ONDA")
        wf_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; "
            "letter-spacing: 1px; border: none;"
        )
        head.addWidget(wf_lbl)
        head.addStretch()
        hint = QLabel("clique / arraste para keyframes")
        hint.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;"
        )
        head.addWidget(hint)
        cl.addLayout(head)

        wf_row = QHBoxLayout()
        wf_row.setSpacing(2)
        wf_row.setContentsMargins(0, 0, 0, 0)

        db_axis = _DbAxisWidget()
        db_axis.setFixedWidth(28)
        db_axis.setFixedHeight(78)
        wf_row.addWidget(db_axis)

        self.waveform = _WaveformWidget(self._item, self._color)
        self.waveform.setFixedHeight(78)
        self.waveform.keyframe_changed.connect(
            lambda commit: self.changed.emit(self._item, commit)
        )
        self.waveform.cut_requested.connect(
            lambda: self.cut_applied.emit(
                self._item, self.waveform,
                self._layer_refs.get(self._item.id, {}).get("cut_btn"),
            )
        )
        self.waveform.setToolTip(
            "Clique para criar keyframe | Arraste para ajustar | Botão direito remove"
        )
        wf_row.addWidget(self.waveform)
        cl.addLayout(wf_row)

        self._content_l.addWidget(card)

    # ── quick info row ────────────────────────────────────────────────────────

    def _build_quick_row(self):
        quick = QFrame()
        quick.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        ql = QHBoxLayout(quick)
        ql.setContentsMargins(8, 6, 8, 6)
        ql.setSpacing(6)

        self._time_lbl = QLabel(f"00:00.0 / {self._item.duration:.1f}s")
        self._time_lbl.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;"
        )
        self._time_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        ql.addWidget(self._time_lbl)

        self._loop_cb = QCheckBox("Loop")
        self._loop_cb.setStyleSheet(
            f"QCheckBox {{ color: {C['text3']}; font-size: 7pt; font-weight: bold; "
            f"spacing: 4px; border: none; }}"
            f"QCheckBox::indicator {{ width: 13px; height: 13px; border-radius: 4px; "
            f"border: 1px solid {self._color}; background: rgba(255,255,255,0.04); }}"
            f"QCheckBox::indicator:checked {{ background: {self._color}; "
            f"border: 1px solid {self._color}; }}"
        )
        ql.addWidget(self._loop_cb)

        for pill_lbl, pill_val, pill_color in [
            ("VOL", self._item.params.get("volume", 80), self._color),
            ("PAN", self._item.params.get("pan", 0), C["cyan"]),
        ]:
            ql.addWidget(self._pill(pill_lbl, pill_val, pill_color))

        # Controle de speed inline: ◀ [x.xx] ▶
        spd_lbl = QLabel("SPD")
        spd_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;"
        )
        ql.addWidget(spd_lbl)

        spd_dec = QLabel(" ◀ ")
        spd_dec.setFixedSize(16, 20)
        spd_dec.setAlignment(Qt.AlignCenter)
        spd_dec.setStyleSheet(f"color: {C['text3']}; font-size: 8pt; border: none;")
        spd_dec.setCursor(Qt.PointingHandCursor)
        ql.addWidget(spd_dec)

        self._spd_entry = QLineEdit(
            f"{int(self._item.params.get('speed', 100)) / 100:.2f}"
        )
        self._spd_entry.setFixedSize(40, 20)
        self._spd_entry.setAlignment(Qt.AlignCenter)
        self._spd_entry.setStyleSheet(
            f"background: transparent; color: {C['text']}; border: none; "
            "font-family: Consolas; font-size: 9pt; font-weight: bold; padding: 0;"
        )
        ql.addWidget(self._spd_entry)

        spd_inc = QLabel(" ▶ ")
        spd_inc.setFixedSize(16, 20)
        spd_inc.setAlignment(Qt.AlignCenter)
        spd_inc.setStyleSheet(f"color: {C['text3']}; font-size: 8pt; border: none;")
        spd_inc.setCursor(Qt.PointingHandCursor)
        ql.addWidget(spd_inc)

        def _get_spd():
            try:
                return max(0.25, min(4.0, float(self._spd_entry.text().replace(",", "."))))
            except ValueError:
                return 1.0

        def _set_spd(v):
            v = max(0.25, min(4.0, round(v, 2)))
            self._spd_entry.setText(f"{v:.2f}")
            self._item.params["speed"] = str(int(v * 100))
            self.play_requested.emit(self._item)

        spd_dec.mousePressEvent = lambda e: _set_spd(_get_spd() - 0.25)
        spd_inc.mousePressEvent = lambda e: _set_spd(_get_spd() + 0.25)
        self._spd_entry.returnPressed.connect(lambda: _set_spd(_get_spd()))
        self._spd_entry.editingFinished.connect(lambda: _set_spd(_get_spd()))

        self._content_l.addWidget(quick)

    def _pill(self, label, value, color):
        pill = QFrame()
        pill.setStyleSheet(
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 999px;"
        )
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(8, 3, 8, 3)
        pl.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;"
        )
        val = QLabel(str(value))
        val.setStyleSheet(
            f"color: {color}; font-size: 8pt; font-family: Consolas; "
            "font-weight: bold; border: none;"
        )
        pl.addWidget(lbl)
        pl.addWidget(val)
        return pill

    # ── preset card ───────────────────────────────────────────────────────────

    def _build_preset_card(self):
        card = QFrame()
        card.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(6)

        head = QHBoxLayout()
        lbl = QLabel("PRESETS RÁPIDOS")
        lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; "
            "letter-spacing: 1px; border: none;"
        )
        head.addWidget(lbl)
        head.addStretch()
        note = QLabel("um clique para ajustar")
        note.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;"
        )
        head.addWidget(note)
        cl.addLayout(head)

        recommended_key = self._recommended_preset_for_track(self._item.track)
        rec_lbl = QLabel(f"Recomendado: {self._preset_label_for_key(recommended_key)}")
        rec_lbl.setStyleSheet(
            f"color: {self._color}; font-size: 7pt; font-weight: bold; border: none;"
        )
        cl.addWidget(rec_lbl)

        grid = _ResponsiveActionGrid()
        for preset_key, preset_label, preset_desc in self._presets_for_track(self._item.track):
            btn = QPushButton(preset_label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(preset_desc)
            btn.setMinimumHeight(28)
            if preset_key == recommended_key:
                btn.setStyleSheet(
                    f"background: rgba(255,255,255,0.08); color: {self._color}; "
                    f"font-size: 8pt; font-weight: bold; border: 1px solid {self._color}; "
                    "border-radius: 10px; padding: 3px 8px;"
                )
            else:
                btn.setStyleSheet(
                    f"background: rgba(255,255,255,0.05); color: {C['text2']}; "
                    "font-size: 8pt; font-weight: bold; "
                    "border: 1px solid rgba(255,255,255,0.10); "
                    "border-radius: 10px; padding: 3px 8px;"
                )
            btn.clicked.connect(
                lambda checked=False, pk=preset_key: self._apply_mix_preset(pk)
            )
            grid.add_widget(btn)
        grid.finalize()
        cl.addWidget(grid)
        self._content_l.addWidget(card)

    def _apply_mix_preset(self, preset_key):
        presets = self._preset_values_for_track(self._item.track)
        for key, value in presets.get(preset_key, presets["reset"]).items():
            self._item.params[key] = str(value)
        if self._project is not None:
            self._project.save(PROJECTS_DIR)
        self.changed.emit(self._item, True)

    def _presets_for_track(self, track):
        banks = {
            "voice": [
                ("voice_clean",     "CLEAN",     "voz seca e clara"),
                ("voice_broadcast", "BROADCAST", "voz mais presente"),
                ("voice_warm",      "WARM",      "mais corpo e sala leve"),
                ("reset",           "RESET",     "padrão"),
            ],
            "sfx": [
                ("sfx_impact", "IMPACT", "mais punch"),
                ("sfx_dry",    "DRY",    "sem sala"),
                ("sfx_space",  "SPACE",  "mais ambiente"),
                ("reset",      "RESET",  "padrão"),
            ],
            "music": [
                ("music_cinema", "CINEMA", "largura e profundidade"),
                ("music_wide",   "WIDE",   "abertura estéreo"),
                ("music_tight",  "TIGHT",  "mais focado"),
                ("reset",        "RESET",  "padrão"),
            ],
            "audio": [
                ("audio_balanced", "BALANCED", "equilíbrio geral"),
                ("audio_air",      "AIR",      "brilho e leveza"),
                ("audio_focus",    "FOCUS",    "mais centro"),
                ("reset",          "RESET",    "padrão"),
            ],
        }
        return banks.get(track, banks["audio"])

    def _recommended_preset_for_track(self, track):
        return {
            "voice": "voice_clean",
            "sfx":   "sfx_impact",
            "music": "music_cinema",
            "audio": "audio_balanced",
        }.get(track, "audio_balanced")

    def _preset_label_for_key(self, preset_key):
        return {
            "voice_clean": "CLEAN", "voice_broadcast": "BROADCAST", "voice_warm": "WARM",
            "sfx_impact": "IMPACT", "sfx_dry": "DRY", "sfx_space": "SPACE",
            "music_cinema": "CINEMA", "music_wide": "WIDE", "music_tight": "TIGHT",
            "audio_balanced": "BALANCED", "audio_air": "AIR", "audio_focus": "FOCUS",
            "reset": "RESET",
        }.get(preset_key, "RESET")

    def _preset_values_for_track(self, track):
        common = {"reset": {"volume": 80, "pan": 0, "fade_in": 0, "fade_out": 0,
                             "reverb": 0, "room": 0, "speed": 100}}
        banks = {
            "voice": {**common,
                "voice_clean":     {"volume": 94, "pan": 0, "fade_in": 0,  "fade_out": 2,  "reverb": 0,  "room": 0,  "speed": 100},
                "voice_broadcast": {"volume": 92, "pan": 0, "fade_in": 0,  "fade_out": 6,  "reverb": 3,  "room": 5,  "speed": 100},
                "voice_warm":      {"volume": 88, "pan": 0, "fade_in": 2,  "fade_out": 4,  "reverb": 10, "room": 16, "speed": 100},
            },
            "sfx": {**common,
                "sfx_impact": {"volume": 110, "pan": 0, "fade_in": 0, "fade_out": 2, "reverb": 6,  "room": 8,  "speed": 100},
                "sfx_dry":    {"volume": 100, "pan": 0, "fade_in": 0, "fade_out": 0, "reverb": 0,  "room": 0,  "speed": 100},
                "sfx_space":  {"volume": 92,  "pan": 8, "fade_in": 0, "fade_out": 4, "reverb": 18, "room": 30, "speed": 100},
            },
            "music": {**common,
                "music_cinema": {"volume": 78, "pan": 0,  "fade_in": 6, "fade_out": 8, "reverb": 16, "room": 24, "speed": 100},
                "music_wide":   {"volume": 75, "pan": 10, "fade_in": 4, "fade_out": 6, "reverb": 12, "room": 18, "speed": 100},
                "music_tight":  {"volume": 84, "pan": 0,  "fade_in": 2, "fade_out": 4, "reverb": 4,  "room": 6,  "speed": 100},
            },
            "audio": {**common,
                "audio_balanced": {"volume": 80, "pan": 0, "fade_in": 0, "fade_out": 0, "reverb": 0, "room": 0,  "speed": 100},
                "audio_air":      {"volume": 82, "pan": 0, "fade_in": 2, "fade_out": 6, "reverb": 8, "room": 12, "speed": 100},
                "audio_focus":    {"volume": 84, "pan": 0, "fade_in": 0, "fade_out": 2, "reverb": 2, "room": 4,  "speed": 100},
            },
        }
        return banks.get(track, banks["audio"])

    # ── action row ────────────────────────────────────────────────────────────

    def _build_action_row(self):
        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setMinimumHeight(30)
        self._play_btn.setStyleSheet(
            f"background: {self._color}; color: {C['dark_text']}; "
            "font-weight: bold; border-radius: 10px; padding: 4px 12px;"
        )
        self._play_btn.clicked.connect(lambda: self.play_requested.emit(self._item))

        dup_btn = QPushButton("Duplicar")
        dup_btn.setMinimumHeight(30)
        dup_btn.setStyleSheet(
            "background: rgba(255,255,255,0.05); color: #A9B4C8; font-size: 8pt; "
            "font-weight: bold; border-radius: 10px; padding: 4px 12px;"
        )
        dup_btn.clicked.connect(lambda: self.duplicate_requested.emit(self._item))

        self._cut_btn = QPushButton("✂ Recortar")
        self._cut_btn.setMinimumHeight(30)
        self._cut_btn.setCheckable(True)
        self._cut_btn.setChecked(False)
        self._cut_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.05); color: #A9B4C8; "
            "font-size: 8pt; font-weight: bold; border-radius: 10px; "
            "padding: 4px 12px; border: none; }"
            "QPushButton:checked { background: rgba(255,255,255,0.05); color: #A9B4C8; "
            "font-size: 8pt; font-weight: bold; border-radius: 10px; "
            "padding: 4px 12px; border: none; }"
        )
        self._cut_btn.clicked.connect(
            lambda checked: self.cut_applied.emit(self._item, self.waveform, self._cut_btn)
        )

        self._cut_confirm = _SplitConfirmWidget(
            left_text="↩ Desfazer", right_text="✅ Aplicar",
            left_color="#ff6060", right_color=self._color,
        )
        self._cut_confirm.setMinimumHeight(30)
        self._cut_confirm.left_clicked.connect(self._on_undo_cut)
        self._cut_confirm.right_clicked.connect(
            lambda: self.cut_applied.emit(self._item, self.waveform, self._cut_btn)
        )
        self._cut_confirm.hide()

        row = _ResponsiveActionGrid()
        row.add_widget(self._play_btn)
        row.add_widget(dup_btn)
        row.add_widget(self._cut_btn)
        row.add_widget(self._cut_confirm)
        row.finalize()
        self._action_row = row
        self._content_l.addWidget(row)

    def _on_undo_cut(self):
        """Limpa seleções de corte sem aplicar."""
        self._cut_service.clear_selection()
        self.waveform.update()
        self.set_cut_container_mode("active")

    def set_cut_container_mode(self, mode):
        """
        mode='idle'    → Recortar (inativo)
        mode='active'  → Recortar (vermelho, modo ativo)
        mode='confirm' → [Desfazer | Aplicar]
        """
        if mode in ("idle", "active"):
            self._cut_btn.setChecked(mode == "active")
            self._cut_btn.setText("✂ Recortar")
            if mode == "idle":
                self._cut_btn.setStyleSheet(
                    "QPushButton { background: rgba(255,255,255,0.05); color: #A9B4C8; "
                    "font-size: 8pt; font-weight: bold; border-radius: 10px; "
                    "padding: 4px 12px; border: none; }"
                    "QPushButton:checked { background: rgba(255,255,255,0.05); color: #A9B4C8; "
                    "font-size: 8pt; font-weight: bold; border-radius: 10px; "
                    "padding: 4px 12px; border: none; }"
                )
            else:
                self._cut_btn.setStyleSheet(
                    f"QPushButton {{ background: {C['danger']}; color: #fff; "
                    "font-size: 8pt; font-weight: bold; border-radius: 10px; "
                    "padding: 4px 12px; border: none; }"
                    f"QPushButton:checked {{ background: {C['danger']}; color: #fff; "
                    "font-size: 8pt; font-weight: bold; border-radius: 10px; "
                    "padding: 4px 12px; border: none; }"
                )
            self._cut_btn.show()
            self._cut_confirm.hide()
            self._cut_confirm.stop_glow()
        else:  # confirm
            self._cut_btn.hide()
            self._cut_confirm.show()
            self._cut_confirm.start_glow()
        self._action_row._relayout()

    # ── params card (sliders de mixagem) ──────────────────────────────────────

    def _build_params_card(self):
        card = QFrame()
        card.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 14px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(8)

        lbl = QLabel("CONTROLES DE MIXAGEM")
        lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; "
            "letter-spacing: 1px; border: none;"
        )
        cl.addWidget(lbl)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        cl.addLayout(grid)

        slot = [0]
        item = self._item
        c = self._color
        self._add_param_slider(grid, "VOL",      0,    200, int(item.params.get("volume",   80)), "%", c,            item, "volume",   slot)
        self._add_param_slider(grid, "PAN",    -100,   100, int(item.params.get("pan",        0)), "",  c,            item, "pan",      slot)
        self._add_param_slider(grid, "FADE IN",  0,    100, int(item.params.get("fade_in",    0)), "%", C["secondary"], item, "fade_in",  slot)
        self._add_param_slider(grid, "FADE OUT", 0,    100, int(item.params.get("fade_out",   0)), "%", C["secondary"], item, "fade_out", slot)
        self._add_param_slider(grid, "REVERB",   0,    100, int(item.params.get("reverb",     0)), "%", C["primary"],   item, "reverb",   slot)
        self._add_param_slider(grid, "ROOM",     0,    100, int(item.params.get("room",       0)), "%", C["primary"],   item, "room",     slot)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._content_l.addWidget(card)

    def _add_param_slider(self, layout, label, from_, to, default, unit, color, item, param_key, slot):
        from PySide6.QtWidgets import QSlider
        box = QFrame()
        box.setStyleSheet(
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        bl = QVBoxLayout(box)
        bl.setContentsMargins(8, 6, 8, 6)
        bl.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; "
            "font-weight: bold; border: none;"
        )
        top.addWidget(lbl)
        top.addStretch()

        slider = QSlider(Qt.Horizontal)
        slider.setRange(from_, to)
        slider.setValue(default)
        slider.setFixedHeight(16)
        slider.setFocusPolicy(Qt.StrongFocus)
        slider.wheelEvent = lambda e: e.ignore()
        slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: rgba(255,255,255,0.08); "
            f"height: 4px; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 12px; height: 12px; "
            f"margin: -5px 0; border-radius: 6px; border: 2px solid rgba(255,255,255,0.18); }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 2px; }}"
        )

        val_lbl = QLabel(f"{default}{unit}")
        val_lbl.setFixedWidth(48)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val_lbl.setStyleSheet(
            f"color: {C['text']}; font-family: Consolas; font-size: 8pt; "
            "font-weight: bold; border: none;"
        )
        top.addWidget(val_lbl)
        bl.addLayout(top)
        bl.addWidget(slider)

        _REALTIME = {"volume", "pan"}

        def on_change(v):
            val_lbl.setText(f"{v}{unit}")
            item.params[param_key] = str(v)
            if param_key == "volume":
                self.waveform.update()
            if param_key not in _REALTIME:
                self.play_requested.emit(item)

        slider.valueChanged.connect(on_change)

        idx = slot[0]
        slot[0] += 1
        layout.addWidget(box, idx // 2, idx % 2)

    # ── normalização card ─────────────────────────────────────────────────────

    def _build_norm_card(self):
        card = QFrame()
        card.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 14px;"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(6)

        title = QLabel("NORMALIZAR")
        title.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; "
            "letter-spacing: 1px; border: none;"
        )
        cl.addWidget(title)

        method_lbl = QLabel("Método")
        method_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;"
        )
        cl.addWidget(method_lbl)

        radio_style = (
            f"QRadioButton {{ color: {C['text2']}; font-size: 8pt; font-weight: bold; "
            f"spacing: 6px; border: none; }}"
            f"QRadioButton::indicator {{ width: 13px; height: 13px; border-radius: 7px; "
            f"border: 1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.04); }}"
            f"QRadioButton::indicator:checked {{ background: {self._color}; "
            f"border: 1px solid {self._color}; }}"
        )
        rb_peak = QRadioButton("Pico")
        rb_lufs = QRadioButton("Loudness (LUFS)")
        rb_peak.setStyleSheet(radio_style)
        rb_lufs.setStyleSheet(radio_style)
        rb_peak.setChecked(True)

        method_group = QButtonGroup(card)
        method_group.addButton(rb_peak, 0)
        method_group.addButton(rb_lufs, 1)

        radio_row = QHBoxLayout()
        radio_row.setSpacing(12)
        radio_row.setContentsMargins(0, 0, 0, 0)
        radio_row.addWidget(rb_peak)
        radio_row.addWidget(rb_lufs)
        radio_row.addStretch()
        cl.addLayout(radio_row)

        target_lbl = QLabel("Alvo")
        target_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;"
        )
        cl.addWidget(target_lbl)

        _btn_style = (
            f"QPushButton {{ background: rgba(255,255,255,0.06); color: {C['text']}; "
            "font-size: 12pt; font-weight: bold; border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 6px; padding: 0; }}"
            "QPushButton:hover { background: rgba(255,255,255,0.14); }"
            "QPushButton:pressed { background: rgba(255,255,255,0.20); }"
        )
        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(26, 28)
        btn_minus.setStyleSheet(_btn_style)

        norm_entry = QLineEdit("-1.0")
        norm_entry.setFixedHeight(28)
        norm_entry.setFixedWidth(58)
        norm_entry.setAlignment(Qt.AlignCenter)
        norm_entry.setStyleSheet(
            f"QLineEdit {{ background: rgba(255,255,255,0.06); color: {C['text']}; "
            "font-size: 9pt; font-weight: bold; font-family: Consolas; "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; padding: 0 4px; }}"
        )

        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(26, 28)
        btn_plus.setStyleSheet(_btn_style)

        norm_unit = QLabel("dB")
        norm_unit.setStyleSheet(
            f"color: {C['text3']}; font-size: 8pt; font-weight: bold; "
            "border: none; min-width: 32px;"
        )

        def _get_value():
            try:
                return float(norm_entry.text().replace(",", "."))
            except ValueError:
                return -1.0

        def _set_value(v):
            norm_entry.setText(f"{max(-60.0, min(0.0, round(v, 1))):.1f}")

        def _on_method_changed(btn_id):
            if btn_id == 0:
                _set_value(-1.0)
                norm_unit.setText("dB")
            else:
                _set_value(-14.0)
                norm_unit.setText("LUFS")

        def _apply_norm():
            if not _file_exists(self._item.file_path):
                return
            mode = "peak" if rb_peak.isChecked() else "lufs"
            new_vol = compute_normalize_gain(
                self._item.file_path, mode, _get_value(),
                file_offset=float(getattr(self._item, "file_offset", 0.0)),
                duration=float(self._item.duration),
            )
            if new_vol < 0:
                return
            self._item.params["volume"] = str(new_vol)
            self.waveform.update()
            if self._project:
                self._project.save(PROJECTS_DIR)
            self.changed.emit(self._item, True)

        def _step_and_apply(delta):
            _set_value(_get_value() + delta)
            _apply_norm()

        btn_minus.clicked.connect(lambda: _step_and_apply(-0.5))
        btn_plus.clicked.connect(lambda: _step_and_apply(+0.5))
        norm_entry.returnPressed.connect(_apply_norm)
        norm_entry.editingFinished.connect(_apply_norm)
        method_group.idClicked.connect(_on_method_changed)

        target_row = QHBoxLayout()
        target_row.setSpacing(4)
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.addWidget(btn_minus)
        target_row.addWidget(norm_entry)
        target_row.addWidget(btn_plus)
        target_row.addWidget(norm_unit)
        cl.addLayout(target_row)

        self._content_l.addWidget(card)

    # ── inline rename ─────────────────────────────────────────────────────────

    def _inline_rename_layer(self):
        """Double-click no nome: substitui label por entry inline."""
        self._name_lbl.hide()
        entry = QLineEdit(self._item.name)
        entry.setFixedHeight(24)
        entry.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; font-weight: bold; "
            f"font-size: 9pt; border: 1px solid {self._color}; "
            "border-radius: 4px; padding: 0 6px;"
        )
        ok_btn = QPushButton("✓")
        ok_btn.setFixedSize(28, 24)
        ok_btn.setStyleSheet(
            f"QPushButton {{ background: {self._color}; color: #000; font-weight: bold; "
            "font-size: 11pt; border: none; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}"
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(entry)
        row.addWidget(ok_btn)
        container = QWidget()
        container.setLayout(row)
        self._hdr_frame.layout().insertWidget(1, container)
        entry.setFocus()
        entry.selectAll()

        def _confirm():
            new_name = entry.text().strip()
            if new_name:
                self._item.name = new_name
                if self._project:
                    self._project.save(PROJECTS_DIR)
            container.deleteLater()
            self._name_lbl.setText(f"♫ {self._item.name[:24]}")
            self._name_lbl.show()

        ok_btn.clicked.connect(_confirm)
        entry.returnPressed.connect(_confirm)

    # ── refs registration ─────────────────────────────────────────────────────

    def _register_refs(self):
        """Registra referências no dict compartilhado com o painel orquestrador."""
        self._layer_refs.setdefault(self._item.id, {})
        self._layer_refs[self._item.id].update({
            "waveform":     self.waveform,
            "time_lbl":     self._time_lbl,
            "play_btn":     self._play_btn,
            "color":        self._color,
            "current_time": 0.0,
            "loop_cb":      self._loop_cb,
            "cut_btn":      self._cut_btn,
            "cut_confirm":  self._cut_confirm,
            "cut_waveform": self.waveform,
            "action_row":   self._action_row,
        })

    # ── public helpers ────────────────────────────────────────────────────────

    @property
    def item_id(self):
        return self._item.id

    def set_play_state(self, playing: bool):
        """Atualiza visual do botão Play/Stop."""
        if playing:
            self._play_btn.setText("■ Stop")
            self._play_btn.setStyleSheet(
                f"background: {C['danger']}; color: {C['text']}; "
                "font-weight: bold; border-radius: 10px; padding: 4px 12px;"
            )
        else:
            self._play_btn.setText("▶ Play")
            self._play_btn.setStyleSheet(
                f"background: {self._color}; color: {C['dark_text']}; "
                "font-weight: bold; border-radius: 10px; padding: 4px 12px;"
            )

    def update_time_label(self, current: float, total: float):
        self._time_lbl.setText(f"{current:.1f}s / {total:.1f}s")

    def is_loop(self) -> bool:
        return self._loop_cb.isChecked()
