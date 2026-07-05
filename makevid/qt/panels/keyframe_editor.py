"""Keyframe Editor Qt - Canvas interativo para keyframes de volume."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF

from makevid.qt.theme import C


class KeyframeEditorWidget(QWidget):
    """Canvas interativo para editar keyframes de volume (estilo CapCut)."""

    changed = Signal(bool)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self._item = item
        self._dragging = None  # indice do keyframe sendo arrastado
        self._pad = 20
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setMouseTracking(True)
        if self._item.volume_keyframes:
            self._item.volume_keyframes.sort(key=lambda k: k.get("time", 0.0))

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("KEYFRAMES DE VOLUME")
        lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt; font-weight: bold;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        btn_add = QPushButton("+ Add")
        btn_add.setFixedSize(40, 18)
        btn_add.setStyleSheet(f"background: {C['border']}; color: {C['text']}; font-size: 8pt; border-radius: 3px;")
        btn_add.clicked.connect(self._add_mid)
        hdr.addWidget(btn_add)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedSize(40, 18)
        btn_reset.setStyleSheet(f"background: {C['border']}; color: {C['red']}; font-size: 8pt; border-radius: 3px;")
        btn_reset.clicked.connect(self._reset)
        hdr.addWidget(btn_reset)
        layout.addLayout(hdr)

        # Info
        info = QLabel("Duplo-click = add | Botão direito = remover")
        info.setStyleSheet(f"color: {C['text3']}; font-size: 7pt;")
        layout.addWidget(info)

    @property
    def keyframes(self):
        return self._item.volume_keyframes

    # ============================================================
    # PAINT
    # ============================================================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height() - 30  # desconta header
        pad = self._pad
        draw_w = w - pad * 2
        draw_h = h - pad
        dur = self._item.duration or 1.0
        y_offset = 30  # offset pelo header

        # Fundo
        painter.fillRect(QRectF(0, y_offset, w, h), QColor(28, 46, 74, 140))

        # Grid horizontal
        painter.setPen(QPen(QColor(C["border"]), 1, Qt.DashLine))
        for val in [0.0, 0.5, 1.0, 1.5, 2.0]:
            y = y_offset + pad + draw_h * (1 - val / 2.0)
            painter.drawLine(QPointF(pad, y), QPointF(w - pad, y))
            painter.setPen(QPen(QColor(C["text3"])))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(QPointF(2, y + 4), f"{int(val*100)}%")
            painter.setPen(QPen(QColor(C["border"]), 1, Qt.DashLine))

        # Grid vertical
        step = max(1, int(dur / 5))
        for t in range(0, int(dur) + 1, step):
            x = pad + (t / dur) * draw_w
            painter.drawLine(QPointF(x, y_offset + pad), QPointF(x, y_offset + pad + draw_h))
            painter.setPen(QPen(QColor(C["text3"])))
            painter.drawText(QPointF(x - 4, y_offset + pad + draw_h + 12), f"{t}s")
            painter.setPen(QPen(QColor(C["border"]), 1, Qt.DashLine))

        # Curva
        kfs = sorted(self._item.volume_keyframes, key=lambda k: k["time"])
        if len(kfs) >= 2:
            path = QPainterPath()
            first = True
            for kf in kfs:
                x = pad + (kf["time"] / dur) * draw_w
                y = y_offset + pad + draw_h * (1 - kf["value"] / 2.0)
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)

            # Fill
            fill_path = QPainterPath(path)
            last_x = pad + draw_w
            fill_path.lineTo(last_x, y_offset + pad + draw_h)
            fill_path.lineTo(pad, y_offset + pad + draw_h)
            fill_path.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(10, 200, 185, 40)))
            painter.drawPath(fill_path)

            # Line
            painter.setPen(QPen(QColor(C["cyan"]), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        # Pontos
        for i, kf in enumerate(kfs):
            x = pad + (kf["time"] / dur) * draw_w
            y = y_offset + pad + draw_h * (1 - kf["value"] / 2.0)
            r = 6 if self._dragging == i else 5

            painter.setPen(QPen(QColor("#ffffff"), 1))
            color = QColor("#00ffee") if self._dragging == i else QColor(C["cyan"])
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), r, r)

            # Tooltip valor
            painter.setPen(QPen(QColor(C["text"])))
            painter.setFont(QFont("Consolas", 7))
            painter.drawText(QPointF(x - 10, y - 10), f"{kf['value']*100:.0f}%")

        painter.end()

    # ============================================================
    # MOUSE
    # ============================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._find_nearest(event.position())
            if idx is not None:
                self._dragging = idx
                self.update()
            event.accept()
        elif event.button() == Qt.RightButton:
            # Remover ponto
            idx = self._find_nearest(event.position(), threshold=15)
            if idx is not None:
                self._item.volume_keyframes.pop(idx)
                self._normalize_keyframes()
                self.changed.emit(True)
                self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging is not None:
            t, v = self._pos_to_tv(event.position())
            kf = self._item.volume_keyframes[self._dragging]
            kf["time"] = round(t, 2)
            kf["value"] = round(v, 3)
            self._normalize_keyframes()
            self._dragging = self._item.volume_keyframes.index(kf)
            self.changed.emit(False)
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._dragging is not None:
            self._dragging = None
            self.changed.emit(True)
            self.update()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """Double-click = adicionar keyframe."""
        if event.button() == Qt.LeftButton:
            t, v = self._pos_to_tv(event.position())
            self._item.volume_keyframes.append({"time": round(t, 2), "value": round(v, 3)})
            self._normalize_keyframes()
            self.changed.emit(True)
            self.update()
            event.accept()

    # ============================================================
    # HELPERS
    # ============================================================

    def _pos_to_tv(self, pos):
        w = self.width()
        h = self.height() - 30
        pad = self._pad
        draw_w = w - pad * 2
        draw_h = h - pad
        dur = self._item.duration or 1.0

        t = max(0, min(dur, ((pos.x() - pad) / draw_w) * dur))
        v = max(0, min(2.0, (1 - (pos.y() - 30 - pad) / draw_h) * 2.0))
        return t, v

    def _find_nearest(self, pos, threshold=12):
        w = self.width()
        h = self.height() - 30
        pad = self._pad
        draw_w = w - pad * 2
        draw_h = h - pad
        dur = self._item.duration or 1.0

        best_i, best_dist = None, threshold
        for i, kf in enumerate(self._item.volume_keyframes):
            kx = pad + (kf["time"] / dur) * draw_w
            ky = 30 + pad + draw_h * (1 - kf["value"] / 2.0)
            dist = ((pos.x() - kx) ** 2 + (pos.y() - ky) ** 2) ** 0.5
            if dist < best_dist:
                best_i, best_dist = i, dist
        return best_i

    def _normalize_keyframes(self):
        self._item.volume_keyframes.sort(key=lambda k: k.get("time", 0.0))

    def _add_mid(self):
        dur = self._item.duration
        self._item.volume_keyframes.append({"time": round(dur / 2, 2), "value": 1.0})
        self._normalize_keyframes()
        self.changed.emit(True)
        self.update()

    def _reset(self):
        self._item.volume_keyframes = [
            {"time": 0.0, "value": 1.0},
            {"time": self._item.duration, "value": 1.0},
        ]
        self._normalize_keyframes()
        self.changed.emit(True)
        self.update()
