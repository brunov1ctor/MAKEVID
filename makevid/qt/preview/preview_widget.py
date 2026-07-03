"""PreviewWidget — display de vídeo com playback."""

import numpy as np
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStackedWidget, QDialog
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import (
    QImage, QPixmap, QCursor, QPainter, QColor, QPolygonF,
    QPainterPath, QPen, QBrush, QLinearGradient, QFont
)

from makevid.qt.theme import C
from makevid.qt.preview.player import TimelinePlayerQt
from makevid.qt.preview.clip_properties import ClipPropertiesMixin
from makevid.qt.preview.media_browser import MediaBrowserMixin
from makevid.qt.preview.projects_view import ProjectsViewMixin


class _FullscreenWindow(QDialog):
    def __init__(self, preview, parent=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self._preview = preview
        self.setStyleSheet("background: #000000;")
        self.showFullScreen()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._lbl = QLabel()
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setStyleSheet("background: #000000;")
        layout.addWidget(self._lbl)

        preview.player.frame_ready.connect(self._on_frame)

    def _on_frame(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        rgb = frame_bgr[:, :, ::-1].copy()
        img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        self._lbl.setPixmap(QPixmap.fromImage(img).scaled(
            self._lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mouseDoubleClickEvent(self, e): self._close()
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape: self._close()
        else: super().keyPressEvent(e)

    def _close(self):
        self._preview.player.frame_ready.disconnect(self._on_frame)
        self._preview._fullscreen_win = None
        self.close()


class _VideoDisplay(QLabel):
    """QLabel que pinta o vídeo e todos os controles sobrepostos diretamente."""

    BTN   = 24
    PAD   = 8
    VOL_W = 60
    BAR_H = 4   # altura da barra de progresso
    BAR_PAD = 8  # margem lateral da barra

    def __init__(self, preview, parent=None):
        super().__init__(parent)
        self._pv = preview
        self._hover = False
        self._drag_vol = False
        self._drag_seek = False
        self._fade = 0
        self._last_pixmap = None
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(14)
        self._fade_timer.timeout.connect(self._tick_fade)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(200, 80)
        self.setStyleSheet(
            f"border: none; border-radius: 20px;"
            f"background: {C['dark']};"
        )
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMouseTracking(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_pixmap and not self._last_pixmap.isNull():
            self.setPixmap(self._last_pixmap.scaled(
                self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        pv = self._pv
        if getattr(pv, '_play_overlay', None) and pv._play_overlay.isVisible():
            pv._center_overlay()

    # ── fade ──────────────────────────────────────────────────────────────────

    def _tick_fade(self):
        target = 255 if self._hover else 0
        step = 20
        self._fade += step if self._fade < target else -step
        self._fade = max(0, min(255, self._fade))
        self.update()
        if self._fade == target:
            self._fade_timer.stop()

    # ── rects ─────────────────────────────────────────────────────────────────

    def _bar_rect(self):
        """Barra de progresso vermelha — acima dos botões."""
        bw = self.width() - self.BAR_PAD * 2
        y  = self.height() - self.BTN - self.PAD * 2 - self.BAR_H - 4
        return QRectF(self.BAR_PAD, y, bw, self.BAR_H)

    def _play_rect(self):
        # mantido apenas para compatibilidade de clique no vídeo
        return QRectF(0, 0, 0, 0)

    def _mute_rect(self):
        y = self.height() - self.BTN - self.PAD
        return QRectF(self.PAD, y, self.BTN, self.BTN)

    def _vol_rect(self):
        y = self.height() - self.BTN - self.PAD + self.BTN // 2 - 3
        x = self.PAD + self.BTN + 4
        return QRectF(x, y, self.VOL_W, 6)

    def _time_rect(self):
        """Área do texto de tempo — à direita do volume."""
        y = self.height() - self.BTN - self.PAD
        return QRectF(self.PAD + self.BTN + 4 + self.VOL_W + 8, y, 120, self.BTN)

    def _expand_rect(self):
        y = self.height() - self.BTN - self.PAD
        return QRectF(self.width() - self.BTN - self.PAD, y, self.BTN, self.BTN)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        super().paintEvent(event)
        pv = self._pv
        is_playing = pv.player.is_playing or pv._is_playing
        progress   = getattr(pv, '_progress_value', 0.0)   # 0.0–1.0
        time_text  = getattr(pv, '_time_text', '')

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Clipar ao border-radius para nao vazar fora das bordas arredondadas
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(self.rect()), 20, 20)
        p.setClipPath(clip_path)

        # ── barra de progresso (sempre visível quando tocando) ────────────────
        if is_playing or progress > 0:
            br = self._bar_rect()
            # trilha
            track = QPainterPath()
            track.addRoundedRect(br, 2, 2)
            p.setPen(Qt.NoPen)
            p.fillPath(track, QColor(255, 255, 255, 40))
            # preenchimento vermelho
            if progress > 0:
                fp = QPainterPath()
                fp.addRoundedRect(QRectF(br.x(), br.y(), br.width() * progress, br.height()), 2, 2)
                p.fillPath(fp, QColor("#ff0000"))
            # bolinha na posição atual
            dot_x = br.x() + br.width() * progress
            p.setBrush(QColor("#ff4444"))
            p.drawEllipse(QPointF(dot_x, br.center().y()), 5, 5)

        # ── tempo (sempre visível quando tocando) ─────────────────────────────
        if time_text and (is_playing or progress > 0):
            tr = self._time_rect()
            p.setPen(QColor(255, 255, 255, 200))
            p.setFont(QFont("Consolas", 8, QFont.Bold))
            p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, time_text)

        # ── controles com fade no hover ───────────────────────────────────────
        a = self._fade
        if a > 0:
            # gradiente escuro na base
            grad = QLinearGradient(0, self.height() - 60, 0, self.height())
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(1.0, QColor(0, 0, 0, int(a * 0.70)))
            p.fillRect(self.rect(), QBrush(grad))

            # mute
            self._draw_btn(p, self._mute_rect(), "🔇" if pv._muted else "🔊", a)

            # volume
            vr = self._vol_rect()
            vtrack = QPainterPath()
            vtrack.addRoundedRect(vr, 3, 3)
            p.fillPath(vtrack, QColor(255, 255, 255, int(a * 0.22)))
            fw = vr.width() * pv._master_volume
            if fw > 0:
                vfp = QPainterPath()
                vfp.addRoundedRect(QRectF(vr.x(), vr.y(), fw, vr.height()), 3, 3)
                fc = QColor(C["primary"]); fc.setAlpha(int(a * 0.9))
                p.fillPath(vfp, fc)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(a * 0.9)))
            p.drawEllipse(QPointF(vr.x() + fw, vr.center().y()), 5, 5)

            # expand
            self._draw_btn(p, self._expand_rect(), "⛶", a)

        p.end()

    def _draw_btn(self, p, rect, icon, alpha):
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        bg = QColor(C["glass"]); bg.setAlpha(int(alpha * 0.55))
        p.fillPath(path, bg)
        p.setPen(QColor(255, 255, 255, int(alpha * 0.9)))
        p.setFont(QFont("Segoe UI Symbol", 10))
        p.drawText(rect, Qt.AlignCenter, icon)

    # ── mouse ─────────────────────────────────────────────────────────────────

    def enterEvent(self, e):
        self._hover = True
        self._fade_timer.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._drag_vol = False
        self._drag_seek = False
        self._fade_timer.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        pos = e.position()
        pv  = self._pv

        if self._mute_rect().contains(pos):
            pv._toggle_mute(); self.update(); return
        if self._expand_rect().contains(pos):
            pv._open_fullscreen(); return

        vr = self._vol_rect()
        if QRectF(vr.x() - 4, vr.y() - 8, vr.width() + 8, vr.height() + 16).contains(pos):
            self._drag_vol = True
            self._set_vol_x(pos.x()); return

        br = self._bar_rect()
        if QRectF(br.x(), br.y() - 6, br.width(), br.height() + 12).contains(pos):
            self._drag_seek = True
            self._seek_x(pos.x()); return

        pv._pause() if pv.player.is_playing else pv._play()

    def mouseMoveEvent(self, e):
        if self._drag_vol:
            self._set_vol_x(e.position().x())
        elif self._drag_seek:
            self._seek_x(e.position().x())
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_vol  = False
        self._drag_seek = False
        super().mouseReleaseEvent(e)

    def _set_vol_x(self, x):
        vr = self._vol_rect()
        ratio = max(0.0, min(1.0, (x - vr.x()) / vr.width()))
        self._pv._set_volume(ratio)
        self.update()

    def _seek_x(self, x):
        br = self._bar_rect()
        ratio = max(0.0, min(1.0, (x - br.x()) / br.width()))
        target = ratio * self._pv.project.total_duration()
        self._pv.player.seek_to_time(target)
        self._pv.timeline.set_playhead(target)


class PreviewWidget(ClipPropertiesMixin, MediaBrowserMixin, ProjectsViewMixin, QWidget):
    """Display de vídeo com controles de playback."""

    def __init__(self, project, timeline_widget, parent=None):
        super().__init__(parent)
        self.project = project
        self.timeline = timeline_widget
        self._is_playing = False
        self._progress_value = 0.0
        self._time_text = ''
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("background: transparent;")
        layout.addWidget(self._stack, stretch=1)

        # Página 0 — display
        self._display_page = QWidget(self._stack)
        self._display_page.setStyleSheet("background: transparent;")
        dp_layout = QVBoxLayout(self._display_page)
        dp_layout.setContentsMargins(0, 0, 0, 0)
        dp_layout.setSpacing(0)

        self._display = _VideoDisplay(self, self._display_page)
        dp_layout.addWidget(self._display, stretch=1)

        self._play_overlay = None
        self._stack.addWidget(self._display_page)

        self.player = TimelinePlayerQt(self)
        self.player.set_project(self.project)

        self._projects_panel = None
        self._browser = None
        self._props_panel = None
        self._paused_at = None
        self._master_volume = 1.0
        self._muted = False
        self._vol_before_mute = 1.0
        self._fullscreen_win = None

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
        h, w = frame_bgr.shape[:2]
        rgb = frame_bgr[:, :, ::-1].copy()
        img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        px = QPixmap.fromImage(img)
        self._display._last_pixmap = px
        self._display.setPixmap(
            px.scaled(self._display.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        self.set_has_media(True)

    def _show_play_button(self, clear_frame=True):
        if clear_frame:
            self._display._last_pixmap = None
            self._display.setPixmap(QPixmap())
            self._display.setText("")
        if not self._play_overlay:
            self._play_overlay = _PlayOverlay(self._display)
        self._play_overlay.show()
        QTimer.singleShot(0, self._center_overlay)

    def _center_overlay(self):
        if self._play_overlay:
            s = self._play_overlay.width()
            dw, dh = self._display.width(), self._display.height()
            x = (dw - s) // 2
            y = (dh - s) // 2
            self._play_overlay.move(x, y)

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
        self._paused_at = self.player._get_current_time() if self.player.is_playing else self.player._start_offset
        self.player.pause()
        self._is_playing = False
        self._show_play_button(clear_frame=False)
        self._display.update()

    def _play(self):
        pos = self._paused_at if self._paused_at is not None else self.timeline.playhead_pos
        self.player.play_from(pos, self.timeline.playback_speed)
        self._paused_at = None
        self._is_playing = True
        self._display.setText("")
        if self._play_overlay:
            self._play_overlay.hide()
        self._display.update()

    def _set_volume(self, ratio):
        self._master_volume = max(0.0, min(1.0, ratio))
        self._muted = self._master_volume == 0.0
        self.player._master_volume = self._master_volume

    def _toggle_mute(self):
        if self._muted:
            self._set_volume(max(0.1, self._vol_before_mute))
        else:
            self._vol_before_mute = self._master_volume
            self._set_volume(0.0)

    def _open_fullscreen(self):
        if self._fullscreen_win:
            self._fullscreen_win._close()
            return
        self._fullscreen_win = _FullscreenWindow(self, self)

    # ── signals ───────────────────────────────────────────────────────────────

    def _on_time_update(self, time_pos):
        total = self.project.total_duration()
        if total > 0:
            self._progress_value = time_pos / total
            m,  s  = int(time_pos) // 60, time_pos % 60
            tm, ts = int(total)    // 60, total    % 60
            self._time_text = f"{m}:{s:04.1f} / {tm}:{ts:04.1f}"
        self._display.update()
        self.timeline.playhead_pos = time_pos
        self.timeline._scene.update_playhead(time_pos, self.timeline.zoom)

    def _on_ended(self):
        self.set_has_media(False)
        self._is_playing = False
        self._paused_at = None
        self._progress_value = 0.0
        self._time_text = ''
        self._show_play_button()
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


class _PlayOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self._pressed = False
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(56, 56)

    def enterEvent(self, e): self._hover = True; self.update(); super().enterEvent(e)
    def leaveEvent(self, e): self._hover = False; self.update(); super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True; self.update()
        display = self.parent()
        display_page = display.parent() if display else None
        preview = display_page.parent().parent() if display_page else None
        if preview and hasattr(preview, "_on_display_click"):
            preview._on_display_click(e)

    def mouseReleaseEvent(self, e): self._pressed = False; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        ts = 18.0 if self._pressed else 22.0
        alpha = 180 if self._pressed else (255 if self._hover else 210)
        tx = cx - ts * 0.4
        poly = QPolygonF([QPointF(tx, cy - ts * 0.6), QPointF(tx, cy + ts * 0.6), QPointF(tx + ts, cy)])
        p.setBrush(QColor(255, 255, 255, alpha)); p.setPen(Qt.NoPen)
        p.drawPolygon(poly); p.end()
