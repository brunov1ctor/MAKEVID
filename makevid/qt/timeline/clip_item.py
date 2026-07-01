"""Clip Item - QGraphicsItem para clips de video na timeline (visual completo)."""

from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath,
    QLinearGradient
)

from makevid.qt.theme import C


class ClipGraphicsItem(QGraphicsRectItem):
    """Clip de video na track de video com visual premium e animação contínua."""

    _thumb_cache = None
    _global_frame_index = 0  # Compartilhado: todos animam sincronizados
    _anim_timer = None

    def __init__(self, clip, x, y, w, h, selected=False):
        super().__init__(x + 1, y + 2, w - 2, h - 4)
        self.clip = clip
        self._x, self._y, self._w, self._h = x, y, w, h
        self._hovered = False
        self._selected = selected

        if ClipGraphicsItem._thumb_cache is None:
            from makevid.qt.timeline.thumbnails import ThumbnailCache
            ClipGraphicsItem._thumb_cache = ThumbnailCache()

        # Cores por status (independente de seleção)
        if clip.status == "done":
            self._fill   = QColor("#0d2e1a")
            self._fill2  = QColor("#1a4a28")
            self._border = QColor("#1e5c30")
        elif clip.status == "generating":
            self._fill   = QColor("#2a1e06")
            self._fill2  = QColor("#3a2a0a")
            self._border = QColor(C["primary"])
        elif clip.status == "error":
            self._fill   = QColor("#2a0a0a")
            self._fill2  = QColor("#3a1010")
            self._border = QColor(C["danger"])
        else:
            self._fill   = QColor("#12122a")
            self._fill2  = QColor("#1a1a38")
            self._border = QColor("#2a2a50")

        self.setPen(Qt.NoPen)
        self.setBrush(Qt.NoBrush)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    def paint(self, painter: QPainter, option, widget=None):
        """Custom paint: rounded card com gradiente, thumbnail, highlight e labels."""
        x, y, w, h = self._x + 2, self._y + 3, self._w - 4, self._h - 6
        radius = 8.0
        hw = 7  # handle width

        # ── Fundo arredondado com gradiente ──────────────────────────────────
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)

        grad = QLinearGradient(x, y, x, y + h)
        top = QColor(self._fill2)
        top.setAlpha(230)
        bot = QColor(self._fill)
        bot.setAlpha(210)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bot)
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        # ── Borda translúcida ─────────────────────────────────────────────────
        border = QColor(self._border)
        border.setAlpha(180 if self._selected else 100)
        painter.setPen(QPen(border, 1.2 if self._selected else 0.8))
        painter.drawPath(path)

        # ── Highlight de seleção (overlay branco sutil) ───────────────────────
        if self._selected:
            sel_path = QPainterPath()
            sel_path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
            painter.drawPath(sel_path)

        # ── Highlight no topo (reflexo glass) ────────────────────────────────
        ref_path = QPainterPath()
        ref_path.addRoundedRect(QRectF(x + radius, y + 1, w - radius * 2, h * 0.28), radius * 0.4, radius * 0.4)
        ref_grad = QLinearGradient(0, y, 0, y + h * 0.28)
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, 22))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(ref_path, QBrush(ref_grad))

        # ── Thumbnail ─────────────────────────────────────────────────────────
        thumb_drawn = False
        try:
            if self.clip.status == "done" and self.clip.video_path and w > 20:
                from pathlib import Path
                from PySide6.QtGui import QPixmap as QP
                vpath = Path(self.clip.video_path)
                if vpath.exists():
                    thumb_w = max(10, int(w - hw * 2 - 4))
                    thumb_h = max(10, int(h - 6))
                    cache = ClipGraphicsItem._thumb_cache
                    frames = cache.get_gif_frames(self.clip, thumb_w, thumb_h)
                    if frames and len(frames) > 1:
                        idx = ClipGraphicsItem._global_frame_index % len(frames)
                        if not frames[idx].isNull():
                            # Clip thumbnail dentro do path arredondado
                            painter.save()
                            painter.setClipPath(path)
                            painter.drawPixmap(int(x + hw + 2), int(y + 3), frames[idx])
                            painter.restore()
                            thumb_drawn = True
                    if not thumb_drawn:
                        png = vpath.with_suffix('.png')
                        if png.exists():
                            px = QP(str(png)).scaled(thumb_w, thumb_h,
                                                     Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                            if not px.isNull():
                                painter.save()
                                painter.setClipPath(path)
                                painter.drawPixmap(int(x + hw + 2), int(y + 3), px)
                                painter.restore()
                                thumb_drawn = True
        except Exception:
            pass

        # ── Trim handles arredondados ─────────────────────────────────────────
        handle_color = QColor(C["primary"])
        handle_color.setAlpha(200)
        painter.setPen(Qt.NoPen)
        painter.setBrush(handle_color)
        lh = QPainterPath()
        lh.addRoundedRect(QRectF(x, y, hw, h), radius, 2)
        painter.fillPath(lh, handle_color)
        rh = QPainterPath()
        rh.addRoundedRect(QRectF(x + w - hw, y, hw, h), 2, radius)
        painter.fillPath(rh, handle_color)

        # Grip lines
        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        for gy in range(int(y + 10), int(y + h - 10), 5):
            painter.drawLine(QPointF(x + 2, gy), QPointF(x + hw - 1, gy))
            painter.drawLine(QPointF(x + w - hw + 1, gy), QPointF(x + w - 2, gy))

        # ── Hover overlay ─────────────────────────────────────────────────────
        if self._hovered:
            hover_path = QPainterPath()
            hover_path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
            hover_fill = QColor(255, 255, 255, 18)
            painter.setPen(Qt.NoPen)
            painter.fillPath(hover_path, hover_fill)
            hover_border = QColor(C["accent"])
            hover_border.setAlpha(220)
            painter.setPen(QPen(hover_border, 1.8))
            painter.drawPath(hover_path)

        # ── Labels ────────────────────────────────────────────────────────────
        painter.setPen(QPen(QColor(255, 255, 255, 220)))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label = self.clip.prompt[:18] if self.clip.prompt else "(vazio)"
        painter.drawText(QPointF(x + hw + 6, y + 14), f"{self.clip.position+1}. {label}")

        painter.setPen(QPen(QColor(C["accent"])))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(QPointF(x + hw + 6, y + 26), f"{self.clip.duration:.1f}s")

        if self.clip.status == "done":
            ok_c = QColor(C["accent"])
            ok_c.setAlpha(200)
            painter.setPen(QPen(ok_c))
            painter.setFont(QFont("Consolas", 7, QFont.Bold))
            painter.drawText(QPointF(x + w - 22, y + 13), "OK")

    def hoverEnterEvent(self, event):
        self._hovered = True
        border = QColor(C["accent"])
        border.setAlpha(220)
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        local_x = event.pos().x() - self.rect().x()
        w = self.rect().width()
        if local_x <= 8 or (w - local_x) <= 8:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    @classmethod
    def tick_animation(cls):
        """Chamado por timer externo para avançar frame de animação."""
        cls._global_frame_index += 1
