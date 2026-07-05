"""Clip Item - Item de video na track de video da timeline."""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPainterPath, QLinearGradient,
    QConicalGradient, QPainterPathStroker
)
from makevid.qt.theme import C

# ── Z-Values canônicos ────────────────────────────────────────────────────────
Z_BACKGROUND  = -100
Z_GRID        =  -50
Z_TRACK_LAYER =    0
Z_CLIP        =   10
Z_AUDIO_ITEM  =   20
Z_MARKER      =   30
Z_PLAYHEAD    =  100
Z_OVERLAY     =  200

# ── Layout de item ────────────────────────────────────────────────────────────
ITEM_PAD_X = 6   # padding horizontal (cada lado)
ITEM_PAD_Y = 5   # padding vertical (cada lado)


class ClipGraphicsItem(QGraphicsItem):

    _thumb_cache = None
    _global_frame = 0
    _anim_timer = None
    _beam_angle = 0.0

    def __init__(self, clip, x, y, w, h, selected=False):
        super().__init__()
        self.clip = clip
        self._w = w
        self._h = h
        self._hovered = False
        self._selected = selected

        import random
        self._beam_phase = random.uniform(0, 360)

        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(False)   # hover gerenciado pelo HoverController
        self.setZValue(Z_CLIP)
        self.setPos(x, y)

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
        return QRectF(-4, -4, self._w + 8, self._h + 8)

    def set_size(self, w, h):
        if self._w == w and self._h == h:
            return
        self.prepareGeometryChange()
        self._w = w
        self._h = h
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        x = 2
        y = 3
        w = self._w - 4
        h = self._h - 6
        hw = 7
        r = 8.0

        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), r, r)

        grad = QLinearGradient(x, y, x, y + h)
        top = QColor(self._fill2); top.setAlpha(230)
        bot = QColor(self._fill);  bot.setAlpha(210)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bot)
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        if self._selected:
            painter.fillPath(path, QBrush(QColor(255, 255, 255, 18)))

        if self._selected:
            self._paint_beam_border(painter, path, x, y, w, h, r)
        elif self._hovered:
            bdr = QColor(C["accent"]); bdr.setAlpha(220)
            painter.setPen(QPen(bdr, 1.8))
            painter.drawPath(path)
        else:
            bdr = QColor(self._bdr); bdr.setAlpha(110)
            painter.setPen(QPen(bdr, 0.8))
            painter.drawPath(path)

        rp = QPainterPath()
        rp.addRoundedRect(QRectF(x + r, y + 1, w - r * 2, h * 0.28), r * 0.4, r * 0.4)
        rg = QLinearGradient(0, y, 0, y + h * 0.28)
        rg.setColorAt(0.0, QColor(255, 255, 255, 22))
        rg.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(rp, QBrush(rg))

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

        hc = QColor(C["primary"]); hc.setAlpha(200)
        painter.setPen(Qt.NoPen)
        lh = QPainterPath()
        lh.addRoundedRect(QRectF(x, y, hw, h), r, 2)
        painter.fillPath(lh, hc)
        rh_path = QPainterPath()
        rh_path.addRoundedRect(QRectF(x + w - hw, y, hw, h), 2, r)
        painter.fillPath(rh_path, hc)

        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))
        for gy in range(int(y + 10), int(y + h - 10), 5):
            painter.drawLine(QPointF(x + 2, gy), QPointF(x + hw - 1, gy))
            painter.drawLine(QPointF(x + w - hw + 1, gy), QPointF(x + w - 2, gy))

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

    def _paint_beam_border(self, painter, path, x, y, w, h, r):
        angle = (ClipGraphicsItem._beam_angle + self._beam_phase) % 360

        stroker = QPainterPathStroker()
        stroker.setWidth(2.5)
        border_area = stroker.createStroke(path)

        stroker_glow = QPainterPathStroker()
        stroker_glow.setWidth(7.0)
        glow_area = stroker_glow.createStroke(path)

        cg = QConicalGradient(0.5, 0.5, angle)
        cg.setCoordinateMode(QConicalGradient.CoordinateMode.ObjectMode)
        cg.setColorAt(0.00, QColor(0,   220, 255, 255))
        cg.setColorAt(0.15, QColor(180,  80, 255, 255))
        cg.setColorAt(0.35, QColor(0,   120, 255, 255))
        cg.setColorAt(0.50, QColor(0,   220, 255, 255))
        cg.setColorAt(0.65, QColor(180,  80, 255, 255))
        cg.setColorAt(0.85, QColor(0,   120, 255, 255))
        cg.setColorAt(1.00, QColor(0,   220, 255, 255))

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setOpacity(0.35)
        painter.fillPath(glow_area, QBrush(cg))
        painter.setOpacity(1.0)
        painter.fillPath(border_area, QBrush(cg))
        painter.restore()

    @classmethod
    def tick_animation(cls):
        cls._global_frame += 1
        cls._beam_angle = (cls._beam_angle + 8.0) % 360
