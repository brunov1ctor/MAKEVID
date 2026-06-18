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

        # Fundo com gradiente de 3 faixas
        third = h // 3
        painter.fillRect(QRectF(lbl_w, 0, w - lbl_w, third), QColor("#181c32"))
        painter.fillRect(QRectF(lbl_w, third, w - lbl_w, third), QColor("#141830"))
        painter.fillRect(QRectF(lbl_w, third * 2, w - lbl_w, h - third * 2), QColor("#10142a"))

        # Borda inferior dourada forte
        painter.setPen(QPen(QColor(C["gold"]), 2))
        painter.drawLine(lbl_w, h - 1, w, h - 1)

        # Borda superior sutil
        painter.setPen(QPen(QColor("#2a3050"), 1))
        painter.drawLine(lbl_w, 0, w, 0)

        # Borda inferior secundária
        painter.setPen(QPen(QColor("#3a2a10"), 1))
        painter.drawLine(lbl_w, h - 3, w, h - 3)

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
                # Marca principal grossa
                painter.setPen(QPen(QColor(C["gold"]), 2))
                painter.drawLine(x, h - 16, x, h - 2)

                # Marca superior fina
                painter.setPen(QPen(QColor("#4a4a6a"), 1))
                painter.drawLine(x, 2, x, 6)

                m, s = int(t) // 60, t % 60
                txt = f"{m:02d}:{int(s):02d}" if step >= 10 else f"{m:02d}:{s:04.1f}"

                # Hover highlight
                is_hovered = abs(x - hover_x) < 25
                if is_hovered:
                    # Background highlight
                    tw = len(txt) * 7 + 6
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor("#2a2040")))
                    painter.drawRect(QRectF(x - 1, 2, tw, 15))
                    # Texto branco bold
                    painter.setPen(QPen(QColor("#ffffff")))
                    painter.setFont(QFont("Consolas", 10, QFont.Bold))
                else:
                    painter.setPen(QPen(QColor("#9999bb")))
                    painter.setFont(QFont("Consolas", 9, QFont.Bold))

                painter.drawText(QPointF(x + 3, 14), txt)

                # Sub-marcas
                for si in range(1, subdivs):
                    sx = lbl_w + int((t + sub_step * si) * pps)
                    if lbl_w <= sx <= w:
                        if si == subdivs // 2:
                            painter.setPen(QPen(QColor("#5a5a7a"), 1))
                            painter.drawLine(sx, h - 10, sx, h - 2)
                        else:
                            painter.setPen(QPen(QColor("#3a3a5a"), 1))
                            painter.drawLine(sx, h - 6, sx, h - 2)

            t += step

    def hoverMoveEvent(self, event):
        self._hover_x = event.pos().x()
        self.update()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover_x = -100
        self.update()
        super().hoverLeaveEvent(event)
