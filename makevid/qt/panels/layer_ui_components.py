"""Componentes de UI reutilizáveis do editor de layers."""

import numpy as np
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QMimeData
from PySide6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPainterPath, QDrag,
    QConicalGradient, QLinearGradient,
)

from makevid.qt.theme import C


class _GlowButton(QPushButton):
    """Botão com luz girando na borda."""

    def __init__(self, text, glow_colors=None, bg="rgba(255,255,255,0.07)", fg="#fff", parent=None):
        super().__init__(text, parent)
        self._glow_colors = glow_colors or [
            QColor(0, 220, 255), QColor(180, 80, 255),
            QColor(0, 180, 255), QColor(255, 80, 180),
        ]
        self._bg = bg
        self._fg = fg
        self._angle = 0.0
        self._animating = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start_glow(self):
        if not self._animating:
            self._animating = True
            self._timer.start()

    def stop_glow(self):
        self._animating = False
        self._timer.stop()
        self.update()

    def _tick(self):
        self._angle = (self._angle + 3.0) % 360.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = 10
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, r, r)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(self._bg) if isinstance(self._bg, str) else QColor(*self._bg)))
        p.drawPath(path)
        if self._animating:
            border = 2
            cg = QConicalGradient(w / 2, h / 2, self._angle)
            cg.setCoordinateMode(QConicalGradient.CoordinateMode.LogicalMode)
            n = len(self._glow_colors)
            for i, c in enumerate(self._glow_colors):
                cg.setColorAt(i / n, c)
            cg.setColorAt(1.0, self._glow_colors[0])
            inner = QPainterPath()
            inner.addRoundedRect(border, border, w - border * 2, h - border * 2, r - 1, r - 1)
            ring = QPainterPath(path)
            ring = ring.subtracted(inner)
            p.setBrush(QBrush(cg))
            p.drawPath(ring)
        else:
            p.setPen(QPen(QColor(80, 80, 100, 80), 1))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        p.setPen(QColor(self._fg))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()


class _SplitConfirmWidget(QWidget):
    """Botão duplo [Esquerda | Direita] com divisor central e efeito glow."""

    left_clicked  = Signal()
    right_clicked = Signal()

    def __init__(self, left_text, right_text, left_color="#ff6060", right_color="#00ccff", parent=None):
        super().__init__(parent)
        self._left_text   = left_text
        self._right_text  = right_text
        self._left_color  = QColor(left_color)
        self._right_color = QColor(right_color)
        self._angle = 0.0
        self._glowing = False
        self._hover_left  = False
        self._hover_right = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(30)

    def start_glow(self):
        if not self._glowing:
            self._glowing = True
            self._timer.start()

    def stop_glow(self):
        self._glowing = False
        self._timer.stop()
        self.update()

    def _tick(self):
        self._angle = (self._angle + 3.0) % 360.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        mid = w // 2
        r = 10
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, r, r)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(30, 20, 20, 200)))
        p.drawPath(path)
        if self._glowing:
            from PySide6.QtGui import QPainterPathStroker
            cg = QConicalGradient(w / 2, h / 2, self._angle)
            cg.setCoordinateMode(QConicalGradient.CoordinateMode.LogicalMode)
            colors = [self._left_color, self._right_color, self._left_color, self._right_color]
            for i, c in enumerate(colors):
                cg.setColorAt(i / len(colors), c)
            cg.setColorAt(1.0, colors[0])
            stroker = QPainterPathStroker()
            stroker.setWidth(2.0)
            p.setBrush(QBrush(cg))
            p.drawPath(stroker.createStroke(path))
        elif self._hover_right:
            p.setPen(QPen(self._right_color, 1))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        else:
            p.setPen(QPen(QColor(80, 80, 100, 60), 1))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawLine(mid, 4, mid, h - 4)
        if self._hover_right:
            rp = QPainterPath()
            rp.addRoundedRect(mid, 0, mid, h, r, r)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 200, 255, 30))
            p.drawPath(rp)
        font = QFont("Segoe UI", 8, QFont.Bold)
        p.setFont(font)
        p.setPen(self._left_color)
        p.drawText(0, 0, mid, h, Qt.AlignCenter, self._left_text)
        p.setPen(self._right_color)
        p.drawText(mid, 0, mid, h, Qt.AlignCenter, self._right_text)
        p.end()

    def mouseMoveEvent(self, event):
        mid = self.width() // 2
        self._hover_left  = event.position().x() < mid
        self._hover_right = not self._hover_left
        self.update()

    def leaveEvent(self, event):
        self._hover_left = self._hover_right = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.position().x() < self.width() // 2:
                self.left_clicked.emit()
            else:
                self.right_clicked.emit()
        event.accept()


class _LayerDragLabel(QLabel):
    """Label que permite arrastar o item para outra posição/track na timeline."""

    def __init__(self, item_id, display_name, parent=None):
        super().__init__(f"\u266b {display_name}", parent)
        self._item_id = item_id
        self._drag_start = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 8:
            super().mouseMoveEvent(event)
            return
        mime = QMimeData()
        mime.setData("application/x-makevid-track-item", self._item_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)


class _ResponsiveActionGrid(QWidget):
    """Grid responsivo que redistribui widgets conforme a largura disponível."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._widgets = []
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(8)
        self._grid.setVerticalSpacing(8)
        self._grid.setAlignment(Qt.AlignTop)

    def add_widget(self, widget):
        self._widgets.append(widget)
        widget.setParent(self)
        widget.show()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def finalize(self):
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(self)
        if not self._widgets:
            return
        visible = [w for w in self._widgets if w.isVisible()]
        if not visible:
            return
        available = max(180, self.width())  # fallback 180px quando oculto
        cols = max(1, available // (90 + self._grid.horizontalSpacing()))
        cols = min(cols, len(visible))
        for index, widget in enumerate(visible):
            self._grid.addWidget(widget, index // cols, index % cols)
        for col in range(cols):
            self._grid.setColumnStretch(col, 1)
        self._grid.invalidate()
