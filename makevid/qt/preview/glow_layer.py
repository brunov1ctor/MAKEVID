"""PreviewGlowPanel — GlassPanel com light spill pintado no próprio paintEvent."""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QPainterPath, QLinearGradient, QBrush, QPen

from makevid.qt.widgets import GlassPanel
from makevid.qt.theme import C


class PreviewGlowPanel(GlassPanel):
    """GlassPanel com glow de light spill pintado antes do vidro, clipado ao path arredondado."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._has_media = False

    def set_has_media(self, value: bool):
        if value != self._has_media:
            self._has_media = value
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        alpha_scale = 1.8 if self._has_media else 1.0

        # Path arredondado — definido primeiro para usar no clip e no glass
        r = QRectF(1, 1, w - 2, h - 2)
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)

        # ── Glow clipado ao path arredondado ──────────────────────────────
        p.setClipPath(path)
        p.setCompositionMode(QPainter.CompositionMode_Screen)

        g1 = QRadialGradient(cx, cy * 0.3, w * 0.7)
        g1.setColorAt(0.0, QColor(90, 228, 255, int(18 * alpha_scale)))
        g1.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), g1)

        g2 = QRadialGradient(cx, cy * 1.6, w * 0.75)
        g2.setColorAt(0.0, QColor(108, 99, 255, int(22 * alpha_scale)))
        g2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), g2)

        g3 = QRadialGradient(cx, cy, w * 0.85)
        g3.setColorAt(0.0, QColor(96, 165, 250, int(14 * alpha_scale)))
        g3.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), g3)

        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setClipping(False)

        # ── Glass ─────────────────────────────────────────────────────────
        grad = QLinearGradient(0, 0, 0, h)
        base = QColor(self._tint)
        top_c = QColor(base)
        top_c.setRed(min(255, base.red() + 14))
        top_c.setGreen(min(255, base.green() + 12))
        top_c.setBlue(min(255, base.blue() + 18))
        top_c.setAlpha(245)
        base.setAlpha(230)
        grad.setColorAt(0.0, top_c)
        grad.setColorAt(1.0, base)
        p.fillPath(path, QBrush(grad))

        inner_grad = QLinearGradient(0, 0, 0, self._radius * 2)
        inner_grad.setColorAt(0.0, QColor(0, 0, 0, 28))
        inner_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        inner_path = QPainterPath()
        inner_path.addRoundedRect(QRectF(1, 1, w - 2, self._radius * 2), self._radius, self._radius)
        p.fillPath(inner_path, QBrush(inner_grad))

        ref_rect = QRectF(self._radius * 0.4, 1, w - self._radius * 0.8, min(self._radius * 1.2, 20))
        ref_path = QPainterPath()
        ref_path.addRoundedRect(ref_rect, self._radius * 0.3, self._radius * 0.3)
        ref_grad = QLinearGradient(0, 0, 0, ref_rect.height())
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, 22))
        ref_grad.setColorAt(0.5, QColor(255, 255, 255, 8))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.fillPath(ref_path, QBrush(ref_grad))

        border_color = QColor(C["glass_border"])
        border_color.setAlpha(self._border_opacity)
        p.setPen(QPen(border_color, 1.0))
        p.drawPath(path)

        p.end()
