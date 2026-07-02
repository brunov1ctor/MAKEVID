"""Preview Widget Qt - Display de video com play/pause e progress bar."""

import numpy as np
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QImage, QPixmap, QFont, QCursor, QPainter,
    QColor, QPolygonF
)

from makevid.qt.theme import C
from makevid.qt.preview.player import TimelinePlayerQt


class _PlayOverlay(QWidget):
    """Botão play — só triângulo, sem círculo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self._pressed = False
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(56, 56)

    def enterEvent(self, event):
        self._hover = True; self.update(); super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False; self.update(); super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True; self.update()
        # Sobe até o PreviewWidget (pai do display) para evitar duplo disparo
        display = self.parent()
        preview = display.parent() if display else None
        if preview and hasattr(preview, '_on_display_click'):
            preview._on_display_click(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        ts = 18.0 if self._pressed else 22.0
        alpha = 180 if self._pressed else (255 if self._hover else 210)
        tx = cx - ts * 0.4
        poly = QPolygonF([
            QPointF(tx, cy - ts * 0.6),
            QPointF(tx, cy + ts * 0.6),
            QPointF(tx + ts, cy),
        ])
        p.setBrush(QColor(255, 255, 255, alpha))
        p.setPen(Qt.NoPen)
        p.drawPolygon(poly)
        p.end()


class PreviewWidget(QWidget):
    """Display de video com controles de playback."""

    def __init__(self, project, timeline_widget, parent=None):
        super().__init__(parent)
        self.project = project
        self.timeline = timeline_widget
        self._is_playing = False

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(6)

        # Display principal
        self._display = QLabel()
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setMinimumSize(200, 80)
        self._display.setStyleSheet(
            f"background: {C['dark']}; "
            f"border: 1px solid {C['glass_border']}; "
            f"border-radius: 16px;")
        self._display.setCursor(QCursor(Qt.PointingHandCursor))
        self._display.mousePressEvent = self._on_display_click
        layout.addWidget(self._display, stretch=1)

        # Overlay play
        self._play_overlay = None

        # Progress bar (estilo YouTube) - escondida quando nao em uso
        self._progress_container = QWidget()
        self._progress_container.setFixedHeight(36)
        self._progress_container.setStyleSheet("background: transparent;")
        pc_layout = QVBoxLayout(self._progress_container)
        pc_layout.setContentsMargins(0, 14, 0, 14)
        pc_layout.setSpacing(0)
        self._progress = QProgressBar()
        self._progress.setFixedHeight(4)
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 2px; }")
        self._progress.setCursor(QCursor(Qt.PointingHandCursor))
        self._progress.setMouseTracking(True)
        self._progress_container.enterEvent = self._on_progress_enter
        self._progress_container.leaveEvent = self._on_progress_leave
        self._progress.mousePressEvent = self._on_progress_click
        pc_layout.addWidget(self._progress)
        self._progress_container.hide()
        layout.addWidget(self._progress_container)

        # Info label
        self._info = QLabel()
        self._info.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        layout.addWidget(self._info)

        # Player
        self.player = TimelinePlayerQt(self)
        self.player.set_project(self.project)

        # Projects panel — inserido dinamicamente ao abrir
        self._projects_panel = None

        # Play button overlay (texto no display)
        self._show_play_button()

    def _connect_signals(self):
        self.player.frame_ready.connect(self._on_frame)
        self.player.playback_ended.connect(self._on_ended)
        self.player.time_updated.connect(self._on_time_update)
        self.timeline.playhead_moved.connect(self._on_playhead_moved)

    def set_has_media(self, value: bool):
        """Notifica o glow layer sobre presença de mídia."""
        glow = getattr(self, '_glow_layer', None)
        if glow:
            glow.set_has_media(value)

    # ============================================================
    # DISPLAY
    # ============================================================

    def _on_frame(self, frame_bgr):
        """Recebe frame BGR do player e mostra no display."""
        h, w, ch = frame_bgr.shape
        # Converter BGR para RGB
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)

        display_size = self._display.size()
        pixmap = QPixmap.fromImage(img).scaled(
            display_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self._display.setPixmap(pixmap)
        self.set_has_media(True)

    def _show_play_button(self, clear_frame=True):
        """Mostra triângulo play centralizado sobre o display."""
        if clear_frame:
            self._display.setPixmap(QPixmap())
            self._display.setText("")
            self._display.setStyleSheet(
                f"background: {C['dark']}; "
                f"border: 1px solid {C['glass_border']}; "
                f"border-radius: 16px;")

        if hasattr(self, '_play_overlay') and self._play_overlay:
            self._play_overlay.deleteLater()

        self._play_overlay = _PlayOverlay(self._display)
        self._center_overlay()
        self._play_overlay.show()

    def _center_overlay(self):
        if hasattr(self, '_play_overlay') and self._play_overlay:
            s = self._play_overlay.width()
            self._play_overlay.move(
                (self._display.width() - s) // 2,
                (self._display.height() - s) // 2,
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_play_overlay') and self._play_overlay and self._play_overlay.isVisible():
            self._center_overlay()
        # Reposicionar props panel se visivel
        if hasattr(self, '_props_panel') and self._props_panel and self._props_panel.isVisible():
            panel_h = int(self._display.height() * 0.95)
            self._props_panel.setFixedHeight(max(200, panel_h))
            self._props_panel.move(max(0, self._display.width() - 235), 5)

    # ============================================================
    # CONTROLES
    # ============================================================

    def _on_display_click(self, event):
        """Click no display = play/pause."""
        if self.player.is_playing:
            self._pause()
        else:
            self._play()

    def _pause(self):
        self._paused_at = self.player._start_offset if not self.player.is_playing else self.player._get_current_time()
        self.player.pause()
        self._is_playing = False
        self._show_play_button(clear_frame=False)

    def _play(self):
        pos = getattr(self, '_paused_at', self.timeline.playhead_pos)
        speed = self.timeline.playback_speed
        self.player.play_from(pos, speed)
        self._paused_at = None
        self._is_playing = True
        self._display.setText("")
        self._display.setStyleSheet(
            f"background: {C['dark']}; border: 1px solid {C['glass_border']}; border-radius: 16px;")
        if hasattr(self, '_play_overlay') and self._play_overlay:
            self._play_overlay.hide()
        self._progress_container.show()

    def _on_progress_click(self, event):
        """Click na barra de progresso = seek."""
        w = self._progress.width()
        if w <= 0:
            return
        ratio = max(0, min(1.0, event.position().x() / w))
        total_dur = self.project.total_duration()
        target = ratio * total_dur
        self.player.seek_to_time(target)
        self.timeline.set_playhead(target)

    def _on_progress_enter(self, event):
        """Hover na barra: cresce e mostra ponteira."""
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(
            "QProgressBar { background: #1a1a2a; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 3px; }")
        if not hasattr(self, '_progress_dot') or not self._progress_dot:
            self._progress_dot = QLabel(self._progress_container)
            self._progress_dot.setFixedSize(30, 30)
            self._progress_dot.setText("\u2734")
            self._progress_dot.setAlignment(Qt.AlignCenter)
            self._progress_dot.setStyleSheet(
                "QLabel { background: transparent; color: #ffffff; font-size: 18pt; "
                "border: none; }")

        val = self._progress.value()
        max_val = self._progress.maximum() or 1
        x_pos = int((val / max_val) * self._progress.width())
        self._progress_dot.move(max(0, x_pos - 15), 3)
        self._progress_dot.show()

    def _on_progress_leave(self, event):
        """Sai do hover: volta fino, esconde ponteira."""
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 2px; }")
        if hasattr(self, '_progress_dot') and self._progress_dot:
            self._progress_dot.hide()

    # ============================================================
    # SIGNALS
    # ============================================================

    def _on_time_update(self, time_pos):
        """Player atualiza posição."""
        total = self.project.total_duration()
        if total > 0:
            self._progress.setValue(int(time_pos / total * 1000))
            # Atualizar ponteira + sparks se visiveis
            if hasattr(self, '_progress_dot') and self._progress_dot and self._progress_dot.isVisible():
                x_pos = int((time_pos / total) * self._progress.width())
                self._progress_dot.move(max(0, x_pos - 15), 3)
        # Atualizar playhead na timeline
        self.timeline.playhead_pos = time_pos
        self.timeline._scene.update_playhead(time_pos, self.timeline.zoom)
        # Info
        m = int(time_pos) // 60
        s = time_pos % 60
        tm = int(total) // 60
        ts = total % 60
        self._info.setText(f"{m}:{s:04.1f} / {tm}:{ts:04.1f}")

    def _on_ended(self):
        """Playback terminou."""
        self.set_has_media(False)
        self._is_playing = False
        self._paused_at = None
        self._progress.setValue(0)
        if hasattr(self, '_progress_dot') and self._progress_dot:
            self._progress_dot.hide()
        self._progress_container.hide()
        self._show_play_button()
        self._info.setText("")
        # Reset playhead na timeline
        self.timeline.playhead_pos = 0
        self.timeline._scene.update_playhead(0, self.timeline.zoom)

    def _on_playhead_moved(self, time_pos):
        """Timeline moveu playhead (scrub manual)."""
        if self.player.is_playing:
            # Seek sem parar o playback
            self.player.seek_to_time(time_pos)
        else:
            # Scrub: mostrar frame na posição
            self._scrub_frame(time_pos)

    def _scrub_frame(self, time_pos):
        """Mostra frame na posição sem tocar."""
        try:
            import cv2
        except ImportError:
            return

        clips = sorted(self.project.clips, key=lambda c: c.position)
        if not clips:
            return

        # Encontrar clip na posição
        current = 0.0
        for clip in clips:
            if current + clip.duration > time_pos:
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    cap = cv2.VideoCapture(str(clip.video_path))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 16
                    local_time = time_pos - current
                    target_frame = int(local_time * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target_frame))
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        # Aplicar FX
                        fx_items = self.project.get_track_items("fx")
                        if fx_items:
                            from makevid.core.fx_processor import apply_fx_to_frame
                            frame_rgb = frame[:, :, ::-1]
                            total_dur = self.project.total_duration()
                            frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, time_pos, total_dur)
                            frame = frame_rgb[:, :, ::-1]
                        self._on_frame(frame)
                        self._info.setText(f"{time_pos:.1f}s | Clip {clip.position+1}")
                return
            current += clip.duration


    # ============================================================
    # BROWSER (abre dentro do preview substituindo o display)
    # ============================================================

    def _hide_display(self):
        if self.player.is_playing:
            self.player.stop()
        self._display.hide()
        self._progress_container.hide()
        self._info.hide()
        if hasattr(self, '_browser') and self._browser:
            self._browser.deleteLater()
            self._browser = None

    def _show_browser(self, title, accent, files, build_card_fn, import_fn, clean_fn):
        """Base para show_video_browser e show_audio_browser."""
        from PySide6.QtWidgets import QScrollArea, QFrame
        self._hide_display()

        self._browser = QFrame(self)
        self._browser.setObjectName("browserFrame")
        self._browser.setStyleSheet(
            f"QFrame#browserFrame {{ background: {C['panel']}; border: 1px solid {accent}; border-radius: 4px; }}")
        bl = QVBoxLayout(self._browser)
        bl.setContentsMargins(1, 1, 1, 1)
        bl.setSpacing(0)

        hdr = QFrame()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(f"background: {C['card']}; border: none;")
        from PySide6.QtWidgets import QHBoxLayout as HL
        hl = HL(hdr)
        hl.setContentsMargins(12, 0, 8, 0)
        hl.setSpacing(6)
        lbl = QLabel(f"{title}  #{len(files)}")
        lbl.setStyleSheet(f"color: {accent}; font-size: 11pt; font-weight: bold; border: none;")
        hl.addWidget(lbl)
        hl.addStretch()
        btn_imp = QPushButton("+ Importar")
        btn_imp.setFixedHeight(22)
        btn_imp.setStyleSheet(
            f"background: {C['card']}; color: {accent}; font-size: 8pt; font-weight: bold; "
            f"border: 1px solid {accent}; border-radius: 3px; padding: 0 8px;")
        btn_imp.clicked.connect(import_fn)
        hl.addWidget(btn_imp)
        btn_clean = QPushButton("Limpar Inutilizados")
        btn_clean.setFixedHeight(22)
        btn_clean.setStyleSheet(
            "background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; "
            "border: 1px solid #ff4444; border-radius: 3px; padding: 0 8px;")
        btn_clean.clicked.connect(clean_fn)
        hl.addWidget(btn_clean)
        btn_x = QPushButton("\u2715")
        btn_x.setFixedSize(28, 22)
        btn_x.setObjectName("closeBtn")
        btn_x.clicked.connect(self._close_browser)
        hl.addWidget(btn_x)
        bl.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C['panel']}; border: none; }}")
        sc = QWidget()
        sc.setStyleSheet(f"background: {C['panel']};")
        self._browser_layout = QVBoxLayout(sc)
        self._browser_layout.setContentsMargins(8, 8, 8, 8)
        self._browser_layout.setSpacing(6)
        scroll.setWidget(sc)
        bl.addWidget(scroll)

        if not files:
            empty = QLabel("Nenhum arquivo encontrado.")
            empty.setStyleSheet(f"color: {C['text3']}; font-size: 10pt; padding: 12px;")
            self._browser_layout.addWidget(empty)
        else:
            for f in files:
                build_card_fn(f)
        self._browser_layout.addStretch()
        self.layout().insertWidget(0, self._browser, stretch=1)
        self._browser.show()

    def show_video_browser(self):
        from makevid.config import OUTPUTS_DIR
        proj_dir = OUTPUTS_DIR / self.project.id
        files = sorted(proj_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True) if proj_dir.exists() else []
        self._show_browser(
            title="MEUS VIDEOS", accent=C['gold'], files=files,
            build_card_fn=self._build_browser_video_card,
            import_fn=self._browser_import_video,
            clean_fn=self._browser_clean_videos,
        )

    def show_audio_browser(self):
        from makevid.config import AUDIO_DIR
        proj_audio = AUDIO_DIR / self.project.id
        files = sorted(
            [f for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac") for f in proj_audio.rglob(ext)],
            key=lambda p: p.stat().st_mtime, reverse=True) if proj_audio.exists() else []
        self._show_browser(
            title="MEUS AUDIOS", accent=C['cyan'], files=files,
            build_card_fn=self._build_browser_audio_card,
            import_fn=self._browser_import_audio,
            clean_fn=self._browser_clean_audios,
        )

    def show_projects_panel(self):
        """Mostra painel de projetos no lugar do display."""
        if self.player.is_playing:
            self.player.stop()

        if self._projects_panel is not None:
            self._projects_panel.hide()
            self._projects_panel.setParent(None)
            self._projects_panel.deleteLater()
            self._projects_panel = None

        from makevid.qt.panels.projects_panel import ProjectsPanel
        self._projects_panel = ProjectsPanel(self.project, parent=self)
        self._projects_panel.closed.connect(self._close_projects_panel)
        self._projects_panel.project_opened.connect(self.window()._on_project_opened)

        # Montar tudo antes de qualquer repaint
        self.setUpdatesEnabled(False)
        self.layout().addWidget(self._projects_panel, stretch=1)
        self._display.hide()
        self._progress_container.hide()
        self._info.hide()
        self._projects_panel.show()
        self.setUpdatesEnabled(True)

    def _close_projects_panel(self):
        if self._projects_panel is not None:
            self._projects_panel.deleteLater()
            self._projects_panel = None
        self._display.show()
        self._info.show()
        self._show_play_button()

    def _on_project_changed(self, proj):
        self.project = proj
        self.player.set_project(proj)

    def _build_browser_video_card(self, vpath):
        import time as _time
        from PySide6.QtWidgets import QFrame, QPushButton, QLineEdit
        from PySide6.QtWidgets import QHBoxLayout as HL, QVBoxLayout as VL

        _path = [vpath]

        card = QFrame()
        card.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = HL(card)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.setSpacing(8)

        # Thumbnail
        try:
            import cv2
            cap = cv2.VideoCapture(str(vpath))
            ret, frame = cap.read()
            cap.release()
            if ret:
                rgb = frame[:, :, ::-1].copy()
                h, w = rgb.shape[:2]
                img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
                pm = QPixmap.fromImage(img).scaled(120, 68, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                if pm.width() > 120 or pm.height() > 68:
                    pm = pm.copy((pm.width() - 120) // 2, (pm.height() - 68) // 2, 120, 68)
                th = QLabel()
                th.setPixmap(pm)
                th.setFixedSize(120, 68)
                cl.addWidget(th)
        except Exception:
            pass

        info = VL()
        info.setSpacing(2)

        # Nome + campo de renomear
        name_row = HL()
        name_row.setSpacing(4)
        name_lbl = QLabel(vpath.stem[:30])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none;")
        name_edit = QLineEdit(vpath.stem)
        name_edit.setFixedHeight(20)
        name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 9pt; font-weight: bold; "
            f"border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 4px;")
        name_edit.hide()
        name_row.addWidget(name_lbl)
        name_row.addWidget(name_edit)
        name_row.addStretch()
        info.addLayout(name_row)

        sz = vpath.stat().st_size / 1e6
        mt = _time.strftime("%d/%m %H:%M", _time.localtime(vpath.stat().st_mtime))
        meta = QLabel(f"{sz:.1f} MB | {mt}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 9pt; border: none;")
        info.addWidget(meta)

        btns = HL()
        btns.setSpacing(4)

        # Botao renomear
        br = QPushButton("Renomear")
        br.setFixedHeight(22)
        br.setStyleSheet(
            f"background: {C['card']}; color: {C['warning']}; border: 1px solid {C['warning']}; "
            f"border-radius: 3px; font-size: 8pt; font-weight: bold; padding: 0 6px;")

        def _toggle_rename():
            if name_edit.isHidden():
                name_edit.setText(_path[0].stem)
                name_lbl.hide(); name_edit.show()
                name_edit.setFocus(); name_edit.selectAll()
                br.setText("OK")
            else:
                _confirm_rename()

        def _confirm_rename():
            new_name = name_edit.text().strip()
            if new_name and new_name != _path[0].stem:
                new_p = _path[0].with_name(new_name + _path[0].suffix)
                try:
                    _path[0].rename(new_p)
                    for c in self.project.clips:
                        if c.video_path == str(_path[0]):
                            c.video_path = str(new_p)
                    from makevid.config import PROJECTS_DIR
                    self.project.save(PROJECTS_DIR)
                    _path[0] = new_p
                    name_lbl.setText(new_name[:30])
                except Exception:
                    pass
            name_edit.hide(); name_lbl.show(); br.setText("Renomear")

        br.clicked.connect(_toggle_rename)
        name_edit.returnPressed.connect(_confirm_rename)
        btns.addWidget(br)

        ba = QPushButton("+ Timeline")
        ba.setFixedHeight(22)
        ba.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 6px;")
        ba.clicked.connect(lambda ck=False: self._add_video_to_tl(_path[0]))
        btns.addWidget(ba)

        bd = QPushButton("Deletar")
        bd.setFixedHeight(22)
        bd.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 6px;")
        bd.clicked.connect(lambda ck=False, c=card: [_path[0].unlink(missing_ok=True), c.deleteLater()])
        btns.addWidget(bd)
        btns.addStretch()
        info.addLayout(btns)
        cl.addLayout(info)
        self._browser_layout.addWidget(card)

    def _build_browser_audio_card(self, apath):
        import time as _time
        import numpy as np
        from PySide6.QtWidgets import QFrame, QPushButton, QLineEdit
        from PySide6.QtWidgets import QHBoxLayout as HL, QVBoxLayout as VL
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtGui import QPainter as _QP, QColor as _QC, QPen as _QPen

        _path = [apath]  # mutavel para rename

        card = QFrame()
        card.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = HL(card)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.setSpacing(6)
        info = VL()
        info.setSpacing(2)

        # Nome + campo de renomear
        name_row = HL()
        name_row.setSpacing(4)
        name_lbl = QLabel(apath.stem[:28])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none;")
        name_edit = QLineEdit(apath.stem)
        name_edit.setFixedHeight(20)
        name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 9pt; font-weight: bold; "
            f"border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 4px;")
        name_edit.hide()
        name_row.addWidget(name_lbl)
        name_row.addWidget(name_edit)
        name_row.addStretch()
        info.addLayout(name_row)

        dur = 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            dur = get_audio_duration(str(apath)) or 0
        except Exception:
            pass

        sz = apath.stat().st_size / 1024
        mt = _time.strftime("%d/%m %H:%M", _time.localtime(apath.stat().st_mtime))
        meta = QLabel(f"{dur:.1f}s | {sz:.0f}KB | {mt}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        info.addWidget(meta)

        # Envelope real do arquivo
        N_BARS = 200
        _wdata = np.zeros(N_BARS, dtype=np.float32)
        try:
            import soundfile as sf
            samples, _ = sf.read(str(apath), dtype='float32')
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            chunk = max(1, len(samples) // N_BARS)
            env = np.array([float(np.abs(samples[i:i+chunk]).max())
                            for i in range(0, len(samples), chunk)])[:N_BARS]
            peak = max(float(env.max()), 1e-6)
            _wdata[:len(env)] = env / peak
        except Exception:
            pass

        class _Wave(QWidget):
            def __init__(self_, data):
                super().__init__()
                self_.setFixedHeight(48)
                self_._data = data
                self_._prog = 0.0
            def set_progress(self_, v):
                self_._prog = max(0.0, min(1.0, v))
                self_.update()
            def paintEvent(self_, ev):
                p = _QP(self_)
                p.setRenderHint(_QP.Antialiasing, False)
                w, h = self_.width(), self_.height()
                p.fillRect(0, 0, w, h, _QC(C['dark']))
                mid = h / 2
                n = len(self_._data)
                bar_w = max(1.0, (w - 4) / n)
                cx = w * self_._prog
                peak = max(float(np.max(self_._data)), 0.01)
                if peak < 0.001:
                    p.setPen(_QPen(_QC(C['text3']), 1, Qt.DashLine))
                    p.drawLine(4, int(mid), w - 4, int(mid))
                    p.end()
                    return
                color_played = _QC(C['accent']); color_played.setAlpha(210)
                color_idle = _QC(C['text3']); color_idle.setAlpha(160)
                p.setPen(Qt.NoPen)
                for i, amp in enumerate(self_._data):
                    x = int(4 + i * bar_w)
                    bh = max(1, int((amp / peak) * (mid - 4)))
                    p.setBrush(color_played if (x <= cx) else color_idle)
                    p.drawRect(x, int(mid - bh), max(1, int(bar_w) - 1), bh * 2)
                if self_._prog > 0:
                    p.setPen(_QPen(_QC("white"), 1))
                    p.drawLine(int(cx), 0, int(cx), h)
                p.end()

        wave = _Wave(_wdata)
        info.addWidget(wave)

        btns = HL()
        btns.setSpacing(4)
        btns.setContentsMargins(0, 2, 0, 0)
        _st = {'player': None, 'ao': None, 'timer': None}

        bp = QPushButton("▶")
        bp.setFixedSize(30, 24)
        bp.setStyleSheet(
            f"background: {C['card']}; color: {C['cyan']}; border: 1px solid {C['cyan']}; "
            f"border-radius: 3px; font-size: 12pt; font-weight: bold; "
            f"font-family: 'Segoe UI Symbol', 'Arial Unicode MS', sans-serif; padding: 0;")

        def _toggle(ck=False, _bp=bp, _wave=wave, _dur=dur):
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            if _st['player'] is None:
                pl = QMediaPlayer(card); ao = QAudioOutput(card)
                pl.setAudioOutput(ao); ao.setVolume(1.0)
                t = QTimer(card); t.setInterval(80)
                _st['player'] = pl; _st['ao'] = ao; _st['timer'] = t
                def _state(s, __bp=_bp, __wave=_wave, __t=t):
                    if s == QMediaPlayer.PlayingState:
                        __bp.setText("⏸"); __t.start()
                    else:
                        __bp.setText("▶"); __t.stop()
                        if s == QMediaPlayer.StoppedState:
                            __wave.set_progress(0.0)
                pl.playbackStateChanged.connect(_state)
                t.timeout.connect(
                    lambda __pl=pl, __w=_wave, __d=_dur:
                    __w.set_progress(__pl.position() / (__d * 1000) if __d > 0 else 0))
            pl = _st['player']
            if pl.playbackState() == QMediaPlayer.PlayingState:
                pl.pause()
            else:
                if pl.playbackState() != QMediaPlayer.PausedState:
                    pl.setSource(QUrl.fromLocalFile(str(_path[0])))
                pl.play()

        bp.clicked.connect(_toggle)
        btns.addWidget(bp)

        # Botao renomear
        br = QPushButton("Renomear")
        br.setFixedHeight(22)
        br.setStyleSheet(
            f"background: {C['card']}; color: {C['warning']}; border: 1px solid {C['warning']}; "
            f"border-radius: 3px; font-size: 8pt; font-weight: bold; padding: 0 6px;")

        def _toggle_rename():
            if name_edit.isHidden():
                name_edit.setText(_path[0].stem)
                name_lbl.hide(); name_edit.show()
                name_edit.setFocus(); name_edit.selectAll()
                br.setText("OK")
            else:
                _confirm_rename()

        def _confirm_rename():
            new_name = name_edit.text().strip()
            if new_name and new_name != _path[0].stem:
                new_p = _path[0].with_name(new_name + _path[0].suffix)
                try:
                    _path[0].rename(new_p)
                    _path[0] = new_p
                    name_lbl.setText(new_name[:28])
                except Exception:
                    pass
            name_edit.hide(); name_lbl.show(); br.setText("Renomear")

        br.clicked.connect(_toggle_rename)
        name_edit.returnPressed.connect(_confirm_rename)
        btns.addWidget(br)

        ba = QPushButton("+ Timeline")
        ba.setFixedHeight(22)
        ba.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 8px;")
        ba.clicked.connect(lambda ck=False, d=dur: self._add_audio_to_tl(_path[0], d))
        btns.addWidget(ba)

        def _delete_audio(ck=False, c=card):
            pl = _st.get('player')
            if pl:
                pl.stop()
                pl.setSource(QUrl())
            t = _st.get('timer')
            if t:
                t.stop()
            _path[0].unlink(missing_ok=True)
            c.deleteLater()

        bd = QPushButton("Deletar")
        bd.setFixedHeight(22)
        bd.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 8px;")
        bd.clicked.connect(_delete_audio)
        btns.addWidget(bd)
        btns.addStretch()
        info.addLayout(btns)
        cl.addLayout(info)
        self._browser_layout.addWidget(card)

    def _close_browser(self):
        if hasattr(self, '_browser') and self._browser:
            self._browser.deleteLater()
            self._browser = None
        self._display.show()
        self._progress_container.show()
        self._info.show()
        self._show_play_button()

    def _add_video_to_tl(self, vpath):
        from makevid.core.timeline import get_video_duration
        from makevid.config import PROJECTS_DIR
        dur = get_video_duration(str(vpath)) or 5.0
        clip = self.project.add_clip(prompt=vpath.stem, position=len(self.project.clips))
        clip.video_path = str(vpath)
        clip.duration = dur
        clip.status = "done"
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

    def _add_audio_to_tl(self, path, dur):
        from makevid.config import PROJECTS_DIR
        existing = self.project.get_track_items("audio")
        start = max((i.start_time + i.duration for i in existing), default=self.timeline.playhead_pos)
        self.project.add_track_item(name=path.stem[:20], track="audio", start_time=start, duration=dur or 5.0, file_path=str(path))
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

    def _play_audio_file(self, path):
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
            data, sr = sf.read(str(path), dtype="float32")
            sd.stop()
            sd.play(np.ascontiguousarray(data), samplerate=sr)
        except Exception:
            pass

    def _rename_video(self, vpath, new_name):
        from makevid.config import PROJECTS_DIR
        new_name = new_name.strip()
        if not new_name or new_name == vpath.stem:
            return
        new_path = vpath.parent / f"{new_name}{vpath.suffix}"
        if not new_path.exists():
            vpath.rename(new_path)
            for clip in self.project.clips:
                if clip.video_path == str(vpath):
                    clip.video_path = str(new_path)
            self.project.save(PROJECTS_DIR)

    def _browser_import_video(self):
        from PySide6.QtWidgets import QFileDialog
        from makevid.config import OUTPUTS_DIR
        import shutil
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Video", "", "Video (*.mp4 *.avi *.mov *.mkv)")
        for p in paths:
            src = Path(p)
            dest = OUTPUTS_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self._close_browser()
        self.show_video_browser()

    def _browser_clean_videos(self):
        from makevid.config import OUTPUTS_DIR
        used = {str(Path(c.video_path).resolve()) for c in self.project.clips if c.video_path}
        out_dir = OUTPUTS_DIR / self.project.id
        if out_dir.exists():
            for f in out_dir.rglob("*.mp4"):
                if str(f.resolve()) not in used:
                    f.unlink(missing_ok=True)
        self._close_browser()
        self.show_video_browser()

    def _browser_import_audio(self):
        from PySide6.QtWidgets import QFileDialog
        from makevid.config import AUDIO_DIR
        import shutil
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Audio", "", "Audio (*.wav *.mp3 *.ogg *.flac)")
        for p in paths:
            src = Path(p)
            dest = AUDIO_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self._close_browser()
        self.show_audio_browser()

    def _browser_clean_audios(self):
        from makevid.config import AUDIO_DIR
        from PySide6.QtCore import QUrl
        if hasattr(self, '_browser') and self._browser:
            from PySide6.QtMultimedia import QMediaPlayer
            for pl in self._browser.findChildren(QMediaPlayer):
                pl.stop()
                pl.setSource(QUrl())
        used = {str(Path(i.file_path).resolve()) for i in self.project.track_items if i.file_path}
        proj_audio = AUDIO_DIR / self.project.id
        if proj_audio.exists():
            for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac"):
                for f in proj_audio.rglob(ext):
                    if str(f.resolve()) not in used:
                        f.unlink(missing_ok=True)
        self._close_browser()
        self.show_audio_browser()

    def show_clip_properties(self, clip):
        """Mostra painel lateral de propriedades sobre o display."""
        self._hide_clip_properties()
        self._current_clip = clip
        from PySide6.QtWidgets import (
            QPushButton, QGridLayout, QScrollArea, QLineEdit, QTextEdit,
            QVBoxLayout as VL, QHBoxLayout as HL
        )
        from PySide6.QtCore import Qt as QtC, QRectF
        from PySide6.QtGui import QPainter, QPainterPath, QLinearGradient, QBrush, QPen
        from pathlib import Path as P

        class _GlassProps(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setAttribute(Qt.WA_TranslucentBackground)
            def paintEvent(self, ev):
                from makevid.qt.theme import C as _C
                p = QPainter(self)
                p.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 14, 14)
                grad = QLinearGradient(0, 0, 0, self.height())
                base = QColor(_C["glass"])
                top = QColor(base)
                top.setRed(min(255, base.red() + 14))
                top.setGreen(min(255, base.green() + 12))
                top.setBlue(min(255, base.blue() + 18))
                top.setAlpha(180); base.setAlpha(155)
                grad.setColorAt(0.0, top); grad.setColorAt(1.0, base)
                p.fillPath(path, QBrush(grad))
                hl = QPainterPath()
                hl.addRoundedRect(QRectF(8, 1, self.width() - 16, 18), 8, 8)
                hg = QLinearGradient(0, 0, 0, 18)
                hg.setColorAt(0.0, QColor(255, 255, 255, 12))
                hg.setColorAt(1.0, QColor(255, 255, 255, 0))
                p.setPen(Qt.NoPen); p.fillPath(hl, QBrush(hg))
                bc = QColor(_C["glass_border"]); bc.setAlpha(55)
                p.setPen(QPen(bc, 1.0)); p.drawPath(path); p.end()

        self._props_panel = _GlassProps(self._display)
        self._props_panel.setFixedWidth(230)
        pl = VL(self._props_panel)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.setSpacing(4)

        # Header: apenas X
        hdr = HL()
        hdr.addStretch()
        btn_x = QPushButton("\u2715")
        btn_x.setFixedSize(22, 22)
        btn_x.setObjectName("closeBtn")
        btn_x.clicked.connect(self._hide_clip_properties)
        hdr.addWidget(btn_x)
        pl.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtC.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")
        sc = QWidget(); sc.setStyleSheet("background: transparent;")
        sl = VL(sc); sl.setContentsMargins(0, 4, 0, 4); sl.setSpacing(4)

        sl.addWidget(self._prop_lbl("DESCRICAO"))
        self._props_desc = QTextEdit()
        self._props_desc.setPlainText(clip.prompt or "")
        self._props_desc.setFixedHeight(56)
        self._props_desc.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['glass_border']}; "
            f"border-radius: 6px; padding: 3px; font-size: 9pt;")
        self._props_desc.textChanged.connect(self._save_clip_desc)
        sl.addWidget(self._props_desc)
        sl.addWidget(self._prop_sep())

        def prop_row(label, value, color=C['text']):
            r = HL()
            la = QLabel(label); la.setFixedWidth(60)
            la.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; font-weight: bold; border: none; background: transparent;")
            r.addWidget(la)
            va = QLabel(str(value))
            va.setStyleSheet(f"color: {color}; font-family: Consolas; font-size: 10pt; font-weight: bold; border: none; background: transparent;")
            r.addWidget(va); r.addStretch(); sl.addLayout(r)

        prop_row("Duracao", f"{clip.duration:.1f}s", C['accent'])
        prop_row("Status", clip.status.upper(), C['success'] if clip.status == 'done' else C['primary'])
        prop_row("Seed", clip.seed or "random")
        if clip.video_path:
            vp = P(clip.video_path)
            if vp.exists():
                prop_row("Tamanho", f"{vp.stat().st_size / 1e6:.1f} MB")
        sl.addWidget(self._prop_sep())

        sl.addWidget(self._prop_lbl("TITULO"))
        self._props_title = QLineEdit(clip.prompt or "")
        self._props_title.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['glass_border']}; "
            f"border-radius: 6px; padding: 3px; font-size: 9pt; font-weight: bold;")
        self._props_title.returnPressed.connect(self._save_clip_title)
        sl.addWidget(self._props_title)
        sl.addWidget(self._prop_sep())

        sl.addWidget(self._prop_lbl("ACOES"))
        gl = QGridLayout(); gl.setContentsMargins(0, 2, 0, 0); gl.setSpacing(3)

        def bstyle(c2):
            return (f"QPushButton {{ background: {C['card']}; color: {c2}; font-weight: bold; font-size: 8pt; "
                    f"border: 1px solid {c2}; border-radius: 6px; padding: 4px; }}"
                    f"QPushButton:hover {{ background: {C['card_hover']}; }}")

        b1 = QPushButton("\u27f3 REGERAR")
        b1.setStyleSheet(f"QPushButton {{ background: {C['primary']}; color: {C['dark_text']}; font-weight: bold; font-size: 8pt; border-radius: 6px; padding: 4px; }}QPushButton:hover {{ background: {C['secondary']}; }}")
        b1.clicked.connect(lambda: self._clip_action("regenerate")); gl.addWidget(b1, 0, 0)

        b2 = QPushButton("\u29c9 DUPLICAR"); b2.setStyleSheet(bstyle(C['accent']))
        b2.clicked.connect(lambda: self._clip_action("duplicate")); gl.addWidget(b2, 0, 1)

        b3 = QPushButton("\u2702 DIVIDIR"); b3.setStyleSheet(bstyle(C['purple']))
        b3.clicked.connect(lambda: self._clip_action("split")); gl.addWidget(b3, 1, 0)

        b4 = QPushButton("\u2715 REMOVER")
        b4.setStyleSheet(f"QPushButton {{ background: {C['danger_bg']}; color: {C['danger']}; font-weight: bold; font-size: 8pt; border: 1px solid {C['danger']}; border-radius: 6px; padding: 4px; }}QPushButton:hover {{ background: {C['danger']}; color: {C['dark_text']}; }}")
        b4.clicked.connect(lambda: self._clip_action("delete")); gl.addWidget(b4, 1, 1)

        b5 = QPushButton("\u2b06 REFINAR"); b5.setStyleSheet(bstyle(C['success']))
        b5.clicked.connect(lambda: self._clip_action("upscale")); gl.addWidget(b5, 2, 0)

        b6 = QPushButton("\U0001f464 FACE"); b6.setStyleSheet(bstyle(C['warning']))
        b6.clicked.connect(lambda: self._clip_action("faceswap")); gl.addWidget(b6, 2, 1)

        b7 = QPushButton("\u270f EDITAR"); b7.setStyleSheet(bstyle(C['info']))
        b7.clicked.connect(lambda: self._clip_action("inpaint")); gl.addWidget(b7, 3, 0, 1, 2)

        sl.addLayout(gl); sl.addStretch()
        scroll.setWidget(sc); pl.addWidget(scroll)

        panel_h = int(self._display.height() * 0.95)
        self._props_panel.setFixedHeight(max(200, panel_h))
        self._props_panel.move(max(0, self._display.width() - 235), 5)
        self._props_panel.show()
    def _prop_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        return l

    def _prop_sep(self):
        from PySide6.QtWidgets import QFrame
        s = QFrame()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background: {C['border']}; border: none;")
        return s

    def _save_clip_title(self):
        clip = getattr(self, '_current_clip', None)
        if clip and hasattr(self, '_props_title'):
            new = self._props_title.text().strip()
            if new and new != clip.prompt:
                clip.prompt = new
                from makevid.config import PROJECTS_DIR
                self.project.save(PROJECTS_DIR)
                self.timeline.redraw()

    def _save_clip_desc(self):
        clip = getattr(self, '_current_clip', None)
        if clip and hasattr(self, '_props_desc'):
            new = self._props_desc.toPlainText().strip()
            if new != clip.prompt:
                clip.prompt = new
                from makevid.config import PROJECTS_DIR
                self.project.save(PROJECTS_DIR)

    def _hide_clip_properties(self):
        if hasattr(self, '_props_panel') and self._props_panel:
            self._props_panel.deleteLater()
            self._props_panel = None

    def _clip_action(self, action):
        clip = getattr(self, '_current_clip', None)
        if not clip:
            return
        app = self.window()
        app._selected_clip = clip
        if action == "regenerate":
            app._regenerate_clip()
        elif action == "duplicate":
            app._duplicate_clip()
        elif action == "split":
            app._split_clip_at_playhead()
        elif action == "delete":
            from makevid.config import PROJECTS_DIR
            app.project.remove_clip(clip.id)
            app.project.save(PROJECTS_DIR)
            app.timeline.redraw()
        elif action == "upscale":
            pass  # TODO: integrar UpscaleService
        elif action == "faceswap":
            pass  # TODO: integrar FaceSwapService
        elif action == "inpaint":
            app._show_inpaint()
        self._hide_clip_properties()
