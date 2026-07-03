"""GlowOverlay — light spill pintado sobre o centralWidget, atrás de tudo."""

import logging
from PySide6.QtWidgets import QWidget, QSplitter, QSplitterHandle
from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from PySide6.QtGui import QPainter, QRadialGradient, QColor

from makevid.qt.widgets import GlassPanel

log = logging.getLogger("glow")


class PreviewGlowPanel(GlassPanel):
    """GlassPanel normal — notifica o GlowOverlay quando há mídia."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._has_media = False
        self._halo = None  # compatibilidade

    def set_has_media(self, value: bool):
        if value != self._has_media:
            self._has_media = value
            if self._halo:
                self._halo.set_has_media(value)


class GlowOverlay(QWidget):
    """
    Widget filho do centralWidget que pinta o glow atrás de tudo.
    - setAttribute(WA_TransparentForMouseEvents) — não captura mouse
    - lower() — fica atrás de todos os outros filhos
    - Atualiza posição/tamanho via track()
    """

    _SPREAD = 0.35

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self._has_media = False
        self._alpha_t   = 0.0
        self._cx        = 0.0
        self._cy        = 0.0
        self._rw        = 1.0
        self._rh        = 1.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.lower()
        log.info("[GlowOverlay] criado")

    def set_has_media(self, value: bool):
        self._has_media = value

    def track(self, target: QWidget):
        """Cobre o parent inteiro e memoriza o centro/tamanho do target."""
        p = self.parent()
        if not p:
            return
        # cobre todo o parent
        self.setGeometry(0, 0, p.width(), p.height())
        self.lower()
        # centro do target em coordenadas do parent
        origin = target.mapTo(p, QPoint(0, 0))
        self._cx = origin.x() + target.width()  / 2.0
        self._cy = origin.y() + target.height() / 2.0
        self._rw = float(target.width())
        self._rh = float(target.height())
        self.update()
        log.debug(f"[GlowOverlay.track] overlay=({self.width()}x{self.height()}) "
                  f"center=({self._cx:.0f},{self._cy:.0f}) target=({self._rw:.0f}x{self._rh:.0f})")

    def _tick(self):
        target = 1.0 if self._has_media else 0.0
        if self._alpha_t == target:
            return
        step = 0.025
        if abs(self._alpha_t - target) < step:
            self._alpha_t = target
        else:
            self._alpha_t += step if target > self._alpha_t else -step
        self.update()

    def paintEvent(self, event):
        if self._rw == 0:
            return
        p = QPainter(self)
        if not p.isActive():
            return
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy   = self._cx, self._cy
        rw, rh   = self._rw, self._rh
        scale    = 0.6 + 0.4 * self._alpha_t
        rad      = max(rw, rh) * (1.0 + self._SPREAD)

        def _grad(fx, fy, rfrac, r, g, b, ba):
            gx = cx + fx * rw * 0.3
            gy = cy + fy * rh * 0.3
            gr = QRadialGradient(gx, gy, rfrac * rad)
            a  = int(ba * scale)
            gr.setColorAt(0.0, QColor(r, g, b, a))
            gr.setColorAt(0.5, QColor(r, g, b, int(a * 0.4)))
            gr.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), gr)

        _grad( 0.0, -0.4, 0.85,  90, 228, 255, 35)
        _grad( 0.0,  0.4, 0.90, 108,  99, 255, 40)
        _grad( 0.0,  0.0, 1.00,  96, 165, 250, 25)
        _grad(-0.5,  0.0, 0.60,  90, 228, 255, 18)
        _grad( 0.5,  0.0, 0.60, 108,  99, 255, 18)
        p.end()


# Stubs por compatibilidade
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
