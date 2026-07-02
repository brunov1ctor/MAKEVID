"""Track Item - QGraphicsItem para items de audio/fx nas tracks."""

from pathlib import Path
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainterPath, QPainter,
    QLinearGradient
)

from makevid.qt.theme import C


class TrackGraphicsItem(QGraphicsItem):
    """Item genérico em qualquer track (audio, voice, sfx, music)."""

    def __init__(self, track_item, x, y, w, h, color, selected=False):
        super().__init__()
        self.track_item = track_item
        self._color = QColor(color)
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._hovered = False
        self._selected = selected
        self._waveform_data = None

        self.setAcceptHoverEvents(True)
        self.setZValue(2)

        if track_item.file_path and Path(track_item.file_path).exists():
            self._build_waveform()

    def _build_waveform(self):
        try:
            from makevid.core.audio_utils import read_audio_mono
            import numpy as np

            audio, sr = read_audio_mono(self.track_item.file_path)
            if len(audio) < 10:
                return

            w = max(4, self._w - 12)
            if len(audio) < w:
                self._waveform_data = np.interp(
                    np.linspace(0, len(audio) - 1, w),
                    np.arange(len(audio)), audio)
            else:
                block_size = max(1, len(audio) // w)
                result = np.zeros(w)
                for i in range(int(w)):
                    start = i * block_size
                    end = min(start + block_size, len(audio))
                    block = audio[start:end]
                    if len(block) > 0:
                        result[i] = block[np.argmax(np.abs(block))]
                self._waveform_data = result
        except Exception:
            self._waveform_data = None

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        x = self._x + 2
        y = self._y + 3
        w = self._w - 4
        h = self._h - 6
        if w < 2 or h < 2:
            return

        radius = 6.0
        c = self._color

        # Fundo
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)

        top = QColor(c.red(), c.green(), c.blue(), 80 if self._hovered else 55)
        bot = QColor(c.red(), c.green(), c.blue(), 50 if self._hovered else 30)
        grad = QLinearGradient(x, y, x, y + h)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bot)
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        # Borda
        border = QColor(c)
        border.setAlpha(160 if self._hovered else 80)
        painter.setPen(QPen(border, 1.2 if self._selected else 0.8))
        painter.drawPath(path)

        # Highlight seleção
        if self._selected:
            painter.setPen(QPen(QColor(255, 255, 255, 70), 1.5))
            painter.drawPath(path)

        # Highlight topo
        ref = QPainterPath()
        ref.addRoundedRect(QRectF(x + radius, y + 0.5, w - radius * 2, h * 0.25), 3, 3)
        ref_grad = QLinearGradient(0, y, 0, y + h * 0.25)
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, 20))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(ref, QBrush(ref_grad))

        # Trim handles
        handle_c = QColor(c)
        handle_c.setAlpha(180)
        lh = QPainterPath()
        lh.addRoundedRect(QRectF(x, y, 4, h), radius, 2)
        painter.fillPath(lh, handle_c)
        rh = QPainterPath()
        rh.addRoundedRect(QRectF(x + w - 4, y, 4, h), 2, radius)
        painter.fillPath(rh, handle_c)

        # Waveform
        wx = x + 6
        mid_y = y + h / 2
        amp = max(1, (h - 10) / 2)
        ww = w - 12

        if self._waveform_data is not None and len(self._waveform_data) > 1:
            import numpy as np
            data = self._waveform_data
            peak = max(abs(data.max()), abs(data.min()), 0.01)
            data_norm = data / peak
            wc = QColor(c)
            wc.setAlpha(180 if self._hovered else 110)
            painter.setPen(QPen(wc, 1.0))
            points = min(len(data_norm) - 1, int(ww))
            for i in range(points):
                y1 = mid_y - data_norm[i] * amp
                y2 = mid_y - data_norm[i + 1] * amp
                painter.drawLine(int(wx + i), int(y1), int(wx + i + 1), int(y2))
        else:
            dc = QColor(c)
            dc.setAlpha(60)
            painter.setPen(QPen(dc, 1, Qt.DashLine))
            painter.drawLine(int(wx), int(mid_y), int(wx + ww), int(mid_y))

        # Label
        painter.setPen(QPen(QColor(255, 255, 255, 200)))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        name = self.track_item.params.get("block_name", self.track_item.name)[:22]
        painter.drawText(QRectF(x + 6, y, w - 12, h), Qt.AlignVCenter | Qt.AlignLeft, name)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        local_x = event.pos().x() - self._x
        if local_x <= 6 or (self._w - local_x) <= 6:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)
