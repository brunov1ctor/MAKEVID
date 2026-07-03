"""Clip Item - Item de video na track de video da timeline."""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath, QLinearGradient
)
from makevid.qt.theme import C


class ClipGraphicsItem(QGraphicsItem):

    _thumb_cache = None
    _global_frame = 0
    _anim_timer = None

    def __init__(self, clip, x, y, w, h, selected=False):
        super().__init__()
        self.clip = clip
        self._x, self._y, self._w, self._h = x, y, w, h
        self._hovered = False
        self._selected = selected

        # Nunca deixar o Qt gerenciar seleção
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

        if ClipGraphicsItem._thumb_cache is None:
            from makevid.qt.timeline.thumbnails import ThumbnailCache
            ClipGraphicsItem._thumb_cache = ThumbnailCache()

        s = clip.status
        if s == "done":
            self._fill  = QColor("#0d2e1a")
            self._fill2 = QColor("#1a4a28")
            self._bdr   = QColor("#1e5c30")
        elif s == "generating":
            self._fill  = QColor("#2a1e06")
            self._fill2 = QColor("#3a2a0a")
            self._bdr   = QColor(C["primary"])
        elif s == "error":
            self._fill  = QColor("#2a0a0a")
            self._fill2 = QColor("#3a1010")
            self._bdr   = QColor(C["danger"])
        else:
            self._fill  = QColor("#12122a")
            self._fill2 = QColor("#1a1a38")
            self._bdr   = QColor("#2a2a50")

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        x = self._x + 2
        y = self._y + 3
        w = self._w - 4
        h = self._h - 6
        hw = 7
        r = 8.0

        # --- fundo ---
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), r, r)

        grad = QLinearGradient(x, y, x, y + h)
        top = QColor(self._fill2); top.setAlpha(230)
        bot = QColor(self._fill);  bot.setAlpha(210)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bot)
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        # --- overlay seleção ---
        if self._selected:
            painter.fillPath(path, QBrush(QColor(255, 255, 255, 18)))

        # --- borda ---
        bdr = QColor(self._bdr)
        if self._selected:
            bdr.setAlpha(220)
            painter.setPen(QPen(bdr, 2.0))
        elif self._hovered:
            bdr = QColor(C["accent"]); bdr.setAlpha(220)
            painter.setPen(QPen(bdr, 1.8))
        else:
            bdr.setAlpha(110)
            painter.setPen(QPen(bdr, 0.8))
        painter.drawPath(path)

        # --- reflexo topo ---
        rp = QPainterPath()
        rp.addRoundedRect(QRectF(x + r, y + 1, w - r * 2, h * 0.28), r * 0.4, r * 0.4)
        rg = QLinearGradient(0, y, 0, y + h * 0.28)
        rg.setColorAt(0.0, QColor(255, 255, 255, 22))
        rg.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(rp, QBrush(rg))

        # --- thumbnail ---
        try:
            if self.clip.status == "done" and self.clip.video_path and w > 20:
                from pathlib import Path
                if Path(self.clip.video_path).exists():
                    tw = max(10, int(w - hw * 2 - 4))
                    th = max(10, int(h - 6))
                    frames = ClipGraphicsItem._thumb_cache.get_gif_frames(self.clip, tw, th)
                    if frames:
                        idx = ClipGraphicsItem._global_frame % len(frames)
                        px = frames[idx]
                        if not px.isNull():
                            painter.save()
                            painter.setClipPath(path)
                            painter.drawPixmap(int(x + hw + 2), int(y + 3), px)
                            painter.restore()
        except Exception:
            pass

        # --- handles ---
        hc = QColor(C["primary"]); hc.setAlpha(200)
        painter.setPen(Qt.NoPen)
        lh = QPainterPath()
        lh.addRoundedRect(QRectF(x, y, hw, h), r, 2)
        painter.fillPath(lh, hc)
        rh = QPainterPath()
        rh.addRoundedRect(QRectF(x + w - hw, y, hw, h), 2, r)
        painter.fillPath(rh, hc)

        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        for gy in range(int(y + 10), int(y + h - 10), 5):
            painter.drawLine(QPointF(x + 2, gy), QPointF(x + hw - 1, gy))
            painter.drawLine(QPointF(x + w - hw + 1, gy), QPointF(x + w - 2, gy))

        # --- labels ---
        painter.setPen(QPen(QColor(255, 255, 255, 220)))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label = self.clip.prompt[:18] if self.clip.prompt else "(vazio)"
        painter.drawText(QPointF(x + hw + 6, y + 14), f"{self.clip.position + 1}. {label}")

        painter.setPen(QPen(QColor(C["accent"])))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(QPointF(x + hw + 6, y + 26), f"{self.clip.duration:.1f}s")

        if self.clip.status == "done":
            ok = QColor(C["accent"]); ok.setAlpha(200)
            painter.setPen(QPen(ok))
            painter.setFont(QFont("Consolas", 7, QFont.Bold))
            painter.drawText(QPointF(x + w - 22, y + 13), "OK")

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        lx = event.pos().x() - self._x
        self.setCursor(Qt.SizeHorCursor if lx <= 8 or (self._w - lx) <= 8 else Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    @classmethod
    def tick_animation(cls):
        cls._global_frame += 1
