"""Track Item - QGraphicsItem para items de audio/fx nas tracks."""

from pathlib import Path
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPainter

from makevid.qt.theme import C


class TrackGraphicsItem(QGraphicsRectItem):
    """Item genérico em qualquer track (audio, voice, sfx, music, fx)."""

    def __init__(self, track_item, x, y, w, h, color):
        super().__init__(x + 1, y + 2, w - 2, h - 4)
        self.track_item = track_item
        self._color = QColor(color)
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._waveform_path = None
        self._hovered = False

        # Visual
        self.setPen(QPen(self._color, 1))
        self.setBrush(QBrush(QColor("#0a1520")))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

        # Label no topo
        name = track_item.params.get("block_name", track_item.name)[:20]
        self._label = QGraphicsTextItem(name, self)
        self._label.setFont(QFont("Segoe UI", 7, QFont.Bold))
        self._label.setDefaultTextColor(QColor("#ffffff"))
        self._label.setPos(x + 4, y + 1)

        # Trim handles
        self._left_handle = QGraphicsRectItem(x, y + 2, 4, h - 4, self)
        self._left_handle.setPen(QPen(Qt.NoPen))
        self._left_handle.setBrush(QBrush(self._color))

        self._right_handle = QGraphicsRectItem(x + w - 4, y + 2, 4, h - 4, self)
        self._right_handle.setPen(QPen(Qt.NoPen))
        self._right_handle.setBrush(QBrush(self._color))

        # Gerar waveform se tem arquivo
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
        """Override paint para desenhar waveform linha a linha como no antigo."""
        super().paint(painter, option, widget)

        x = self._x + 4
        mid_y = self._y + self._h / 2
        amp = (self._h - 8) / 2 - 2
        w = self._w - 8

        if hasattr(self, '_waveform_data') and self._waveform_data is not None and len(self._waveform_data) > 1:
            import numpy as np
            data = self._waveform_data
            peak = max(abs(data.max()), abs(data.min()), 0.01)
            data_norm = data / peak

            if self._hovered:
                pen = QPen(self._color, 1.5)
            else:
                pen = QPen(QColor("#1a3a3a"), 1)
            painter.setPen(pen)

            points = min(len(data_norm) - 1, w)
            for i in range(points):
                y1 = mid_y - data_norm[i] * amp
                y2 = mid_y - data_norm[i + 1] * amp
                painter.drawLine(int(x + i), int(y1), int(x + i + 1), int(y2))
        elif w > 4:
            # Linha tracejada central se nao tem waveform
            pen = QPen(self._color if self._hovered else QColor("#1a3a3a"), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(x), int(mid_y), int(x + w), int(mid_y))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setPen(QPen(QColor("#00ffee"), 2))
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
        self.setPen(QPen(self._color, 1))
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)
