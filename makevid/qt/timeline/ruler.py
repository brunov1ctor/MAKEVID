"""Ruler - Barra de tempo com hover highlight (visual completo)."""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter

from makevid.qt.theme import C


class RulerItem(QGraphicsItem):
    """Régua de tempo com marcas adaptativas e hover highlight."""

    def __init__(self, lbl_w, scene_w, ruler_h, zoom, total_dur):
        super().__init__()
        self._lbl_w = lbl_w
        self._scene_w = scene_w
        self._ruler_h = ruler_h
        self._zoom = zoom
        self._total_dur = total_dur
        self._hover_x = -100
        self.setZValue(4)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.NoButton)  # nao captura clicks

    def boundingRect(self) -> QRectF:
        return QRectF(self._lbl_w, 0, self._scene_w - self._lbl_w, self._ruler_h)

    def paint(self, painter: QPainter, option, widget=None):
        lbl_w = self._lbl_w
        w = self._scene_w
        h = self._ruler_h
        pps = self._zoom

        # Fundo uniforme discreto
        painter.fillRect(QRectF(lbl_w, 0, w - lbl_w, h), QColor("#0d1020"))

        # Linha inferior sutil (não mais borda dourada grossa)
        painter.setPen(QPen(QColor(C["glass_border"]), 1))
        painter.drawLine(lbl_w, h - 1, w, h - 1)

        # Step adaptativo
        if pps >= 80:
            step = 1.0
        elif pps >= 40:
            step = 2.0
        elif pps >= 20:
            step = 5.0
        elif pps >= 10:
            step = 10.0
        else:
            step = 15.0

        subdivs = 4 if step <= 2 else 5
        sub_step = step / subdivs
        hover_x = self._hover_x

        t = 0.0
        while t <= self._total_dur + step:
            x = lbl_w + int(t * pps)
            if lbl_w <= x <= w:
                # Marca principal
                painter.setPen(QPen(QColor(C["primary"]), 1))
                painter.drawLine(x, h - 12, x, h - 1)

                m, s = int(t) // 60, t % 60
                txt = f"{m:02d}:{int(s):02d}" if step >= 10 else f"{m:02d}:{s:04.1f}"

                is_hovered = abs(x - hover_x) < 25
                if is_hovered:
                    tw = len(txt) * 7 + 6
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor(C["glass_hover"])))
                    painter.drawRoundedRect(QRectF(x - 1, 2, tw, 14), 3, 3)
                    painter.setPen(QPen(QColor(C["text"])))
                    painter.setFont(QFont("Consolas", 9, QFont.Bold))
                else:
                    painter.setPen(QPen(QColor(C["text3"])))
                    painter.setFont(QFont("Consolas", 8))

                painter.drawText(QPointF(x + 3, 13), txt)

                # Sub-marcas
                for si in range(1, subdivs):
                    sx = lbl_w + int((t + sub_step * si) * pps)
                    if lbl_w <= sx <= w:
                        alpha = 80 if si == subdivs // 2 else 45
                        painter.setPen(QPen(QColor(C["glass_border"]), 1))
                        painter.drawLine(sx, h - (7 if si == subdivs // 2 else 4), sx, h - 1)

            t += step

    def hoverMoveEvent(self, event):
        self._hover_x = event.pos().x()
        self.update()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover_x = -100
        self.update()
        super().hoverLeaveEvent(event)
