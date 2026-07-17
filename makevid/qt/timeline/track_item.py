"""Track Item - Item de audio/fx/voice/sfx/music na timeline."""

import logging
from pathlib import Path
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainterPath, QPainter, QLinearGradient,
    QConicalGradient, QPainterPathStroker
)
from makevid.qt.theme import C
from makevid.qt.timeline.clip_item import Z_AUDIO_ITEM, ITEM_PAD_X, ITEM_PAD_Y

_log = logging.getLogger("timeline")


class TrackGraphicsItem(QGraphicsItem):

    def __init__(self, track_item, x, y, w, h, color, selected=False, group_names=None):
        super().__init__()
        self.track_item = track_item
        self._color = QColor(color)
        self._w = w
        self._h = h
        self._hovered = False
        self._selected = selected
        self._waveform = None
        self._group_items = group_names or [track_item]

        import random
        self._beam_phase = random.uniform(0, 360)

        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(False)   # hover gerenciado pelo HoverController
        self.setZValue(Z_AUDIO_ITEM)
        self.setPos(x, y)

        if track_item.file_path and Path(track_item.file_path).exists():
            self._load_waveform()

    def _load_waveform(self):
        try:
            import soundfile as sf
            import numpy as np
            raw, sr = sf.read(self.track_item.file_path, dtype="float32")
            data = np.array(raw, copy=True)
            if len(data.shape) > 1:
                data = data.mean(axis=1)

            offset_sec = float(getattr(self.track_item, 'file_offset', 0.0))
            if offset_sec > 0:
                data = data[int(offset_sec * sr):]

            file_dur = float((getattr(self.track_item, 'params', {}) or {}).get('file_duration', 0.0))
            trunc_dur = file_dur if file_dur > 0 else float(self.track_item.duration)
            max_samples = int(trunc_dur * sr)
            if max_samples > 0 and len(data) > max_samples:
                data = data[:max_samples]

            muted = getattr(self.track_item, 'muted_regions', [])
            if muted:
                keep, prev = [], 0
                for region in sorted(muted, key=lambda r: r['start']):
                    ca = max(0, min(int(float(region['start']) * sr), len(data)))
                    cb = max(ca, min(int(float(region['end']) * sr), len(data)))
                    if ca > prev:
                        keep.append(data[prev:ca])
                    prev = cb
                if prev < len(data):
                    keep.append(data[prev:])
                data = np.concatenate(keep) if keep else np.array([], dtype=np.float32)

            if len(data) < 10:
                return

            n = max(4, self._w - 12)
            if len(data) < n:
                self._waveform = np.interp(
                    np.linspace(0, len(data) - 1, n),
                    np.arange(len(data)), data)
            else:
                bs = max(1, len(data) // n)
                rms_vals = np.array([
                    float(np.sqrt(np.mean(data[i*bs:i*bs+bs]**2))) if len(data[i*bs:i*bs+bs]) else 1e-9
                    for i in range(int(n))
                ])
                rms_vals = np.maximum(rms_vals, 1e-9)
                db = 20 * np.log10(rms_vals)
                db_floor, db_ceil = -60.0, max(db.max(), -59.0)
                self._waveform = np.clip((db - db_floor) / (db_ceil - db_floor), 0.0, 1.0)
        except Exception:
            self._waveform = None

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
        x = ITEM_PAD_X
        y = ITEM_PAD_Y
        w = self._w - ITEM_PAD_X * 2
        h = self._h - ITEM_PAD_Y * 2
        if w < 2 or h < 2:
            return

        c = self._color
        r = 6.0

        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), r, r)

        painter.fillPath(path, QBrush(QColor(18, 18, 32)))

        a_top = 220 if self._selected else (208 if self._hovered else 190)
        a_bot = 185 if self._selected else (170 if self._hovered else 150)
        grad = QLinearGradient(x, y, x, y + h)
        grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), a_top))
        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), a_bot))
        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(grad))

        if self._selected:
            self._paint_beam_border(painter, path, x, y, w, h)
        elif self._hovered:
            bdr = QColor(c).lighter(120)
            bdr.setAlpha(230)
            painter.setPen(QPen(bdr, 1.8))
            painter.drawPath(path)
        else:
            bdr = QColor(c)
            bdr.setAlpha(140)
            painter.setPen(QPen(bdr, 1.0))
            painter.drawPath(path)

        ref = QPainterPath()
        ref.addRoundedRect(QRectF(x + r, y + 0.5, w - r * 2, h * 0.25), 3, 3)
        rg = QLinearGradient(0, y, 0, y + h * 0.25)
        rg.setColorAt(0.0, QColor(255, 255, 255, 22))
        rg.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.fillPath(ref, QBrush(rg))

        hc = QColor(c)
        hc.setAlpha(210)
        lh = QPainterPath()
        lh.addRoundedRect(QRectF(x, y, 4, h), r, 2)
        painter.fillPath(lh, hc)
        rh = QPainterPath()
        rh.addRoundedRect(QRectF(x + w - 4, y, 4, h), 2, r)
        painter.fillPath(rh, hc)

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

        self._draw_volume_keyframes(painter, x, y, w, h)

        pad = max(2, int(h * 0.06))
        badge_sz = max(10, min(16, int(h * 0.22)))
        icon_sz  = max(10, min(18, int(h * 0.28)))
        name_min = 8

        total = h - pad * 2
        show_name  = total >= name_min
        show_icon  = total >= icon_sz + name_min + 2
        show_badge = total >= icon_sz + name_min + badge_sz + 4

        icon_top  = y + h - pad - icon_sz
        badge_top = y + pad
        name_top  = y + pad + (badge_sz + 2 if show_badge else 0)
        name_bot  = icon_top - 2 if show_icon else (y + h - pad)
        name_h    = max(name_min, name_bot - name_top)

        if show_name:
            painter.save()
            painter.setPen(QPen(QColor(255, 255, 255, 215)))
            painter.setFont(QFont("Segoe UI", max(6, min(8, int(h * 0.14))), QFont.Bold))
            name = self.track_item.params.get("block_name", self.track_item.name)[:22]
            painter.drawText(QRectF(x + 4, name_top, w - 8, name_h),
                             Qt.AlignHCenter | Qt.AlignVCenter, name)
            painter.restore()

        if show_icon:
            self._draw_layer_icons(painter, x, y, w, h, icon_sz, pad)

        if show_badge:
            bx = x + 5
            by = y + pad
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawRoundedRect(QRectF(bx, by, badge_sz, badge_sz), 3, 3)
            painter.setPen(QPen(QColor(255, 255, 255, 220)))
            painter.setFont(QFont("Segoe UI", max(5, badge_sz - 5), QFont.Bold))
            painter.drawText(QRectF(bx, by, badge_sz, badge_sz), Qt.AlignCenter, str(len(self._group_items)))
            painter.restore()

    def _draw_volume_keyframes(self, painter: QPainter, x, y, w, h):
        kfs = getattr(self.track_item, "volume_keyframes", None)
        if not kfs or len(kfs) < 2:
            return

        dur = max(0.001, float(getattr(self.track_item, "duration", 1.0) or 1.0))
        pad_x = 6
        top = y + 6
        bottom = y + h - 6
        band_h = max(8, bottom - top)
        draw_w = max(1, w - pad_x * 2)

        pts = []
        for kf in sorted(kfs, key=lambda k: k.get("time", 0.0)):
            ratio = max(0.0, min(1.0, float(kf.get("time", 0.0)) / dur))
            value = max(0.0, min(2.0, float(kf.get("value", 1.0)))) / 2.0
            px = x + pad_x + ratio * draw_w
            py = bottom - value * band_h
            pts.append((px, py, value))

        if len(pts) < 2:
            return

        path = QPainterPath()
        path.moveTo(pts[0][0], pts[0][1])
        for px, py, _ in pts[1:]:
            path.lineTo(px, py)

        fill_path = QPainterPath(path)
        fill_path.lineTo(pts[-1][0], bottom)
        fill_path.lineTo(pts[0][0], bottom)
        fill_path.closeSubpath()

        accent = QColor(self._color)
        accent.setAlpha(70 if not self._hovered else 95)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(accent))
        painter.drawPath(fill_path)

        line = QColor(C["cyan"])
        line.setAlpha(230 if self._selected else 200)
        painter.setPen(QPen(line, 1.6))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setFont(QFont("Consolas", 6, QFont.Bold))
        for px, py, value in pts:
            r = 4
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            painter.setBrush(QBrush(QColor(self._color).lighter(120)))
            painter.drawEllipse(QRectF(px - r, py - r, r * 2, r * 2))

    def _draw_layer_icons(self, painter, x, y, w, h, sz, pad_bot=3):
        from makevid.qt.timeline.track_icons import infer_icon_key
        _EMOJI = {
            "mic":    "🎧",
            "tts":    "🗣",
            "import": "📂",
            "music":  "🎵",
            "sfx":    "🔊",
            "voice":  "🎤",
            "rec":    "⏺",
            "default":"🎶",
        }
        iy = y + h - pad_bot - sz
        ix = x + 4
        painter.save()
        painter.setFont(QFont("Segoe UI Emoji", max(6, sz - 3)))
        painter.setPen(QPen(QColor(255, 255, 255, 220)))
        for ti in self._group_items:
            if ix + sz > x + w - 4:
                break
            key = infer_icon_key(ti.name, getattr(ti, 'track', ''), ti.params.get('source_type', ''))
            emoji = _EMOJI.get(key, _EMOJI["default"])
            painter.drawText(QRectF(ix, iy, sz, sz), Qt.AlignCenter, emoji)
            ix += sz + 2
        painter.restore()

    def _paint_beam_border(self, painter, path, x, y, w, h):
        from makevid.qt.timeline.clip_item import ClipGraphicsItem
        angle = (ClipGraphicsItem._beam_angle + getattr(self, '_beam_phase', 0.0)) % 360

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
