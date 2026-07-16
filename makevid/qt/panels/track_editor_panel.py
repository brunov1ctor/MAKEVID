"""Track Editor Panel — orquestrador do editor de layers de áudio."""

import logging
import time as _time
import threading

import numpy as np
import soundfile as sf
import sounddevice as sd

_log = logging.getLogger(__name__)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QSizePolicy, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR
from makevid.services.waveform_cut_service import WaveformCutService
from makevid.core.audio_utils import slice_volume_keyframes

from makevid.qt.panels.layer_widget import LayerWidget
from makevid.qt.panels.layer_cut_controller import LayerCutController
from makevid.qt.panels.layer_audio_player import (
    _LayerStreamPlayer, _prepare_audio, _file_exists,
)
from makevid.qt.panels.layer_ui_components import _ResponsiveActionGrid

TRACK_COLORS = {
    "voice": C["track_voice"], "sfx": C["track_sfx"],
    "music": C["track_music"], "audio": C["track_audio"],
}
TRACK_TITLES = {
    "voice": "🎤 VOZ", "sfx": "🔊 SFX",
    "music": "🎵 MUSICA", "audio": "🎧 AUDIO",
}


class TrackEditorPanel(QWidget):
    """Orquestrador do editor de layers — monta o painel e delega para LayerWidget."""

    closed  = Signal()
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item           = None
        self._project        = None
        self._playing        = {}        # item_id -> bool
        self._paused_state   = {}        # item_id -> {ratio, time}
        self._layer_refs     = {}        # item_id -> {waveform, time_lbl, play_btn, ...}
        self._layer_frames   = {}        # item_id -> LayerWidget
        self._action_grid    = None
        self._stream_players = {}        # item_id -> _LayerStreamPlayer
        self._anim_gen       = {}        # item_id -> int
        self._cut_service    = WaveformCutService()
        self._cut_ctrl       = LayerCutController(
            self._cut_service, self._layer_refs,
            self._commit_layer_edit, self.changed, self._playing,
        )
        self.setMinimumWidth(0)
        self.setObjectName("trackEditorPanel")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_shell()

    def _build_shell(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

    # ── show_item ─────────────────────────────────────────────────────────────

    def show_item(self, item, project):
        """Popula o editor com os layers do grupo do item."""
        self._item         = item
        self._project      = project
        self._playing      = {}
        self._paused_state = {}
        self._layer_refs   = {}
        self._layer_frames = {}
        self._action_grid  = None
        # Recria o controlador de corte com o novo dict de refs
        self._cut_ctrl = LayerCutController(
            self._cut_service, self._layer_refs,
            self._commit_layer_edit, self.changed, self._playing,
        )

        color = TRACK_COLORS.get(item.track, C["cyan"])
        title = TRACK_TITLES.get(item.track, "AUDIO")

        while self._outer.count():
            child = self._outer.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 8, 10, 6)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 14pt; font-weight: bold; "
            "background: transparent; border: none;"
        )
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self._close)
        hdr_l.addWidget(close_btn)
        self._outer.addLayout(hdr_l)

        info = QLabel(f"  {item.name} · {item.duration:.1f}s · Inicio {item.start_time:.1f}s")
        info.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;"
        )
        self._outer.addWidget(info)

        summary = QFrame()
        summary.setStyleSheet(
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;"
        )
        sl = QHBoxLayout(summary)
        sl.setContentsMargins(10, 8, 10, 8)
        sl.setSpacing(6)
        sl.addWidget(self._chip("TRACK", title, color))
        sl.addWidget(self._chip("DUR", f"{item.duration:.1f}s", C["cyan"]))
        sl.addWidget(self._chip("IN", f"{item.start_time:.1f}s", C["secondary"]))
        sl.addStretch()
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

        group = self._get_group(item)
        layers_lbl = QLabel(f"EDITOR DE SOM · {len(group)} layer(s)")
        layers_lbl.setStyleSheet(
            f"color: {color}; font-size: 9pt; font-weight: bold; "
            "letter-spacing: 1px; border: none;"
        )
        L.addWidget(layers_lbl)

        for layer_item in sorted(group, key=lambda i: i.start_time):
            lw = LayerWidget(
                layer_item, project, color,
                self._cut_service, self._layer_refs,
            )
            lw.play_requested.connect(self._on_play_requested)
            lw.seek_requested.connect(self._seek_play)
            lw.cut_applied.connect(self._on_cut_applied)
            lw.changed.connect(self._on_layer_change)
            lw.delete_requested.connect(self._delete_layer)
            lw.duplicate_requested.connect(self._duplicate)
            self._layer_frames[layer_item.id] = lw
            L.addWidget(lw)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.08);")
        L.addWidget(sep)

        action_grid = _ResponsiveActionGrid()
        self._action_grid = action_grid
        L.addWidget(action_grid)

        play_all_btn = QPushButton("▶ PLAY CONJUNTO")
        play_all_btn.setFixedHeight(28)
        play_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        play_all_btn.setStyleSheet(
            f"background: rgba(255,255,255,0.05); color: {color}; font-weight: bold; "
            f"font-size: 10pt; border: 1px solid {color}; border-radius: 10px; padding: 2px 10px;"
        )
        play_all_btn.clicked.connect(lambda: self._play_all(group, color))
        action_grid.add_widget(play_all_btn)

        rename_btn = QPushButton("✏ RENOMEAR")
        rename_btn.setFixedHeight(28)
        rename_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rename_btn.setStyleSheet(
            f"background: rgba(255,255,255,0.07); color: {color}; font-weight: bold; "
            f"font-size: 10pt; border: 1px solid {color}; border-radius: 10px; padding: 2px 10px;"
        )
        rename_btn.clicked.connect(lambda: self._rename_block(item, color))
        action_grid.add_widget(rename_btn)

        save_btn = QPushButton("SALVAR")
        save_btn.setFixedHeight(28)
        save_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        save_btn.setStyleSheet(
            f"background: {color}; color: {C['dark_text']}; font-weight: bold; "
            "font-size: 10pt; border-radius: 10px; padding: 2px 10px;"
        )
        save_btn.clicked.connect(lambda: project.save(PROJECTS_DIR))
        action_grid.add_widget(save_btn)
        action_grid.finalize()

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
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 999px;"
        )
        cl = QHBoxLayout(chip)
        cl.setContentsMargins(10, 4, 10, 4)
        cl.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;"
        )
        val = QLabel(value)
        val.setStyleSheet(
            f"color: {color}; font-size: 8pt; font-family: Consolas; "
            "font-weight: bold; border: none;"
        )
        cl.addWidget(lbl)
        cl.addWidget(val)
        return chip

    # ── signal handlers ───────────────────────────────────────────────────────

    def _on_play_requested(self, item):
        """Recebido de LayerWidget.play_requested — toggle play/pause."""
        lw = self._layer_frames.get(item.id)
        if self._playing.get(item.id, False):
            self._pause_play(item)
        else:
            self._start_play(item)

    def _on_cut_applied(self, item, waveform, cut_btn):
        lw = self._layer_frames.get(item.id)
        self._cut_ctrl.apply_cut(item, waveform, cut_btn, lw)

    def _on_layer_change(self, item, commit):
        if commit and self._project is not None:
            self._project.save(PROJECTS_DIR)
        self.changed.emit()

    # ── play / pause / stop ───────────────────────────────────────────────────

    def _pause_play(self, item):
        stream = self._stream_players.pop(item.id, None)
        if stream:
            stream.stop()
        try:
            sd.stop()
        except Exception:
            _log.debug("Erro ao parar sd (pause)", exc_info=True)
        self._playing[item.id] = False
        refs = self._layer_refs.get(item.id, {})
        if refs:
            wf = refs.get("waveform")
            self._paused_state[item.id] = {
                "ratio": max(0.0, min(1.0, wf._playhead_ratio if wf and wf._playhead_ratio >= 0 else 0.0)),
                "time":  float(refs.get("current_time", 0.0)),
            }
        lw = self._layer_frames.get(item.id)
        if lw:
            lw.set_play_state(False)

    def _start_play(self, item):
        if not _file_exists(item.file_path):
            return
        try:
            data, sr = _prepare_audio(item)
            if data is None or len(data) == 0:
                return

            if self._cut_service.is_active(item.id) and self._cut_service.has_selection():
                keep, prev = [], 0
                for cut_a, cut_b in sorted(self._cut_service.get_selections()):
                    ca = max(0, min(int(cut_a * len(data)), len(data)))
                    cb = max(ca, min(int(cut_b * len(data)), len(data)))
                    if ca > prev:
                        keep.append(data[prev:ca])
                    prev = cb
                if prev < len(data):
                    keep.append(data[prev:])
                data = np.concatenate(keep) if keep else np.zeros((0, 2), dtype=np.float32)

            if len(data) == 0:
                return

            paused      = self._paused_state.pop(item.id, None)
            start_ratio = max(0.0, min(1.0, float(paused["ratio"]) if paused else 0.0))
            speed       = int(item.params.get("speed", 100)) / 100.0
            play_sr     = int(sr * speed) if speed > 0 else sr

            lw   = self._layer_frames.get(item.id)
            loop = lw.is_loop() if lw else False

            old = self._stream_players.pop(item.id, None)
            if old:
                old.stop()
            sd.stop()

            single_duration = len(data) / max(1, play_sr)

            if loop:
                stream = _LayerStreamPlayer(data, play_sr, item)
                stream.start(start_ratio)
                self._stream_players[item.id] = stream
            else:
                vol = int(item.params.get("volume", 80)) / 100.0
                pan = int(item.params.get("pan", 0)) / 100.0
                out = data[int(start_ratio * len(data)):].copy()
                out *= vol
                if pan != 0.0:
                    angle = (pan + 1.0) * np.pi / 4.0
                    out[:, 0] *= float(np.cos(angle))
                    out[:, 1] *= float(np.sin(angle))
                sd.play(np.ascontiguousarray(np.clip(out, -1, 1).astype(np.float32)), samplerate=play_sr)

            self._playing[item.id] = True
            if lw:
                lw.set_play_state(True)
            self._animate_playhead(item.id, start_ratio, single_duration, loop=loop)
        except Exception:
            _log.exception("Erro ao reproduzir audio")

    def _stop_play(self, item_id):
        stream = self._stream_players.pop(item_id, None)
        if stream:
            stream.stop()
        try:
            sd.stop()
        except Exception:
            _log.debug("Erro ao parar sd (stop)", exc_info=True)
        self._playing[item_id] = False
        refs = self._layer_refs.get(item_id, {})
        wf   = refs.get("waveform")
        if wf:
            wf.set_playhead(-1)
        lw = self._layer_frames.get(item_id)
        color = refs.get("color", C["cyan"])
        if lw:
            lw.set_play_state(False)

    def _play_all(self, group, color):
        def run():
            try:
                sr   = 44100
                base = min(i.start_time for i in group)
                end  = max(i.start_time + i.duration for i in group)
                total_samples = int((end - base) * sr)
                if total_samples <= 0:
                    return
                mix = np.zeros((total_samples, 2), dtype=np.float32)
                for it in group:
                    if not _file_exists(it.file_path):
                        continue
                    data, item_sr = sf.read(it.file_path, dtype="float32")
                    if len(data.shape) == 1:
                        data = np.column_stack([data, data])
                    if item_sr != sr:
                        new_len = int(len(data) * sr / item_sr)
                        data = np.column_stack([
                            np.interp(np.linspace(0, len(data)-1, new_len), np.arange(len(data)), data[:, 0]),
                            np.interp(np.linspace(0, len(data)-1, new_len), np.arange(len(data)), data[:, 1]),
                        ])
                    vol = int(it.params.get("volume", 80)) / 100.0
                    data *= vol
                    s = int((it.start_time - base) * sr)
                    e = min(s + len(data), total_samples)
                    mix[s:e] += data[:e-s]
                sd.stop()
                sd.play(np.ascontiguousarray(np.clip(mix, -1, 1).astype(np.float32)), samplerate=sr)
            except Exception:
                _log.exception("Erro ao reproduzir audio (play all)")
        threading.Thread(target=run, daemon=True).start()

    # ── playhead animation ────────────────────────────────────────────────────

    def _animate_playhead(self, item_id, start_ratio, play_duration, loop=False):
        refs = self._layer_refs.get(item_id)
        if not refs:
            return
        gen = self._anim_gen.get(item_id, 0) + 1
        self._anim_gen[item_id] = gen
        waveform   = refs["waveform"]
        time_lbl   = refs["time_lbl"]
        start_time = _time.time()

        def _tick():
            if self._anim_gen.get(item_id, 0) != gen:
                return
            if not self._playing.get(item_id, False):
                waveform.set_playhead(-1)
                return
            elapsed = _time.time() - start_time
            if elapsed >= play_duration:
                if loop:
                    self._animate_playhead(item_id, 0.0, play_duration, loop=True)
                    return
                self._playing[item_id] = False
                waveform.set_playhead(-1)
                lw = self._layer_frames.get(item_id)
                if lw:
                    lw.set_play_state(False)
                item_dur = float(waveform._item.duration)
                refs["current_time"] = item_dur
                time_lbl.setText(f"{item_dur:.1f}s / {item_dur:.1f}s")
                return
            audio_ratio  = min(1.0, start_ratio + (elapsed / play_duration) * (1.0 - start_ratio))
            visual_ratio = waveform._audio_ratio_to_visual(audio_ratio)
            waveform._playhead_ratio = visual_ratio
            waveform.update()
            item_dur = float(waveform._item.duration)
            current  = audio_ratio * item_dur
            refs["current_time"] = current
            lw = self._layer_frames.get(item_id)
            if lw:
                lw.update_time_label(current, item_dur)
            QTimer.singleShot(33, _tick)

        QTimer.singleShot(33, _tick)

    # ── seek ──────────────────────────────────────────────────────────────────

    def _seek_play(self, item, ratio):
        if not _file_exists(item.file_path):
            return
        try:
            data, sr = _prepare_audio(item)
            if data is None or len(data) == 0:
                return
            refs     = self._layer_refs.get(item.id, {})
            waveform = refs.get("waveform")
            audio_ratio  = waveform._visual_ratio_to_audio(ratio) if waveform else ratio
            audio_ratio  = max(0.0, min(1.0, audio_ratio))
            start_sample = int(audio_ratio * len(data))
            if start_sample >= len(data):
                start_sample, audio_ratio = 0, 0.0
            data = data[start_sample:]
            play_duration = len(data) / max(1, sr)
            sd.stop()
            sd.play(np.ascontiguousarray(np.clip(data, -1.0, 1.0).astype(np.float32)), samplerate=sr)
            self._playing[item.id] = True
            lw = self._layer_frames.get(item.id)
            if lw:
                lw.set_play_state(True)
            self._animate_playhead(item.id, audio_ratio, play_duration)
        except Exception:
            _log.exception("Erro ao reproduzir audio (seek)")

    # ── layer actions ─────────────────────────────────────────────────────────

    def _duplicate(self, item):
        self._project.add_track_item(
            name=item.name, track=item.track,
            start_time=item.start_time, duration=item.duration,
            file_path=item.file_path, params=dict(item.params),
            clip_index=item.clip_index,
        )
        self._project.save(PROJECTS_DIR)
        self.show_item(self._item, self._project)

    def _delete_layer(self, item):
        lw  = self._layer_frames.get(item.id)
        if lw is None:
            self._do_delete_layer(item)
            return

        confirm = QFrame()
        confirm.setStyleSheet(
            f"background: rgba(180,30,30,0.18); border: 1px solid {C['danger']}; border-radius: 10px;"
        )
        cl = QHBoxLayout(confirm)
        cl.setContentsMargins(10, 6, 10, 6)
        cl.setSpacing(8)
        lbl = QLabel(f"Remover <b>{item.name[:20]}</b>?")
        lbl.setStyleSheet(
            f"color: {C['text']}; font-size: 9pt; border: none; background: transparent;"
        )
        cl.addWidget(lbl)
        cl.addStretch()
        yes_btn = QPushButton("Remover")
        yes_btn.setFixedHeight(26)
        yes_btn.setStyleSheet(
            f"background: {C['danger']}; color: #fff; font-size: 8pt; "
            "font-weight: bold; border-radius: 8px; padding: 2px 12px;"
        )
        no_btn = QPushButton("Cancelar")
        no_btn.setFixedHeight(26)
        no_btn.setStyleSheet(
            "background: rgba(255,255,255,0.07); color: #A9B4C8; font-size: 8pt; "
            "font-weight: bold; border-radius: 8px; padding: 2px 12px;"
        )
        cl.addWidget(no_btn)
        cl.addWidget(yes_btn)

        lw.layout().insertWidget(0, confirm)
        yes_btn.clicked.connect(lambda: (confirm.deleteLater(), self._do_delete_layer(item)))
        no_btn.clicked.connect(confirm.deleteLater)

    def _do_delete_layer(self, item):
        stream = self._stream_players.pop(item.id, None)
        if stream:
            stream.stop()
        try:
            sd.stop()
        except Exception:
            _log.debug("Erro ao parar sd (delete)", exc_info=True)
        self._project.remove_track_item(item.id)
        self._project.save(PROJECTS_DIR)
        self.changed.emit()
        remaining = self._project.get_track_items(item.track)
        if remaining:
            self.show_item(remaining[0], self._project)
        else:
            self._close()

    def _commit_layer_edit(self, item):
        if self._project is not None:
            self._project.save(PROJECTS_DIR)
        self.changed.emit()

    # ── rename block ──────────────────────────────────────────────────────────

    def _rename_block(self, item, color):
        if getattr(self, "_rename_block_widget", None):
            self._rename_block_widget.deleteLater()
            self._rename_block_widget = None

        current = item.params.get("block_name", item.name)
        entry   = QLineEdit(current)
        entry.setFixedHeight(28)
        entry.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; font-weight: bold; "
            f"font-size: 10pt; border: 1px solid {color}; border-radius: 6px; padding: 0 8px;"
        )
        ok_btn = QPushButton("✓")
        ok_btn.setFixedSize(28, 28)
        ok_btn.setStyleSheet(
            f"QPushButton {{ background: {color}; color: #000; font-weight: bold; "
            f"font-size: 12pt; border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}"
        )
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(entry)
        row.addWidget(ok_btn)
        container = QWidget()
        container.setLayout(row)
        self._rename_block_widget = container
        self._outer.insertWidget(3, container)
        entry.setFocus()
        entry.selectAll()

        def _confirm():
            new_name = entry.text().strip()
            if new_name:
                for gi in self._get_group(item):
                    gi.params["block_name"] = new_name
                if self._project:
                    self._project.save(PROJECTS_DIR)
                self.changed.emit()
            container.deleteLater()
            self._rename_block_widget = None

        ok_btn.clicked.connect(_confirm)
        entry.returnPressed.connect(_confirm)

    # ── close ─────────────────────────────────────────────────────────────────

    def _close(self):
        for stream in self._stream_players.values():
            stream.stop()
        self._stream_players.clear()
        try:
            sd.stop()
        except Exception:
            _log.debug("Erro ao parar sd (close)", exc_info=True)
        self.closed.emit()
        self.hide()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _get_group(self, item):
        all_track = self._project.get_track_items(item.track)
        if item.clip_index >= 0:
            return [i for i in all_track if i.clip_index == item.clip_index]
        return [item]
