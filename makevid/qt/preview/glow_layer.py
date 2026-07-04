"""Glow/light-spill pintado diretamente no PreviewGlowPanel."""

from PySide6.QtWidgets import QWidget, QSplitter
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QPainterPath

from makevid.qt.widgets import GlassPanel


class PreviewGlowPanel(GlassPanel):
    """GlassPanel com halo local ao redor do display. Glow ambiental fica no AmbientBackground."""
    def __init__(self, **kwargs):
        kwargs.setdefault('shadow', False)
        super().__init__(**kwargs)
        self._has_media = False
        self._alpha_t   = 0.35
        self._halo      = None
        self._preview   = None  # referência ao PreviewWidget

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_preview(self, preview_widget):
        """Registra o PreviewWidget para localizar a geometria do display."""
        self._preview = preview_widget

    def set_has_media(self, value: bool):
        if value != self._has_media:
            self._has_media = value

    def _tick(self):
        target = 1.0 if self._has_media else 0.35
        if self._alpha_t == target:
            return
        step = 0.025
        if abs(self._alpha_t - target) < step:
            self._alpha_t = target
        else:
            self._alpha_t += step if target > self._alpha_t else -step
        self.update()

    def _display_rect_in_panel(self) -> QRectF:
        """Retorna a geometria do _VideoDisplay em coordenadas deste painel."""
        pv = self._preview
        if pv is None:
            return QRectF(self.rect())
        display = getattr(pv, '_display', None)
        if display is None:
            return QRectF(self.rect())
        origin = display.mapTo(self, display.rect().topLeft())
        return QRectF(origin.x(), origin.y(), display.width(), display.height())

    def paintEvent(self, event):
        super().paintEvent(event)

        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        w  = self.width()
        h  = self.height()
        a  = self._alpha_t
        dr = self._display_rect_in_panel()

        def _radial(cx, cy, radius, r, g, b, base_a):
            gr = QRadialGradient(QPointF(cx, cy), radius)
            alpha = int(base_a * a)
            gr.setColorAt(0.0, QColor(r, g, b, alpha))
            gr.setColorAt(0.5, QColor(r, g, b, int(alpha * 0.3)))
            gr.setColorAt(1.0, QColor(r, g, b, 0))
            path = QPainterPath()
            path.addEllipse(QPointF(cx, cy), radius, radius)
            p.fillPath(path, gr)

        # ── glow local — nasce da tela ────────────────────────────────────────
        cx = dr.center().x()
        cy = dr.center().y()
        _radial(cx, cy, dr.width() * 0.75,  58, 216, 255, 35)
        _radial(cx, cy, dr.width() * 0.55, 108,  99, 255, 28)

        p.end()


# ── Stubs de compatibilidade ──────────────────────────────────────────────────

class GlowOverlay(QWidget):
    """Stub — mantido para não quebrar imports legados."""
    def __init__(self, parent=None): super().__init__(parent)
    def track(self, *a): pass
    def set_has_media(self, *a): pass


class PreviewHalo:
    def __init__(self, *a, **kw): pass
    def track(self, *a): pass
    def set_has_media(self, *a): pass
    def show(self): pass
    def isVisible(self): return False
    def x(self): return 0
    def y(self): return 0
    def width(self): return 0
    def height(self): return 0


class GlowSplitter(QSplitter):
    """Stub — mantido para não quebrar imports."""
    def set_glow_rect(self, *a): pass
    def set_has_media(self, *a): pass
