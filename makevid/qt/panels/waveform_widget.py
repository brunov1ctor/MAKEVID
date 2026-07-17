"""Widgets de visualização de forma de onda com eixo de dB."""

import logging
import numpy as np

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QPainterPath, QPolygon,
)

from makevid.qt.theme import C
from makevid.qt.panels.layer_audio_player import _prepare_audio_visual

_log = logging.getLogger(__name__)

# Escala fixa: 0 dB (topo) até -60 dB (base) — igual DAWs profissionais
_DB_FLOOR = -60.0
_DB_CEIL  =   0.0
_DB_RANGE =  60.0

def _db_to_y(db_val: float, h: int) -> int:
    """Converte valor dB para coordenada Y (0 = topo = 0 dB, h = base = -60 dB)."""
    ratio = (db_val - _DB_CEIL) / (_DB_FLOOR - _DB_CEIL)   # 0.0 → topo, 1.0 → base
    return int(ratio * h)

# Linhas principais do grid (db, cor_linha, mostrar_label)
_GRID_MAJOR = [
    (  0, QColor(255, 255, 255, 55), True),
    ( -3, QColor(220,  80,  80, 90), True),
    ( -6, QColor(220, 180,  60, 80), True),
    ( -9, QColor(180, 180,  60, 50), True),
    (-12, QColor(100, 200, 120, 75), True),
    (-15, QColor(140, 140, 140, 40), True),
    (-18, QColor( 80, 160, 220, 70), True),
    (-21, QColor(140, 140, 140, 35), True),
    (-24, QColor(140, 140, 140, 50), True),
    (-30, QColor(120, 120, 120, 40), True),
    (-36, QColor(120, 120, 120, 55), True),
    (-42, QColor(100, 100, 100, 35), True),
    (-48, QColor(100, 100, 100, 35), True),
    (-54, QColor( 90,  90,  90, 30), True),
    (-60, QColor( 80,  80,  80, 40), True),
]

# Linhas secundárias (pontilhadas, entre as principais)
_GRID_MINOR = [-1, -2, -4, -5, -7, -8, -10, -11, -13, -14, -16, -17,
               -19, -20, -22, -23, -25, -27, -33, -39, -45, -51, -57]


class _DbAxisWidget(QWidget):
    """Eixo Y de dB lateral — escala fixa 0 → -60 dB, igual DAWs."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(11, 18, 32, 200))
        p.setFont(QFont("Consolas", 6, QFont.Bold))
        for db_val, color, _ in _GRID_MAJOR:
            y = _db_to_y(db_val, h)
            p.setPen(QPen(color, 1))
            p.drawLine(w - 4, y, w, y)
            p.setPen(QPen(color.lighter(150)))
            label = "0" if db_val == 0 else str(db_val)
            p.drawText(0, y - 7, w - 5, 14, Qt.AlignRight | Qt.AlignVCenter, label)
        p.end()


class _WaveformWidget(QWidget):
    """Waveform com keyframes de volume, marcações de dB e modo de recorte."""

    keyframe_changed = Signal(bool)
    cut_requested    = Signal()
    selection_changed = Signal()

    def __init__(self, item, color, parent=None):
        super().__init__(parent)
        self._item   = item
        self._color  = QColor(color)
        self._waveform_data  = None
        self._playhead_ratio = -1
        self._dragging       = None
        self._cut_service    = None
        self._cut_dragging   = False
        self._cut_press_pos  = None
        self._cut_edge_drag  = None
        self._wip_end_preview = None
        self._peak_db        = None
        self._rms_db         = None
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._ensure_default_keyframes()
        self._load_waveform()

    _EDGE_HIT = 8

    # ── public ────────────────────────────────────────────────────────────────

    def set_cut_mode(self, service):
        self._cut_service    = service
        self._cut_dragging   = False
        self._cut_press_pos  = None
        self._wip_end_preview = None
        if service is None:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("Clique para criar keyframe | Arraste para ajustar | Botão direito remove")
        else:
            self.setCursor(Qt.CrossCursor)
            self.setToolTip("Clique e arraste para selecionar a região a recortar")
        self.update()

    def set_playhead(self, ratio):
        self._playhead_ratio = self._audio_ratio_to_visual(ratio)
        self.update()

    def set_peak_rms(self, peak_db: float | None, rms_db: float | None):
        """Atualiza os valores de Peak e RMS exibidos no badge durante a reprodução."""
        self._peak_db = peak_db
        self._rms_db  = rms_db
        self.update()

    def reload_waveform(self):
        self._load_waveform()
        self.update()

    # ── internal ──────────────────────────────────────────────────────────────

    def _hit_edge(self, x):
        if self._cut_service is None:
            return None
        return self._cut_service.hit_edge(x / max(1, self.width()), self._EDGE_HIT, self.width())

    def _ensure_default_keyframes(self):
        if self._item.volume_keyframes:
            self._item.volume_keyframes.sort(key=lambda k: k.get("time", 0.0))

    def _load_waveform(self):
        data, sr = _prepare_audio_visual(self._item)
        if data is None or len(data) < 10:
            return
        try:
            mono  = data.mean(axis=1) if len(data.shape) > 1 else data
            chunk = max(1, len(mono) // 400)
            rms_values = [
                max(float(np.sqrt(np.mean(mono[i:i+chunk] ** 2))), 1e-9)
                for i in range(0, len(mono), chunk)
            ]
            db = np.array([20 * np.log10(v) for v in rms_values])
            # escala fixa -60..0 dB — igual ao eixo lateral
            db = np.clip(db, _DB_FLOOR, _DB_CEIL)
            self._waveform_data = list((db - _DB_FLOOR) / _DB_RANGE)
        except Exception:
            _log.exception("Erro ao carregar waveform")
            self._waveform_data = None

    # ── ratio mapping ─────────────────────────────────────────────────────────

    def _get_all_muted_ratios(self):
        # usa file_duration se disponivel para converter segundos em ratios corretos
        file_dur = float((getattr(self._item, 'params', {}) or {}).get('file_duration', 0.0))
        dur = file_dur if file_dur > 0 else max(0.001, float(self._item.duration or 1.0))
        result = []
        for region in (getattr(self._item, 'muted_regions', []) or []):
            a = float(region['start']) / dur
            b = float(region['end'])   / dur
            if b > a:
                result.append((a, b))
        if self._cut_service is not None:
            result.extend(self._cut_service.get_selections())
        return sorted(result)

    def _kept_segments(self, muted_ratios):
        kept, prev = [], 0.0
        for a, b in muted_ratios:
            a, b = max(0.0, a), min(1.0, b)
            if a > prev:
                kept.append((prev, a))
            prev = max(prev, b)
        if prev < 1.0:
            kept.append((prev, 1.0))
        return kept

    def _audio_ratio_to_visual(self, ratio):
        if ratio < 0:
            return ratio
        muted = self._get_all_muted_ratios()
        if not muted:
            return ratio
        kept  = self._kept_segments(muted)
        total = sum(b - a for a, b in kept)
        if total <= 0:
            return ratio
        audio_pos = ratio * total
        acc = 0.0
        for vis_a, vis_b in kept:
            seg = vis_b - vis_a
            if audio_pos <= acc + seg:
                return vis_a + (audio_pos - acc)
            acc += seg
        return kept[-1][1]

    def _visual_ratio_to_audio(self, ratio):
        if ratio < 0:
            return ratio
        muted = self._get_all_muted_ratios()
        if not muted:
            return ratio
        kept  = self._kept_segments(muted)
        total = sum(b - a for a, b in kept)
        if total <= 0:
            return 0.0
        acc = 0.0
        for vis_a, vis_b in kept:
            seg = vis_b - vis_a
            if ratio <= vis_a:
                break
            if ratio <= vis_b:
                acc += ratio - vis_a
                break
            acc += seg
        return min(1.0, acc / total)

    # ── keyframe drawing ──────────────────────────────────────────────────────

    def _draw_keyframes(self, p, w, h):
        kfs = list(enumerate(self._item.volume_keyframes))
        if len(kfs) < 2:
            return
        dur    = max(0.001, float(self._item.duration or 1.0))
        pad_x  = 6
        bottom = h - 6
        band_h = max(8, bottom - 6)
        draw_w = max(1, w - pad_x * 2)
        sorted_kfs = sorted(kfs, key=lambda pair: pair[1]["time"])
        path, pts = QPainterPath(), []
        for idx, kf in sorted_kfs:
            ratio = max(0.0, min(1.0, float(kf.get("time", 0.0)) / dur))
            value = max(0.0, min(2.0, float(kf.get("value", 1.0)))) / 2.0
            x = pad_x + ratio * draw_w
            y = bottom - value * band_h
            pts.append((idx, x, y, value))
        if len(pts) < 2:
            return
        path.moveTo(pts[0][1], pts[0][2])
        for _, x, y, _ in pts[1:]:
            path.lineTo(x, y)
        fill = QPainterPath(path)
        fill.lineTo(pts[-1][1], bottom)
        fill.lineTo(pts[0][1],  bottom)
        fill.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(self._color.red(), self._color.green(), self._color.blue(), 42)))
        p.drawPath(fill)
        curve_color = QColor(self._color)
        curve_color.setAlpha(220)
        p.setPen(QPen(curve_color, 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        for idx, x, y, value in pts:
            active = self._dragging == idx
            r = 5 if active else 4
            p.setPen(QPen(QColor("#ffffff"), 1))
            p.setBrush(QBrush(QColor("#00ffee") if active else QColor(self._color)))
            p.drawEllipse(int(x) - r, int(y) - r, r * 2, r * 2)
            p.setPen(QPen(QColor(C["text"])))
            p.setFont(QFont("Consolas", 6))
            p.drawText(int(x) - 10, int(y) - 7, f"{value * 200:.0f}%")

    def _find_nearest_keyframe(self, pos, threshold=10):
        dur    = max(0.001, float(self._item.duration or 1.0))
        w, h   = self.width(), self.height()
        pad_x  = 6
        bottom = h - 6
        band_h = max(8, bottom - 6)
        draw_w = max(1, w - pad_x * 2)
        best, best_dist = None, threshold
        for idx, kf in enumerate(self._item.volume_keyframes):
            ratio = max(0.0, min(1.0, float(kf.get("time", 0.0)) / dur))
            value = max(0.0, min(2.0, float(kf.get("value", 1.0)))) / 2.0
            x = pad_x + ratio * draw_w
            y = bottom - value * band_h
            dist = ((pos.x() - x) ** 2 + (pos.y() - y) ** 2) ** 0.5
            if dist < best_dist:
                best, best_dist = idx, dist
        return best

    def _pos_to_kf(self, pos):
        w, h   = self.width(), self.height()
        pad_x  = 6
        bottom = h - 6
        band_h = max(8, bottom - 6)
        draw_w = max(1, w - pad_x * 2)
        dur    = max(0.001, float(self._item.duration or 1.0))
        t = max(0.0, min(dur, ((pos.x() - pad_x) / draw_w) * dur))
        v = max(0.0, min(2.0, (bottom - pos.y()) / band_h * 2.0))
        return t, v

    def _normalize_keyframes(self):
        self._item.volume_keyframes.sort(key=lambda k: k.get("time", 0.0))

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(11, 18, 32, 220))

        # Grid secundário (pontilhado, muito sutil)
        minor_pen = QPen(QColor(255, 255, 255, 10), 1, Qt.DotLine)
        p.setPen(minor_pen)
        for db_val in _GRID_MINOR:
            y = _db_to_y(db_val, h)
            p.drawLine(0, y, w, y)

        # Grid principal (linhas horizontais de dB)
        for db_val, color, _ in _GRID_MAJOR:
            y = _db_to_y(db_val, h)
            pen = QPen(color, 1)
            pen.setStyle(Qt.DashLine if db_val <= -24 else Qt.SolidLine)
            p.setPen(pen)
            p.drawLine(0, y, w, y)

        # Linhas verticais de tempo
        dur = max(0.001, float(self._item.duration or 1.0))
        step = 1.0 if dur <= 10 else (2.0 if dur <= 30 else 5.0)
        t = step
        p.setFont(QFont("Consolas", 6))
        while t < dur:
            x = int(t / dur * w)
            p.setPen(QPen(QColor(255, 255, 255, 18), 1))
            p.drawLine(x, 0, x, h)
            p.setPen(QPen(QColor(255, 255, 255, 55)))
            p.drawText(x + 2, h - 2, f"{t:.0f}s")
            t += step

        # Waveform — barras simétricas ancoradas no eixo de amplitude
        if self._waveform_data:
            n     = len(self._waveform_data)
            bar_w = max(1.0, w / n)
            try:
                vol_scale = min(2.0, max(0.0, float(self._item.params.get('volume', 100)) / 100.0))
            except (TypeError, ValueError):
                vol_scale = 1.0
            color_fill = QColor(self._color)
            color_fill.setAlpha(160)
            color_top  = QColor(self._color)
            color_top.setAlpha(220)
            p.setPen(Qt.NoPen)
            for i, amp in enumerate(self._waveform_data):
                # amp em [0,1] onde 1 = 0 dB, 0 = -60 dB
                # aplicar vol_scale no domínio dB: shift de amplitude
                scaled = min(1.0, amp * vol_scale)
                db_val = _DB_FLOOR + scaled * _DB_RANGE          # dB absoluto
                y_top  = _db_to_y(db_val, h)                     # pixel do pico
                y_bot  = h - y_top                               # espelho inferior
                x      = int(i * bar_w)
                bw     = max(1, int(bar_w) - 1)
                # barra inferior (espelho)
                p.setBrush(color_fill)
                p.drawRect(x, y_top, bw, max(1, y_bot - y_top))
                # linha de topo (destaque)
                p.setBrush(color_top)
                p.drawRect(x, y_top, bw, 1)
        else:
            p.setPen(QPen(QColor(self._color), 1))
            p.drawLine(0, h // 2, w, h // 2)

        self._draw_keyframes(p, w, h)

        # Regiões silenciadas
        for ra, rb in self._get_all_muted_ratios():
            xa, xb = int(ra * w), int(rb * w)
            p.fillRect(xa, 0, max(1, xb - xa), h, QColor(80, 80, 80, 100))
            p.setPen(QPen(QColor(160, 160, 160, 160), 1))
            p.drawLine(xa, 0, xa, h)
            p.drawLine(xb, 0, xb, h)

        # Modo de recorte
        if self._cut_service is not None:
            self._paint_cut_overlay(p, w, h)

        # Badge Peak / RMS
        if self._peak_db is not None or self._rms_db is not None:
            lines = []
            if self._peak_db is not None:
                clipping = self._peak_db >= -0.1
                peak_color = QColor(220, 60, 60) if clipping else QColor(220, 180, 60)
                lines.append((f"Pk {self._peak_db:+.1f}dB", peak_color))
            if self._rms_db is not None:
                lines.append((f"RMS {self._rms_db:+.1f}dB", QColor(100, 200, 120)))
            badge_w, badge_h = 88, 14 * len(lines) + 6
            bx = w - badge_w - 4
            by = 4
            p.fillRect(bx, by, badge_w, badge_h, QColor(8, 14, 26, 200))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1))
            p.drawRect(bx, by, badge_w - 1, badge_h - 1)
            p.setFont(QFont("Consolas", 7, QFont.Bold))
            for i, (text, color) in enumerate(lines):
                p.setPen(QPen(color))
                p.drawText(bx + 4, by + 4 + i * 14, badge_w - 8, 14,
                           Qt.AlignLeft | Qt.AlignVCenter, text)

        # Playhead
        if 0 <= self._playhead_ratio <= 1:
            px = int(self._playhead_ratio * w)
            p.setPen(QPen(QColor(C["playhead"]), 2))
            p.drawLine(px, 0, px, h)
            p.setBrush(QColor(C["playhead"]))
            p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygon([QPoint(px - 4, 0), QPoint(px + 4, 0), QPoint(px, 5)]))

    def _paint_cut_overlay(self, p, w, h):
        ws = max(1, w)
        for sel_a, sel_b in self._cut_service.get_selections():
            xa, xb = int(sel_a * ws), int(sel_b * ws)
            p.fillRect(xa, 0, xb - xa, h, QColor(220, 50, 50, 70))
            p.setPen(QPen(QColor(220, 50, 50, 110), 1))
            for x in range(xa - h, xb, 8):
                p.drawLine(x, h, x + h, 0)
            p.setPen(QPen(QColor(220, 50, 50, 220), 2))
            p.drawLine(xa, 0, xa, h)
            p.drawLine(xb, 0, xb, h)
        if self._cut_service.touches_start():
            p.fillRect(0, 0, 4, h, QColor(255, 200, 0, 200))
        if self._cut_service.touches_end():
            p.fillRect(w - 4, 0, 4, h, QColor(255, 200, 0, 200))
        wip_a, wip_b = self._cut_service.get_wip()
        if wip_a is not None and wip_b > wip_a:
            xa, xb = int(wip_a * ws), int(wip_b * ws)
            p.fillRect(xa, 0, xb - xa, h, QColor(220, 50, 50, 40))
            p.setPen(QPen(QColor(220, 50, 50, 160), 1, Qt.DashLine))
            p.drawLine(xa, 0, xa, h)
            p.drawLine(xb, 0, xb, h)
        pending = self._cut_service.get_pending_point()
        if pending is not None:
            px = int(pending * ws)
            p.setPen(QPen(QColor(255, 180, 0, 220), 2))
            p.drawLine(px, 0, px, h)
            p.setBrush(QColor(255, 180, 0, 200))
            p.setPen(Qt.NoPen)
            p.drawEllipse(px - 5, h // 2 - 5, 10, 10)
            p.setPen(QPen(QColor("#fff")))
            p.setFont(QFont("Consolas", 7))
            p.drawText(px + 4, 14, "A")
            if self._wip_end_preview is not None:
                bx = int(self._wip_end_preview * ws)
                xa, xb = min(px, bx), max(px, bx)
                p.fillRect(xa, 0, xb - xa, h, QColor(220, 50, 50, 40))
                p.setPen(QPen(QColor(220, 50, 50, 180), 2, Qt.DashLine))
                p.drawLine(bx, 0, bx, h)
                p.setBrush(QColor(220, 50, 50, 200))
                p.setPen(Qt.NoPen)
                p.drawEllipse(bx - 5, h // 2 - 5, 10, 10)
                p.setPen(QPen(QColor("#fff")))
                p.setFont(QFont("Consolas", 7))
                p.drawText(bx + 4, 14, "B")

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if self._cut_service is not None and event.button() == Qt.LeftButton:
            x    = event.position().x()
            edge = self._hit_edge(x)
            if edge is not None:
                self._cut_edge_drag = edge
                self._cut_service.begin_edge_drag(edge[0], edge[1])
                self._cut_press_pos = None
                self._cut_dragging  = False
            elif self._cut_service.get_pending_point() is not None:
                ratio = max(0.0, min(1.0, x / max(1, self.width())))
                self._wip_end_preview = ratio
                self._cut_press_pos   = x
                self._cut_dragging    = False
                self._cut_edge_drag   = None
            else:
                self._cut_press_pos = x
                self._cut_dragging  = False
                self._cut_edge_drag = None
            self.update()
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            idx = self._find_nearest_keyframe(event.position())
            if idx is None:
                t, v = self._pos_to_kf(event.position())
                new_kf = {"time": round(t, 2), "value": round(v, 3)}
                self._item.volume_keyframes.append(new_kf)
                self._normalize_keyframes()
                self._dragging = self._item.volume_keyframes.index(new_kf)
                self.keyframe_changed.emit(False)
            else:
                self._dragging = idx
            self.setCursor(Qt.SizeAllCursor)
            self.update()
            event.accept()
        elif event.button() == Qt.RightButton:
            idx = self._find_nearest_keyframe(event.position(), threshold=14)
            if idx is not None:
                self._item.volume_keyframes.pop(idx)
                self._normalize_keyframes()
                self.keyframe_changed.emit(True)
                self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._cut_service is not None:
            x = event.position().x()
            if self._cut_edge_drag is not None:
                self._cut_service.update_edge_drag(max(0.0, min(1.0, x / max(1, self.width()))))
                self.update()
                return
            if self._cut_press_pos is not None:
                dx = abs(x - self._cut_press_pos)
                if self._cut_service.get_pending_point() is not None:
                    self._wip_end_preview = max(0.0, min(1.0, x / max(1, self.width())))
                    self._cut_dragging    = True
                    self.update()
                elif not self._cut_dragging and dx > 4:
                    ratio = max(0.0, min(1.0, self._cut_press_pos / max(1, self.width())))
                    self._cut_service.begin_selection(ratio)
                    self._cut_dragging = True
                    self._cut_service.update_selection(max(0.0, min(1.0, x / max(1, self.width()))))
                    self.update()
                elif self._cut_dragging:
                    self._cut_service.update_selection(max(0.0, min(1.0, x / max(1, self.width()))))
                    self.update()
                    self.selection_changed.emit()
                return
            edge = self._hit_edge(x)
            self.setCursor(Qt.SizeHorCursor if edge else Qt.CrossCursor)
            return
        if self._dragging is not None:
            t, v = self._pos_to_kf(event.position())
            kf = self._item.volume_keyframes[self._dragging]
            kf["time"]  = round(t, 2)
            kf["value"] = round(v, 3)
            self._normalize_keyframes()
            self._dragging = self._item.volume_keyframes.index(kf)
            self.keyframe_changed.emit(False)
            self.update()

    def mouseReleaseEvent(self, event):
        if self._cut_service is not None and event.button() == Qt.LeftButton:
            ratio = max(0.0, min(1.0, event.position().x() / max(1, self.width())))
            if self._cut_edge_drag is not None:
                self._cut_service.end_edge_drag()
                self._cut_edge_drag = None
                self.update()
                self.selection_changed.emit()
            elif self._cut_press_pos is not None and self._cut_service.get_pending_point() is not None:
                self._wip_end_preview = None
                self._cut_service.click_point(ratio)
                self._cut_press_pos = None
                self._cut_dragging  = False
                self.update()
                self.selection_changed.emit()
            elif self._cut_dragging:
                self._cut_dragging  = False
                self._cut_press_pos = None
                self._cut_service.commit_wip()
                self.update()
                self.selection_changed.emit()
            else:
                self._cut_service.click_point(ratio)
                self._cut_press_pos = None
                self.update()
                self.selection_changed.emit()
            event.accept()
            return
        if self._dragging is not None:
            self._dragging = None
            self.setCursor(Qt.PointingHandCursor)
            self.keyframe_changed.emit(True)
            self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._find_nearest_keyframe(event.position(), threshold=14)
            if idx is not None:
                self._dragging = idx
                self.setCursor(Qt.SizeAllCursor)
                self.update()
            event.accept()
