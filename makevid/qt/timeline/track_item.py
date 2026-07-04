"""Track Item - Item de audio/fx/voice/sfx/music na timeline."""

import logging
from pathlib import Path
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainterPath, QPainter, QLinearGradient
)
from makevid.qt.theme import C


_log = logging.getLogger("timeline")


class TrackGraphicsItem(QGraphicsItem):

    def __init__(self, track_item, x, y, w, h, color, selected=False):
        super().__init__()
        self.track_item = track_item
        self._color = QColor(color)
        self._x, self._y, self._w, self._h = x, y, w, h
        self._hovered = False
        self._selected = selected
        self._waveform = None
        self._last_logged_state = None
        _log.debug(f"TrackGraphicsItem created id={track_item.id} color={QColor(color).name()} selected={selected} x={x:.0f} y={y:.0f} w={w:.0f} h={h:.0f}")

        # Nunca deixar o Qt gerenciar seleção — evita override de cores
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

        if track_item.file_path and Path(track_item.file_path).exists():
            self._load_waveform()

    def _load_waveform(self):
        try:
            from makevid.core.audio_utils import read_audio_mono
            import numpy as np
            audio, _ = read_audio_mono(self.track_item.file_path)
            if len(audio) < 10:
                return
            n = max(4, self._w - 12)
            if len(audio) < n:
                self._waveform = np.interp(
                    np.linspace(0, len(audio) - 1, n),
                    np.arange(len(audio)), audio)
            else:
                bs = max(1, len(audio) // n)
                self._waveform = np.array([
                    audio[i * bs: i * bs + bs][
                        __import__('numpy').argmax(
                            __import__('numpy').abs(audio[i * bs: i * bs + bs])
                        )
                    ] if len(audio[i * bs: i * bs + bs]) else 0.0
                    for i in range(int(n))
                ])
        except Exception:
            self._waveform = None

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        state = (self._selected, self._hovered)
        if state != self._last_logged_state:
            a_top = 220 if self._selected else (208 if self._hovered else 190)
            a_bot = 185 if self._selected else (170 if self._hovered else 150)
            bdr_w = 2.5 if self._selected else (1.8 if self._hovered else 1.0)
            bdr_a = 255 if self._selected else (220 if self._hovered else 140)
            c_bright = self._color
            _log.debug(
                f"style id={self.track_item.id} "
                f"selected={self._selected} hovered={self._hovered} "
                f"grad_top=({c_bright.name()},a={a_top}) "
                f"grad_bot=({self._color.name()},a={a_bot}) "
                f"border=(w={bdr_w},a={bdr_a})"
            )
            self._last_logged_state = state

        x = self._x + 2
        y = self._y + 3
        w = self._w - 4
        h = self._h - 6
        if w < 2 or h < 2:
            return

        c = self._color
        r = 6.0

        # --- fundo ---
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), r, r)

        # fundo sólido escuro primeiro
        painter.fillPath(path, QBrush(QColor(18, 18, 32)))

        # camada de cor da track — sempre visível
        a_top = 220 if self._selected else (208 if self._hovered else 190)
        a_bot = 185 if self._selected else (170 if self._hovered else 150)
        c_bright = c
        grad = QLinearGradient(x, y, x, y + h)
        grad.setColorAt(0.0, QColor(c_bright.red(), c_bright.green(), c_bright.blue(), a_top))
        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), a_bot))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        # --- borda ---
        bdr = QColor(c)
        if self._selected:
            bdr.setAlpha(255)
            painter.setPen(QPen(bdr, 2.5))
        elif self._hovered:
            bdr = QColor(c).lighter(120)
            bdr.setAlpha(230)
            painter.setPen(QPen(bdr, 1.8))
        else:
            bdr.setAlpha(140)
            painter.setPen(QPen(bdr, 1.0))
        painter.drawPath(path)

        # --- reflexo topo ---
        ref = QPainterPath()
        ref.addRoundedRect(QRectF(x + r, y + 0.5, w - r * 2, h * 0.25), 3, 3)
        rg = QLinearGradient(0, y, 0, y + h * 0.25)
        rg.setColorAt(0.0, QColor(255, 255, 255, 22))
        rg.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(ref, QBrush(rg))

        # --- handles laterais ---
        hc = QColor(c)
        hc.setAlpha(210)
        lh = QPainterPath()
        lh.addRoundedRect(QRectF(x, y, 4, h), r, 2)
        painter.fillPath(lh, hc)
        rh = QPainterPath()
        rh.addRoundedRect(QRectF(x + w - 4, y, 4, h), 2, r)
        painter.fillPath(rh, hc)

        # --- waveform ---
        wx = x + 6
        mid = y + h / 2
        amp = max(1, (h - 10) / 2)
        ww = w - 12

        if self._waveform is not None and len(self._waveform) > 1:
            import numpy as np
            data = self._waveform
            peak = max(abs(data.max()), abs(data.min()), 0.01)
            norm = data / peak
            wc = QColor(c)
            wc.setAlpha(180 if self._hovered else 130)
            painter.setPen(QPen(wc, 1.0))
            pts = min(len(norm) - 1, int(ww))
            for i in range(pts):
                painter.drawLine(
                    int(wx + i), int(mid - norm[i] * amp),
                    int(wx + i + 1), int(mid - norm[i + 1] * amp)
                )
        else:
            dc = QColor(c)
            dc.setAlpha(75)
            painter.setPen(QPen(dc, 1, Qt.DashLine))
            painter.drawLine(int(wx), int(mid), int(wx + ww), int(mid))

        # --- label ---
        painter.setPen(QPen(QColor(255, 255, 255, 215)))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        name = self.track_item.params.get("block_name", self.track_item.name)[:22]
        painter.drawText(QRectF(x + 6, y, w - 12, h), Qt.AlignVCenter | Qt.AlignLeft, name)

    def hoverEnterEvent(self, event):
        self._hovered = True
        _log.debug(f"hover_enter id={self.track_item.id}")
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        lx = event.pos().x() - self._x
        self.setCursor(Qt.SizeHorCursor if lx <= 6 or (self._w - lx) <= 6 else Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        _log.debug(f"hover_leave id={self.track_item.id}")
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)
