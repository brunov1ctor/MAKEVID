"""Track Item - QGraphicsItem para items de audio/fx nas tracks."""

from pathlib import Path
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainterPath, QPainter,
    QLinearGradient
)

from makevid.qt.theme import C


class TrackGraphicsItem(QGraphicsRectItem):
    """Item genérico em qualquer track (audio, voice, sfx, music, fx)."""

    def __init__(self, track_item, x, y, w, h, color, selected=False):
        super().__init__(x + 1, y + 2, w - 2, h - 4)
        self.track_item = track_item
        self._color = QColor(color)
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._waveform_path = None
        self._hovered = False
        self._selected = selected

        self.setPen(Qt.NoPen)
        self.setBrush(Qt.NoBrush)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

        # Label
        name = track_item.params.get("block_name", track_item.name)[:20]
        self._label = QGraphicsTextItem(name, self)
        self._label.setFont(QFont("Segoe UI", 7, QFont.Bold))
        self._label.setDefaultTextColor(QColor(255, 255, 255, 200))
        self._label.setPos(x + 8, y + 1)

        # Trim handles
        handle_c = QColor(self._color)
        handle_c.setAlpha(180)
        self._left_handle = QGraphicsRectItem(x, y + 2, 4, h - 4, self)
        self._left_handle.setPen(QPen(Qt.NoPen))
        self._left_handle.setBrush(QBrush(handle_c))

        self._right_handle = QGraphicsRectItem(x + w - 4, y + 2, 4, h - 4, self)
        self._right_handle.setPen(QPen(Qt.NoPen))
        self._right_handle.setBrush(QBrush(handle_c))

        if track_item.file_path and Path(track_item.file_path).exists():
            self._build_waveform()

    def _build_waveform(self):
        """Carrega dados de waveform para renderizar no paint."""
        try:
            from makevid.core.audio_utils import read_audio_mono
            import numpy as np

            audio, sr = read_audio_mono(self.track_item.file_path)
            if len(audio) < 10:
                return

            w = max(4, self._w - 8)

            if len(audio) < w:
                self._waveform_data = np.interp(
                    np.linspace(0, len(audio) - 1, w),
                    np.arange(len(audio)), audio)
            else:
                block_size = max(1, len(audio) // w)
                result = np.zeros(w)
                for i in range(w):
                    start = i * block_size
                    end = min(start + block_size, len(audio))
                    block = audio[start:end]
                    if len(block) > 0:
                        result[i] = block[np.argmax(np.abs(block))]
                self._waveform_data = result
        except Exception:
            self._waveform_data = None

    def paint(self, painter: QPainter, option, widget=None):
        x, y, w, h = self._x + 2, self._y + 3, self._w - 4, self._h - 6
        radius = 6.0

        # ── Fundo arredondado com gradiente ──────────────────────────────────
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)

        c = QColor(self._color)
        top = QColor(c.red(), c.green(), c.blue(), 55 if not self._hovered else 80)
        bot = QColor(c.red(), c.green(), c.blue(), 30 if not self._hovered else 50)
        grad = QLinearGradient(x, y, x, y + h)
        grad.setColorAt(0.0, top)
        grad.setColorAt(1.0, bot)
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        # Borda translúcida
        border = QColor(self._color)
        border.setAlpha(140 if self._hovered else 70)
        painter.setPen(QPen(border, 1.0))
        painter.drawPath(path)

        # Highlight de seleção
        if self._selected:
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
            painter.drawPath(path)

        # Highlight topo
        ref = QPainterPath()
        ref.addRoundedRect(QRectF(x + radius, y + 0.5, w - radius * 2, h * 0.25), 3, 3)
        ref_grad = QLinearGradient(0, y, 0, y + h * 0.25)
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, 18))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(ref, QBrush(ref_grad))

        # ── Waveform ────────────────────────────────────────────────────────────
        wx = x + 6
        mid_y = y + h / 2
        amp = (h - 10) / 2
        ww = w - 12

        if hasattr(self, '_waveform_data') and self._waveform_data is not None and len(self._waveform_data) > 1:
            import numpy as np
            data = self._waveform_data
            peak = max(abs(data.max()), abs(data.min()), 0.01)
            data_norm = data / peak
            wc = QColor(self._color)
            wc.setAlpha(160 if self._hovered else 100)
            painter.setPen(QPen(wc, 1.0))
            points = min(len(data_norm) - 1, int(ww))
            for i in range(points):
                y1 = mid_y - data_norm[i] * amp
                y2 = mid_y - data_norm[i + 1] * amp
                painter.drawLine(int(wx + i), int(y1), int(wx + i + 1), int(y2))
        else:
            dc = QColor(self._color)
            dc.setAlpha(60)
            painter.setPen(QPen(dc, 1, Qt.DashLine))
            painter.drawLine(int(wx), int(mid_y), int(wx + ww), int(mid_y))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        """Cursor de resize nas bordas."""
        local_x = event.pos().x() - self.rect().x()
        w = self.rect().width()
        if local_x <= 6 or (w - local_x) <= 6:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)
