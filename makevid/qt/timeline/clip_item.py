"""Clip Item - QGraphicsItem para clips de video na timeline (visual completo)."""

from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QPainterPath

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
        """Custom paint com animação contínua, grip lines e labels."""
        super().paint(painter, option, widget)

        x, y, w, h = self._x + 1, self._y + 2, self._w - 2, self._h - 4
        hw = 6  # handle width

        # Thumbnail/GIF no corpo do clip
        thumb_drawn = False
        try:
            if self.clip.status == "done" and self.clip.video_path and w > 14:
                from pathlib import Path
                from PySide6.QtGui import QPixmap as QP
                vpath = Path(self.clip.video_path)
                if vpath.exists():
                    thumb_w = max(10, int(w - hw * 2 - 2))
                    thumb_h = max(10, int(h - 4))
                    cache = ClipGraphicsItem._thumb_cache
                    # Tentar GIF animado (video real com frames diferentes)
                    frames = cache.get_gif_frames(self.clip, thumb_w, thumb_h)
                    if frames and len(frames) > 1:
                        idx = ClipGraphicsItem._global_frame_index % len(frames)
                        if not frames[idx].isNull():
                            painter.drawPixmap(int(x + hw + 1), int(y + 2), frames[idx])
                            thumb_drawn = True
                    # Fallback: PNG estatico
                    if not thumb_drawn:
                        png = vpath.with_suffix('.png')
                        if png.exists():
                            px = QP(str(png)).scaled(thumb_w, thumb_h,
                                                    Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                            if not px.isNull():
                                painter.drawPixmap(int(x + hw + 1), int(y + 2), px)
                                thumb_drawn = True
        except Exception:
            pass

        # Fallback: nada extra se thumbnail nao carregou
        if not thumb_drawn and self.clip.status == "done" and w > 14:
            pass

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
        self.setPen(QPen(self._border, 2 if self._selected else 1.5))
        self.update()
        super().hoverLeaveEvent(event)

    @classmethod
    def tick_animation(cls):
        """Chamado por timer externo para avançar frame de animação."""
        cls._global_frame_index += 1
