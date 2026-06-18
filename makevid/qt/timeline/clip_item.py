"""Clip Item - QGraphicsItem para clips de video na timeline (visual completo)."""

from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QPainterPath

from makevid.qt.theme import C


class ClipGraphicsItem(QGraphicsRectItem):
    """Clip de video na track de video com visual premium."""

    # Cache compartilhado entre todas as instancias
    _thumb_cache = None

    def __init__(self, clip, x, y, w, h, selected=False):
        super().__init__(x + 1, y + 2, w - 2, h - 4)
        self.clip = clip
        self._x, self._y, self._w, self._h = x, y, w, h
        self._hovered = False
        self._selected = selected
        self._gif_index = 0
        self._gif_timer = None

        # Inicializar cache compartilhado
        if ClipGraphicsItem._thumb_cache is None:
            from makevid.qt.timeline.thumbnails import ThumbnailCache
            ClipGraphicsItem._thumb_cache = ThumbnailCache()

        # Visual baseado no status
        if clip.status == "done":
            self._fill = QColor("#1a4a2a") if not selected else QColor("#2a6a3a")
            self._border = QColor(C["cyan"]) if selected else QColor("#1a5a2a")
        elif clip.status == "generating":
            self._fill = QColor("#3a2a0a")
            self._border = QColor(C["gold"])
        elif clip.status == "error":
            self._fill = QColor("#3a1010")
            self._border = QColor(C["red"])
        else:
            self._fill = QColor("#2a2a4e") if selected else QColor("#1a1a2e")
            self._border = QColor(C["gold"]) if selected else QColor("#2a2a4a")

        self.setPen(QPen(self._border, 2 if selected else 1.5))
        self.setBrush(QBrush(self._fill))
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    def paint(self, painter: QPainter, option, widget=None):
        """Custom paint com thumbnail, grip lines e labels."""
        super().paint(painter, option, widget)

        x, y, w, h = self._x + 1, self._y + 2, self._w - 2, self._h - 4
        hw = 6  # handle width

        # Thumbnail/GIF no corpo do clip
        thumb_drawn = False
        try:
            if self.clip.status == "done" and self.clip.video_path and w > 14:
                from pathlib import Path
                if Path(self.clip.video_path).exists():
                    cache = ClipGraphicsItem._thumb_cache
                    thumb_w = max(10, int(w - hw * 2 - 2))
                    thumb_h = max(10, int(h - 4))
                    if self._hovered:
                        frames = cache.get_gif_frames(self.clip, thumb_w, thumb_h)
                        if frames:
                            idx = self._gif_index % len(frames)
                            painter.drawPixmap(int(x + hw + 1), int(y + 2), frames[idx])
                            thumb_drawn = True
                    else:
                        thumb = cache.get_thumb(self.clip, thumb_w, thumb_h)
                        if thumb:
                            painter.drawPixmap(int(x + hw + 1), int(y + 2), thumb)
                            thumb_drawn = True
        except Exception:
            pass

        # Fallback: gradiente escuro se thumbnail nao carregou
        if not thumb_drawn and self.clip.status == "done" and w > 14:
            from PySide6.QtGui import QLinearGradient
            grad = QLinearGradient(x + hw, y, x + w - hw, y + h)
            grad.setColorAt(0, QColor("#0a2a1a"))
            grad.setColorAt(1, QColor("#1a4a2a"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRect(QRectF(x + hw + 1, y + 2, w - hw * 2 - 2, h - 4))

        # Trim handles (dourados)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(C["gold"])))
        painter.drawRect(QRectF(x, y, hw, h))
        painter.drawRect(QRectF(x + w - hw, y, hw, h))

        # Grip lines nos handles
        painter.setPen(QPen(QColor("#0a0a0f"), 1))
        for gy in range(int(y + 12), int(y + h - 12), 6):
            painter.drawLine(QPointF(x + 2, gy), QPointF(x + hw - 1, gy))
            painter.drawLine(QPointF(x + w - hw + 1, gy), QPointF(x + w - 2, gy))

        # Label
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label = self.clip.prompt[:18] if self.clip.prompt else "(vazio)"
        painter.drawText(QPointF(x + 8, y + 14), f"{self.clip.position+1}. {label}")

        # Duração
        painter.setPen(QPen(QColor(C["cyan"])))
        painter.setFont(QFont("Consolas", 9, QFont.Bold))
        painter.drawText(QPointF(x + 8, y + 30), f"{self.clip.duration:.1f}s")

        # Status badge
        if self.clip.status == "done":
            painter.setPen(QPen(QColor("#00ffcc")))
            painter.setFont(QFont("Consolas", 8, QFont.Bold))
            painter.drawText(QPointF(x + w - 24, y + 14), "OK")

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setPen(QPen(QColor("#00ffee"), 2))
        self.setCursor(Qt.PointingHandCursor)
        # Iniciar GIF
        if self.clip.status == "done" and self.clip.video_path:
            self._gif_index = 0
            self._gif_timer = self.scene().views()[0].window() if self.scene() else None
            # Usar timer do scene
            if self.scene():
                self._start_gif_animation()
        self.update()
        super().hoverEnterEvent(event)

    def _start_gif_animation(self):
        """Anima GIF a cada 150ms."""
        if not self._hovered:
            return
        self._gif_index += 1
        self.update()
        # Agendar proximo frame
        QTimer.singleShot(150, self._start_gif_animation)

    def hoverMoveEvent(self, event):
        local_x = event.pos().x() - self.rect().x()
        w = self.rect().width()
        if local_x <= 8 or (w - local_x) <= 8:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setPen(QPen(self._border, 2 if self._selected else 1.5))
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)
