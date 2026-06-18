"""Playhead - Indicador de posição com hover glow (visual completo)."""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPolygonF, QFont


class PlayheadItem(QGraphicsItem):
    """Playhead vertical com cabeça triangular e hover glow."""

    def __init__(self, time_pos, zoom, lbl_w, scene_h):
        super().__init__()
        self._time_pos = time_pos
        self._zoom = zoom
        self._lbl_w = lbl_w
        self._scene_h = scene_h
        self._hovered = False
        self.setZValue(100)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self._dragging = False
        self._press_pos = None
        self._tl = None  # set externally
        self._update_x()

    def set_position(self, time_pos, zoom, lbl_w):
        self.prepareGeometryChange()
        self._time_pos = time_pos
        self._zoom = zoom
        self._lbl_w = lbl_w
        self._update_x()
        self.update()

    def _update_x(self):
        self._px = self._lbl_w + int(self._time_pos * self._zoom)

    def boundingRect(self) -> QRectF:
        return QRectF(self._px - 14, 0, 28, self._scene_h)

    def shape(self):
        """Hitbox cobrindo toda a faixa vermelha para facilitar grab."""
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(QRectF(self._px - 10, 0, 20, self._scene_h))
        return path

    def paint(self, painter: QPainter, option, widget=None):
        px = self._px
        h = self._scene_h
        hovered = self._hovered

        # Texto do tempo no badge
        t = self._time_pos
        m, s = int(t) // 60, t % 60
        time_txt = f"{m:02d}:{s:04.1f}"

        if hovered:
            # Glow expandido
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(80, 0, 0, 60)))
            painter.drawRect(QRectF(px - 8, 0, 16, h))
            painter.setBrush(QBrush(QColor(120, 0, 0, 40)))
            painter.drawRect(QRectF(px - 5, 0, 10, h))

            # Linha grossa
            painter.setPen(QPen(QColor("#ff4444"), 5))
            painter.drawLine(px, 0, px, h)

            # Cabeça maior
            head = QPolygonF([
                QPointF(px - 14, 0), QPointF(px + 14, 0),
                QPointF(px + 8, 10), QPointF(px, 20), QPointF(px - 8, 10),
            ])
            painter.setPen(QPen(QColor("#ffaaaa"), 2))
            painter.setBrush(QBrush(QColor("#ff3333")))
            painter.drawPolygon(head)

            # Ponto branco maior
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(QPointF(px, 8), 4, 4)

            # Tempo no badge
            painter.setPen(QPen(QColor("#0a0a0f")))
            painter.setFont(QFont("Consolas", 8, QFont.Bold))
            # Balao de tempo (hover)
            tw = 52
            bh = 18
            bx = px - tw // 2
            by = 22
            painter.setPen(QPen(QColor("#ffd700"), 1))
            painter.setBrush(QBrush(QColor("#111328")))
            painter.drawRoundedRect(QRectF(bx, by, tw, bh), 4, 4)
            tri = QPolygonF([
                QPointF(px - 5, by), QPointF(px + 5, by), QPointF(px, by - 6),
            ])
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#111328")))
            painter.drawPolygon(tri)
            painter.setPen(QPen(QColor("#ffd700"), 1))
            painter.drawLine(QPointF(px - 5, by), QPointF(px, by - 6))
            painter.drawLine(QPointF(px + 5, by), QPointF(px, by - 6))
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Consolas", 9, QFont.Bold))
            painter.drawText(QRectF(bx, by, tw, bh), Qt.AlignCenter, time_txt)

            # Triângulo inferior
            foot = QPolygonF([
                QPointF(px - 8, h), QPointF(px + 8, h), QPointF(px, h - 10),
            ])
            painter.setBrush(QBrush(QColor("#ff3333")))
            painter.setPen(QPen(QColor("#ffaaaa"), 1))
            painter.drawPolygon(foot)
        else:
            # Normal
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(50, 0, 0, 80)))
            painter.drawRect(QRectF(px - 4, 0, 8, h))

            painter.setPen(QPen(QColor("#ff2222"), 3))
            painter.drawLine(px, 0, px, h)

            head = QPolygonF([
                QPointF(px - 10, 0), QPointF(px + 10, 0),
                QPointF(px + 5, 8), QPointF(px, 16), QPointF(px - 5, 8),
            ])
            painter.setPen(QPen(QColor("#ff6666"), 2))
            painter.setBrush(QBrush(QColor("#ff2222")))
            painter.drawPolygon(head)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(QPointF(px, 7), 3, 3)

            foot = QPolygonF([
                QPointF(px - 6, h), QPointF(px + 6, h), QPointF(px, h - 8),
            ])
            painter.setBrush(QBrush(QColor("#ff2222")))
            painter.drawPolygon(foot)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.SizeHorCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._press_pos = event.scenePos()
            self.setCursor(Qt.SizeHorCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and self._tl:
            if not self._dragging:
                from PySide6.QtWidgets import QApplication
                if (event.scenePos() - self._press_pos).manhattanLength() < QApplication.startDragDistance():
                    return
                self._dragging = True
            x = event.scenePos().x()
            t = max(0, (x - self._lbl_w) / self._zoom)
            self._tl.set_playhead(t)
            event.accept()

    def mouseReleaseEvent(self, event):
        if not self._dragging:
            # Foi só um clique, não arrastar — deixar o evento passar para a scene/interaction
            event.ignore()
        else:
            event.accept()
        self._dragging = False
        self._press_pos = None
