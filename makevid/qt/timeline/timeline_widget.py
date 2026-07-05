"""Timeline Widget Qt - QGraphicsView com zoom, scroll, speed e tracks."""

import logging
from PySide6.QtWidgets import (
    QGraphicsView, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter
from pathlib import Path

from makevid.qt.theme import C
from makevid.qt.timeline.timeline_scene import TimelineScene
from makevid.qt.timeline.selection_state import SelectionState

_log = logging.getLogger("timeline")


class TimelineWidget(QWidget):
    """Widget completo da timeline: toolbar + QGraphicsView."""

    playhead_moved = Signal(float)
    export_requested = Signal()       # botão EXPORTAR direto
    export_config_requested = Signal() # botão ▲ config

    LBL_W = 62
    RULER_H = 28
    TRACK_GAP = 6

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.zoom = 50
        self.playhead_pos = 0.0
        self.playback_speed = 1.0
        self.scroll_x = 0
        self._split_mode = False
        self._audio_split_mode = None
        self.selection = SelectionState()
        self.collapsed_tracks = set()  # tracks colapsadas

        self._build_ui()
        self.setFocusPolicy(Qt.StrongFocus)
        self._redraw_timer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(50)
        self._redraw_timer.timeout.connect(self.redraw)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = self._build_toolbar()
        layout.addWidget(self._toolbar)

        self._scene = TimelineScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setDragMode(QGraphicsView.NoDrag)
        self._view.setTransformationAnchor(QGraphicsView.NoAnchor)
        self._view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self._view.setStyleSheet("background: rgba(8,12,22,0.92); border: none;")
        self._view.viewport().setStyleSheet("background: rgba(8,12,22,0.92);")
        self._view.setInteractive(True)
        self._view.setAcceptDrops(True)
        self._view.dragEnterEvent = self._on_drag_enter
        self._view.dragMoveEvent = self._on_drag_move
        self._view.dragLeaveEvent = self._on_drag_leave
        self._view.dropEvent = self._on_drop
        self._view.resizeEvent = self._on_view_resize
        self._view.mousePressEvent = self._on_view_mouse_press
        self._view.mouseReleaseEvent = self._on_view_mouse_release
        self._view.mouseMoveEvent = self._on_view_mouse_move
        self._view.leaveEvent = self._on_view_leave
        layout.addWidget(self._view)

        # Timer global de animação para clips (preview contínuo)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(200)
        self._anim_timer.timeout.connect(self._tick_clip_animation)
        self._anim_timer.start()

    def _tick_clip_animation(self):
        from makevid.qt.timeline.clip_item import ClipGraphicsItem
        ClipGraphicsItem.tick_animation()
        self._scene.update()  # repinta a scene inteira de uma vez, não item por item

    def _build_toolbar(self) -> QWidget:
        tb = QWidget()
        tb.setFixedHeight(38)
        tb.setStyleSheet(
            "background: transparent; border: none;"
            f"QPushButton#tlZoomBtn {{"
            f"  background: rgba(18,28,44,0.95);"
            f"  color: {C['text']};"
            "  border: 1px solid rgba(255,255,255,0.34);"
            "  border-radius: 4px;"
            "  padding: 0;"
            "  font-size: 10pt;"
            "  font-weight: bold;"
            "}"
            f"QPushButton#tlZoomBtn:hover {{"
            f"  background: rgba(28,42,64,0.98);"
            f"  border-color: {C['primary']};"
            "}"
            f"QPushButton#tlZoomBtn:pressed {{"
            f"  background: rgba(42,58,86,1.0);"
            "}"
        )
        h = QHBoxLayout(tb)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(6)

        # Title
        lbl = QLabel("TIMELINE")
        lbl.setStyleSheet(f"color: {C['primary']}; font-weight: bold; font-size: 9pt; letter-spacing: 1px;")
        lbl.setToolTip("Timeline principal")
        h.addWidget(lbl)

        self._sep(h)

        # Zoom
        lbl_z = QLabel("Zoom")
        lbl_z.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        h.addWidget(lbl_z)
        btn_zm = QPushButton("-")
        btn_zm.setObjectName("tlZoomBtn")
        btn_zm.setFixedSize(28, 24)
        btn_zm.setStyleSheet(
            "QPushButton {"
            "background: transparent;"
            "color: #ffffff;"
            "border: none;"
            "padding: 0;"
            "font-size: 12pt;"
            "font-weight: bold;"
            "}"
            "QPushButton:hover { color: #cfe3ff; }"
            "QPushButton:pressed { color: #8fb8ff; }"
        )
        btn_zm.setToolTip("Diminuir zoom")
        btn_zm.clicked.connect(lambda: self._adjust_zoom(-10))
        h.addWidget(btn_zm)

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(5, 300)
        self._zoom_slider.setValue(self.zoom)
        self._zoom_slider.setFixedWidth(80)
        self._zoom_slider.setToolTip("Zoom da timeline")
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        h.addWidget(self._zoom_slider)

        btn_zp = QPushButton("+")
        btn_zp.setObjectName("tlZoomBtn")
        btn_zp.setFixedSize(28, 24)
        btn_zp.setStyleSheet(
            "QPushButton {"
            "background: transparent;"
            "color: #ffffff;"
            "border: none;"
            "padding: 0;"
            "font-size: 12pt;"
            "font-weight: bold;"
            "}"
            "QPushButton:hover { color: #cfe3ff; }"
            "QPushButton:pressed { color: #8fb8ff; }"
        )
        btn_zp.setToolTip("Aumentar zoom")
        btn_zp.clicked.connect(lambda: self._adjust_zoom(10))
        h.addWidget(btn_zp)

        self._sep(h)

        # Scroll horizontal
        lbl_s = QLabel("Scroll")
        lbl_s.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        h.addWidget(lbl_s)
        self._scroll_slider = QSlider(Qt.Horizontal)
        self._scroll_slider.setRange(0, 1000)
        self._scroll_slider.setValue(0)
        self._scroll_slider.setFixedWidth(100)
        self._scroll_slider.setToolTip("Deslocar horizontalmente na timeline")
        self._scroll_slider.valueChanged.connect(self._on_scroll_changed)
        h.addWidget(self._scroll_slider)

        self._sep(h)

        # Speed
        lbl_sp = QLabel("Speed")
        lbl_sp.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        h.addWidget(lbl_sp)

        btn_sm = QLabel(" ◀ ")
        btn_sm.setFixedSize(18, 22)
        btn_sm.setAlignment(Qt.AlignCenter)
        btn_sm.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        btn_sm.setCursor(Qt.PointingHandCursor)
        btn_sm.setToolTip("Diminuir velocidade")
        btn_sm.mousePressEvent = lambda e: self._adjust_speed(-0.25)
        h.addWidget(btn_sm)

        self._speed_entry = QLineEdit("1.00")
        self._speed_entry.setFixedSize(48, 22)
        self._speed_entry.setAlignment(Qt.AlignCenter)
        self._speed_entry.setToolTip("Velocidade (0.25 a 4.0)")
        self._speed_entry.setStyleSheet(
            f"background: transparent; color: {C['text']}; border: none; "
            f"font-family: Consolas; font-size: 10pt; font-weight: bold; padding: 0;")
        self._speed_entry.returnPressed.connect(self._on_speed_enter)
        h.addWidget(self._speed_entry)

        btn_sp = QLabel(" ▶ ")
        btn_sp.setFixedSize(18, 22)
        btn_sp.setAlignment(Qt.AlignCenter)
        btn_sp.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        btn_sp.setCursor(Qt.PointingHandCursor)
        btn_sp.setToolTip("Aumentar velocidade")
        btn_sp.mousePressEvent = lambda e: self._adjust_speed(0.25)
        h.addWidget(btn_sp)

        self._sep(h)

        # Loop
        from PySide6.QtWidgets import QCheckBox
        self._loop_cb = QCheckBox("Loop")
        self._loop_cb.setStyleSheet(
            f"QCheckBox {{ color: {C['text3']}; font-size: 8pt; font-weight: bold; spacing: 4px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; border: 2px solid {C['cyan']}; background: transparent; }}"
            f"QCheckBox::indicator:checked {{ background: {C['cyan']}; }}"
            f"QCheckBox::indicator:hover {{ border: 2px solid {C['gold']}; }}")
        self._loop_cb.setToolTip("Repetir playback em loop")
        h.addWidget(self._loop_cb)

        h.addStretch()

        # Time label
        self._time_label = QLabel("00:00.0 / 00:00.0")
        self._time_label.setStyleSheet(
            f"color: {C['text']}; font-family: Consolas; font-size: 10pt; font-weight: bold;")
        h.addWidget(self._time_label)

        self._sep(h)

        # Export: seta config + botao EXPORTAR com hover
        btn_exp_cfg = QPushButton("\u25b2")
        btn_exp_cfg.setFixedSize(22, 20)
        btn_exp_cfg.setToolTip("Configuracao de export")
        btn_exp_cfg.setStyleSheet(
            f"QPushButton {{ background: {C['purple']}; color: #ffffff; font-size: 12pt; "
            f"font-family: 'Segoe UI Symbol'; "
            f"border: 1px solid #bb77ff; border-radius: 3px; padding: 0; }}"
            f"QPushButton:hover {{ background: #bb77ff; border: 2px solid #ffd700; }}")
        btn_exp_cfg.clicked.connect(self._on_export_config)
        h.addWidget(btn_exp_cfg)

        btn_exp = QPushButton("EXPORTAR")
        btn_exp.setFixedHeight(22)
        btn_exp.setToolTip("Exportar video final")
        btn_exp.setStyleSheet(
            f"QPushButton {{ background: {C['purple']}; color: {C['text']}; font-weight: bold; "
            f"font-size: 8pt; border: 1px solid #bb77ff; border-radius: 3px; padding: 2px 10px; }}"
            f"QPushButton:hover {{ background: #9955cc; border: 1px solid #ffd700; }}")
        btn_exp.clicked.connect(self._on_export_direct)
        h.addWidget(btn_exp)

        return tb

    def _sep(self, layout):
        """Separador vertical na toolbar."""
        sep = QLabel()
        sep.setFixedSize(1, 16)
        sep.setStyleSheet(f"background: {C['border']};")
        layout.addWidget(sep)

    # ============================================================
    # PUBLIC
    # ============================================================

    @property
    def loop_enabled(self):
        return self._loop_cb.isChecked()

    # Compatibilidade com código existente.
    @property
    def _selected_clip_id(self):
        return self.selection.selected_clip_id

    @_selected_clip_id.setter
    def _selected_clip_id(self, value):
        self.selection.selected_clip_id = value

    @property
    def _selected_track_item_id(self):
        return self.selection.selected_track_item_id

    @_selected_track_item_id.setter
    def _selected_track_item_id(self, value):
        self.selection.selected_track_item_id = value

    @property
    def _active_track_key(self):
        return self.selection.active_track_key

    @_active_track_key.setter
    def _active_track_key(self, value):
        self.selection.active_track_key = value

    def redraw(self):
        if not self.project:
            self._scene.rebuild_empty()
            self._update_time_label()
            return
        self._scene.rebuild(self.project, self.zoom, self.playhead_pos,
                            self.selection.selected_track_item_id,
                            self.selection.selected_clip_id,
                            self.selection.active_track_key)
        self._update_time_label()

    def set_active_track(self, track_key):
        valid = {"video", "fx", "voice", "sfx", "music", "audio"}
        new_key = track_key if track_key in valid else None
        if self.selection.active_track_key == new_key:
            return
        self.selection.active_track_key = new_key
        self.redraw()

    def clear_active_track(self):
        self.set_active_track(None)

    def _on_project_changed(self, proj):
        self.project = proj
        self.playhead_pos = 0.0
        self.redraw()

    def set_playhead(self, time_pos: float):
        self.playhead_pos = max(0, time_pos)
        self._scene.update_playhead(self.playhead_pos, self.zoom)
        self._update_time_label()
        self.playhead_moved.emit(self.playhead_pos)

    # ============================================================
    # SLOTS
    # ============================================================

    def _adjust_zoom(self, delta):
        self.zoom = max(5, min(300, self.zoom + delta))
        self._zoom_slider.setValue(self.zoom)
        self.redraw()

    def _on_zoom_changed(self, value):
        self.zoom = value
        self.redraw()

    def _on_scroll_changed(self, value):
        total_dur = max(self.project.total_duration(), 10)
        total_w = total_dur * self.zoom
        canvas_w = self._view.viewport().width() or 800
        max_scroll = max(0, total_w - canvas_w + 100)
        self.scroll_x = int((value / 1000) * max_scroll)
        self._view.horizontalScrollBar().setValue(self.scroll_x)
        self.redraw()

    def _adjust_speed(self, delta):
        self.playback_speed = max(0.25, min(4.0, self.playback_speed + delta))
        self._speed_entry.setText(f"{self.playback_speed:.2f}")
        try:
            app = self.window()
            if hasattr(app, 'preview') and app.preview.player.is_playing:
                app.preview.player.set_speed(self.playback_speed)
        except AttributeError:
            pass

    def _on_speed_enter(self):
        try:
            val = float(self._speed_entry.text().replace(",", "."))
            self.playback_speed = max(0.25, min(4.0, val))
        except ValueError:
            pass
        self._speed_entry.setText(f"{self.playback_speed:.2f}")
        try:
            app = self.window()
            if hasattr(app, 'preview') and app.preview.player.is_playing:
                app.preview.player.set_speed(self.playback_speed)
        except AttributeError:
            pass

    def _on_export_direct(self):
        self.export_requested.emit()

    def _on_export_config(self):
        self.export_config_requested.emit()

    def _update_time_label(self):
        if not self.project:
            self._time_label.setText("00:00.0 / 00:00.0")
            return
        total = self.project.total_duration()
        pm, ps = int(self.playhead_pos) // 60, self.playhead_pos % 60
        tm, ts = int(total) // 60, total % 60
        self._time_label.setText(f"{pm:02d}:{ps:04.1f} / {tm:02d}:{ts:04.1f}")

    # ============================================================
    # EVENTS
    # ============================================================

    def wheelEvent(self, event):
        """Ctrl+scroll=zoom, Shift+scroll=volume, normal=scroll horizontal."""
        if event.modifiers() & Qt.ControlModifier:
            delta = 5 if event.angleDelta().y() > 0 else -5
            self._adjust_zoom(delta)
        elif event.modifiers() & Qt.ShiftModifier:
            self._on_volume_scroll(event)
        else:
            delta = event.angleDelta().y()
            self.scroll_x = max(0, self.scroll_x - delta // 2)
            self._view.horizontalScrollBar().setValue(self.scroll_x)
            self.redraw()
        event.accept()

    def keyPressEvent(self, event):
        """Space=play/pause, Delete=remove selecionado, Escape=sai de split mode."""
        key = event.key()
        if key == Qt.Key_Space:
            # Futuro: play/pause via player
            pass
        elif key == Qt.Key_Delete:
            self._on_delete()
        elif key == Qt.Key_Escape:
            self._exit_split_mode()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double-click no widget: delegado para a scene via view."""
        # O evento de double-click dentro da view é tratado pela QGraphicsScene
        # Este handler só pega clicks fora da view (toolbar area)
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Redesenha em tempo real durante o arraste de resize.
        self.redraw()

    def _on_view_leave(self, event):
        self._scene.update_hover(None)
        event.accept()

    def _on_view_resize(self, event):
        QGraphicsView.resizeEvent(self._view, event)
        # Atualiza imediatamente enquanto a view é redimensionada.
        self.redraw()

    def _on_view_mouse_press(self, event):
        pos = self._view.mapToScene(event.pos())
        self._scene.on_mouse_press(pos, event.button())
        event.accept()

    def _on_view_mouse_release(self, event):
        pos = self._view.mapToScene(event.pos())
        self._scene.on_mouse_release(pos)
        event.accept()

    def _on_view_mouse_move(self, event):
        pos = self._view.mapToScene(event.pos())
        self._scene.on_mouse_move(pos, event.buttons())
        self._scene.update_hover(pos)
        event.accept()

    # ============================================================
    # VOLUME SCROLL (Shift+wheel)
    # ============================================================

    def _on_volume_scroll(self, event):
        """Shift+Scroll ajusta volume da track sob o mouse."""
        pos = self._view.mapToScene(event.position().toPoint())
        y = pos.y()
        track_positions = self._scene._track_pos

        track_key = None
        for name in ("voice", "sfx", "music", "audio"):
            if name in track_positions and name not in getattr(self, 'collapsed_tracks', set()):
                ty, th = track_positions[name]
                if ty <= y <= ty + th:
                    track_key = name
                    break

        if not track_key:
            return

        delta = 0.05 if event.angleDelta().y() > 0 else -0.05
        vol = self.project.track_volumes.get(track_key, 1.0)
        vol = max(0.0, min(2.0, vol + delta))
        self.project.track_volumes[track_key] = round(vol, 2)

        from makevid.config import PROJECTS_DIR
        self.project.save(PROJECTS_DIR)
        self.redraw()

    # ============================================================
    # DELETE
    # ============================================================

    def _on_delete(self):
        """Remove track item selecionado (clicado)."""
        from makevid.config import PROJECTS_DIR

        # Só apaga se tem um track item selecionado via interação
        selected_id = getattr(self, '_selected_track_item_id', None)
        if not selected_id:
            return

        item = next((i for i in self.project.track_items if i.id == selected_id), None)
        if item:
            self.project.remove_track_item(item.id)
            self._selected_track_item_id = None
            self.project.save(PROJECTS_DIR)
            self.redraw()

    # ============================================================
    # SPLIT MODE
    # ============================================================

    def enter_split_mode(self):
        """Ativa modo de corte: proximo click divide clip/item."""
        self._split_mode = True
        self._view.setCursor(Qt.CrossCursor)

    def enter_audio_split_mode(self, track):
        """Ativa modo de corte para faixa de audio especifica."""
        self._audio_split_mode = track
        self._view.setCursor(Qt.CrossCursor)

    def _exit_split_mode(self):
        """Sai de qualquer modo de split."""
        self._split_mode = False
        self._audio_split_mode = None
        self._view.setCursor(Qt.ArrowCursor)

    # ============================================================
    # DRAG-AND-DROP (arquivos do SO)
    # ============================================================

    def _drop_scene_pos(self, event):
        try:
            p = event.position().toPoint()
        except Exception:
            p = event.pos()
        return self._view.mapToScene(p)

    def _track_at_scene_pos(self, pos):
        for name, (ty, th) in self._scene._track_pos.items():
            if ty <= pos.y() <= ty + th:
                return name
        return None

    def _time_at_scene_pos(self, pos):
        return max(0.0, (pos.x() - self.LBL_W) / max(1, self.zoom))

    def _clip_position_at_time(self, t):
        clips = sorted(self.project.clips, key=lambda c: c.position)
        if not clips:
            return 0
        cur = 0.0
        for i, c in enumerate(clips):
            if t < cur + c.duration:
                return i
            cur += c.duration
        return len(clips)

    def _on_drag_enter(self, event):
        md = event.mimeData()
        if md.hasUrls() or md.hasFormat("application/x-makevid-track-item"):
            pos = self._drop_scene_pos(event)
            self._scene.update_hover(pos)
            event.acceptProposedAction()

    def _on_drag_move(self, event):
        md = event.mimeData()
        if md.hasUrls() or md.hasFormat("application/x-makevid-track-item"):
            pos = self._drop_scene_pos(event)
            self._scene.update_hover(pos)
            event.acceptProposedAction()

    def _on_drag_leave(self, event):
        self._scene.update_hover(None)
        event.accept()

    def _on_drop(self, event):
        """Arquivos soltos na timeline: audio → track audio, video → clip."""
        import shutil
        from makevid.config import AUDIO_DIR, OUTPUTS_DIR

        md = event.mimeData()
        pos = self._drop_scene_pos(event)
        drop_track = self._track_at_scene_pos(pos)
        drop_time = self._time_at_scene_pos(pos)
        self._scene.update_hover(None)

        if md.hasFormat("application/x-makevid-track-item"):
            item_id = bytes(md.data("application/x-makevid-track-item")).decode("utf-8", errors="ignore").strip()
            item = next((i for i in self.project.track_items if i.id == item_id), None)
            if item is not None:
                if drop_track in {"voice", "sfx", "music", "audio"}:
                    item.track = drop_track
                item.start_time = round(max(0.0, drop_time), 3)
                from makevid.config import PROJECTS_DIR
                self.project.save(PROJECTS_DIR)
                self.redraw()
                event.acceptProposedAction()
                return

        urls = md.urls()
        if not urls:
            return

        audio_exts = {'.wav', '.mp3', '.ogg', '.flac'}
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

        for url in urls:
            path = Path(url.toLocalFile())
            if not path.exists():
                continue

            ext = path.suffix.lower()

            if ext in audio_exts:
                # Importar como item de track no ponto solto.
                dest_dir = AUDIO_DIR / self.project.id
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / path.name
                if not dest.exists():
                    shutil.copy2(str(path), str(dest))
                dur = 5.0
                try:
                    from makevid.core.audio_utils import get_audio_duration
                    dur = get_audio_duration(str(dest)) or 5.0
                except Exception:
                    pass

                target_track = drop_track if drop_track in {"voice", "sfx", "music", "audio"} else "audio"
                self.project.add_track_item(
                    name=path.stem[:20],
                    track=target_track,
                    start_time=drop_time,
                    duration=dur,
                    file_path=str(dest),
                    params={"block_name": f"\U0001f4c2 {path.stem[:12]}"},
                )

            elif ext in video_exts:
                # Importar como clip de video no ponto solto da timeline.
                dest_dir = OUTPUTS_DIR / self.project.id
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / path.name
                if not dest.exists():
                    shutil.copy2(str(path), str(dest))
                from makevid.core.timeline import get_video_duration
                dur = get_video_duration(str(dest)) or 5.0
                clip_pos = self._clip_position_at_time(drop_time)
                clip = self.project.add_clip(prompt=path.stem, position=clip_pos)
                clip.video_path = str(dest)
                clip.duration = dur
                clip.status = "done"

        from makevid.config import PROJECTS_DIR
        self.project.save(PROJECTS_DIR)
        self.redraw()
        event.acceptProposedAction()
