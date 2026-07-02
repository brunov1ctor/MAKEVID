"""PreviewWidget — display de vídeo com playback."""

import numpy as np
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QPixmap, QCursor, QPainter, QColor, QPolygonF

from makevid.qt.theme import C
from makevid.qt.preview.player import TimelinePlayerQt
from makevid.qt.preview.clip_properties import ClipPropertiesMixin
from makevid.qt.preview.media_browser import MediaBrowserMixin
from makevid.qt.preview.projects_view import ProjectsViewMixin


class _PlayOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self._pressed = False
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(56, 56)

    def enterEvent(self, e):
        self._hover = True; self.update(); super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False; self.update(); super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True; self.update()
        display = self.parent()
        preview = display.parent() if display else None
        if preview and hasattr(preview, "_on_display_click"):
            preview._on_display_click(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        ts = 18.0 if self._pressed else 22.0
        alpha = 180 if self._pressed else (255 if self._hover else 210)
        tx = cx - ts * 0.4
        poly = QPolygonF([QPointF(tx, cy - ts * 0.6), QPointF(tx, cy + ts * 0.6), QPointF(tx + ts, cy)])
        p.setBrush(QColor(255, 255, 255, alpha)); p.setPen(Qt.NoPen)
        p.drawPolygon(poly); p.end()


class PreviewWidget(ClipPropertiesMixin, MediaBrowserMixin, ProjectsViewMixin, QWidget):
    """Display de vídeo com controles de playback."""

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

        self._display = QLabel()
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setMinimumSize(200, 80)
        self._display.setStyleSheet(
            f"background: {C['dark']}; border: 1px solid {C['glass_border']}; border-radius: 16px;"
        )
        self._display.setCursor(QCursor(Qt.PointingHandCursor))
        self._display.mousePressEvent = self._on_display_click
        layout.addWidget(self._display, stretch=1)

        self._play_overlay = None

        self._progress_container = QWidget()
        self._progress_container.setFixedHeight(36)
        self._progress_container.setStyleSheet("background: transparent;")
        from PySide6.QtWidgets import QVBoxLayout as VL
        pc_layout = VL(self._progress_container)
        pc_layout.setContentsMargins(0, 14, 0, 14); pc_layout.setSpacing(0)
        self._progress = QProgressBar()
        self._progress.setFixedHeight(4); self._progress.setRange(0, 1000)
        self._progress.setValue(0); self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 2px; }"
        )
        self._progress.setCursor(QCursor(Qt.PointingHandCursor))
        self._progress.setMouseTracking(True)
        self._progress_container.enterEvent = self._on_progress_enter
        self._progress_container.leaveEvent = self._on_progress_leave
        self._progress.mousePressEvent = self._on_progress_click
        pc_layout.addWidget(self._progress)
        self._progress_container.hide()
        layout.addWidget(self._progress_container)

        self._info = QLabel()
        self._info.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        layout.addWidget(self._info)

        self.player = TimelinePlayerQt(self)
        self.player.set_project(self.project)

        self._projects_panel = None
        self._browser = None
        self._props_panel = None

        self._show_play_button()

    def _connect_signals(self):
        self.player.frame_ready.connect(self._on_frame)
        self.player.playback_ended.connect(self._on_ended)
        self.player.time_updated.connect(self._on_time_update)
        self.timeline.playhead_moved.connect(self._on_playhead_moved)

    def set_has_media(self, value: bool):
        glow = getattr(self, "_glow_layer", None)
        if glow:
            glow.set_has_media(value)

    # ── display ───────────────────────────────────────────────────────────────

    def _on_frame(self, frame_bgr):
        h, w, _ = frame_bgr.shape
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img).scaled(self._display.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self._display.setPixmap(pixmap)
        self.set_has_media(True)

    def _show_play_button(self, clear_frame=True):
        if clear_frame:
            self._display.setPixmap(QPixmap()); self._display.setText("")
            self._display.setStyleSheet(
                f"background: {C['dark']}; border: 1px solid {C['glass_border']}; border-radius: 16px;"
            )
        if not self._play_overlay:
            self._play_overlay = _PlayOverlay(self._display)
        self._center_overlay()
        self._play_overlay.show()

    def _center_overlay(self):
        if self._play_overlay:
            s = self._play_overlay.width()
            self._play_overlay.move(
                (self._display.width() - s) // 2,
                (self._display.height() - s) // 2,
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._play_overlay and self._play_overlay.isVisible():
            self._center_overlay()
        if getattr(self, "_props_panel", None) and self._props_panel.isVisible():
            panel_h = int(self._display.height() * 0.95)
            self._props_panel.setFixedHeight(max(200, panel_h))
            self._props_panel.move(max(0, self._display.width() - 235), 5)

    # ── controles ─────────────────────────────────────────────────────────────

    def _on_display_click(self, event):
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
        pos = getattr(self, "_paused_at", self.timeline.playhead_pos)
        self.player.play_from(pos, self.timeline.playback_speed)
        self._paused_at = None
        self._is_playing = True
        self._display.setText("")
        self._display.setStyleSheet(
            f"background: {C['dark']}; border: 1px solid {C['glass_border']}; border-radius: 16px;"
        )
        if self._play_overlay:
            self._play_overlay.hide()
        self._progress_container.show()

    def _on_progress_click(self, event):
        w = self._progress.width()
        if w <= 0:
            return
        ratio = max(0, min(1.0, event.position().x() / w))
        target = ratio * self.project.total_duration()
        self.player.seek_to_time(target)
        self.timeline.set_playhead(target)

    def _on_progress_enter(self, event):
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(
            "QProgressBar { background: #1a1a2a; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 3px; }"
        )
        if not getattr(self, "_progress_dot", None):
            self._progress_dot = QLabel(self._progress_container)
            self._progress_dot.setFixedSize(30, 30)
            self._progress_dot.setText("\u2734")
            self._progress_dot.setAlignment(Qt.AlignCenter)
            self._progress_dot.setStyleSheet(
                "QLabel { background: transparent; color: #ffffff; font-size: 18pt; border: none; }"
            )
        val = self._progress.value()
        x_pos = int((val / (self._progress.maximum() or 1)) * self._progress.width())
        self._progress_dot.move(max(0, x_pos - 15), 3)
        self._progress_dot.show()

    def _on_progress_leave(self, event):
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 2px; }"
        )
        if getattr(self, "_progress_dot", None):
            self._progress_dot.hide()

    # ── signals ───────────────────────────────────────────────────────────────

    def _on_time_update(self, time_pos):
        total = self.project.total_duration()
        if total > 0:
            self._progress.setValue(int(time_pos / total * 1000))
            if getattr(self, "_progress_dot", None) and self._progress_dot.isVisible():
                x_pos = int((time_pos / total) * self._progress.width())
                self._progress_dot.move(max(0, x_pos - 15), 3)
        self.timeline.playhead_pos = time_pos
        self.timeline._scene.update_playhead(time_pos, self.timeline.zoom)
        m, s = int(time_pos) // 60, time_pos % 60
        tm, ts = int(total) // 60, total % 60
        self._info.setText(f"{m}:{s:04.1f} / {tm}:{ts:04.1f}")

    def _on_ended(self):
        self.set_has_media(False)
        self._is_playing = False
        self._paused_at = None
        self._progress.setValue(0)
        if getattr(self, "_progress_dot", None):
            self._progress_dot.hide()
        self._progress_container.hide()
        self._show_play_button()
        self._info.setText("")
        self.timeline.playhead_pos = 0
        self.timeline._scene.update_playhead(0, self.timeline.zoom)

    def _on_playhead_moved(self, time_pos):
        if self.player.is_playing:
            self.player.seek_to_time(time_pos)
        else:
            self._scrub_frame(time_pos)

    def _scrub_frame(self, time_pos):
        try:
            import cv2
        except ImportError:
            return
        clips = sorted(self.project.clips, key=lambda c: c.position)
        current = 0.0
        for clip in clips:
            if current + clip.duration > time_pos:
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    cap = cv2.VideoCapture(str(clip.video_path))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 16
                    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int((time_pos - current) * fps)))
                    ret, frame = cap.read(); cap.release()
                    if ret:
                        fx_items = self.project.get_track_items("fx")
                        if fx_items:
                            from makevid.core.fx_processor import apply_fx_to_frame
                            frame_rgb = frame[:, :, ::-1]
                            frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, time_pos, self.project.total_duration())
                            frame = frame_rgb[:, :, ::-1]
                        self._on_frame(frame)
                        self._info.setText(f"{time_pos:.1f}s | Clip {clip.position+1}")
                return
            current += clip.duration

    # ── project changed ───────────────────────────────────────────────────────

    def _on_project_changed(self, proj):
        if not self.isVisible():
            return
        self.project = proj
        self.player.set_project(proj)
        if self._projects_panel is not None:
            self._projects_panel.set_active(proj.id)
