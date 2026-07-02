"""PreviewGlowPanel + PreviewHalo — light spill que vaza para fora do preview."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QPainterPath, QBrush

from makevid.qt.widgets import GlassPanel


class PreviewGlowPanel(GlassPanel):
    """GlassPanel padrão — sem glow interno. O halo fica num widget separado atrás."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._has_media = False
        self._halo: "PreviewHalo | None" = None

    def set_has_media(self, value: bool):
        if value != self._has_media:
            self._has_media = value
            if self._halo:
                self._halo.set_has_media(value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._halo:
            self._halo.track(self)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._halo:
            self._halo.track(self)


class PreviewHalo(QWidget):
    """
    Widget irmão do preview_shell, posicionado atrás via lower().
    Pinta gradientes radiais grandes que simulam light spill para o ambiente.
    """

    _SPREAD = 0.55   # quanto o halo extravasa além das bordas (fração do tamanho)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self._has_media = False
        # animação suave de intensidade
        self._alpha_t = 0.0          # 0.0 = idle, 1.0 = com mídia
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── API ───────────────────────────────────────────────────────────────────

    def set_has_media(self, value: bool):
        self._has_media = value

    def track(self, target: QWidget):
        """Reposiciona e redimensiona para cobrir target + spread."""
        if not target.parent():
            return
        pos  = target.pos()
        tw, th = target.width(), target.height()
        sx = int(tw * self._SPREAD)
        sy = int(th * self._SPREAD)
        self.setGeometry(
            pos.x() - sx,
            pos.y() - sy,
            tw + sx * 2,
            th + sy * 2,
        )
        self.lower()
        self.update()

    # ── animação ──────────────────────────────────────────────────────────────

    def _tick(self):
        target = 1.0 if self._has_media else 0.0
        step   = 0.025
        if abs(self._alpha_t - target) < step:
            self._alpha_t = target
        else:
            self._alpha_t += step if target > self._alpha_t else -step
        self.update()

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        t = self._alpha_t

        # escala de alpha: idle=0.6, com mídia=1.0
        scale = 0.6 + 0.4 * t

        def _grad(fx, fy, radius_frac, r, g, b, base_alpha):
            gx, gy = cx + fx * w * 0.25, cy + fy * h * 0.25
            rad = radius_frac * max(w, h)
            gr = QRadialGradient(gx, gy, rad)
            a = int(base_alpha * scale)
            gr.setColorAt(0.0, QColor(r, g, b, a))
            gr.setColorAt(0.55, QColor(r, g, b, int(a * 0.3)))
            gr.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), gr)

        # ciano — topo-centro
        _grad( 0.0, -0.35, 0.72,  90, 228, 255, 28)
        # roxo — base-centro
        _grad( 0.0,  0.35, 0.78, 108,  99, 255, 32)
        # azul — centro
        _grad( 0.0,  0.0,  0.90,  96, 165, 250, 20)
        # ciano extra lateral esquerda (sutil)
        _grad(-0.5,  0.0,  0.55,  90, 228, 255, 14)
        # roxo extra lateral direita (sutil)
        _grad( 0.5,  0.0,  0.55, 108,  99, 255, 14)

        p.end()
