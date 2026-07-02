"""VisionOS-style custom widgets — QPainter, shadows, gradients, animations."""

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QRect, QRectF, QPoint, QPointF, QSize,
    QPropertyAnimation, QEasingCurve, QTimer, Property, Signal
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QFont, QFontMetrics, QCursor
)

from makevid.qt.theme import C


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _hex(key: str) -> QColor:
    return QColor(C[key])

def _shadow(widget: QWidget, radius=32, color="#000000", opacity=160, dx=0, dy=8):
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(radius)
    c = QColor(color)
    c.setAlpha(opacity)
    fx.setColor(c)
    fx.setOffset(dx, dy)
    widget.setGraphicsEffect(fx)
    return fx

def _soft_shadow(widget: QWidget, radius=64, opacity=180, dy=16):
    """Sombra profunda para separar painéis do fundo."""
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(radius)
    c = QColor(C["dark"])
    c.setAlpha(opacity)
    fx.setColor(c)
    fx.setOffset(0, dy)
    widget.setGraphicsEffect(fx)
    return fx


# ─────────────────────────────────────────────
#  GlassPanel  — painel flutuante com vidro
# ─────────────────────────────────────────────

class GlassPanel(QWidget):
    """
    Painel com fundo glass pintado via QPainter.
    Suporta borda translúcida, gradiente interno e sombra.
    """

    def __init__(self, parent=None, radius=20, tint=None, border_opacity=45,
                 shadow=True, shadow_radius=40, shadow_dy=12):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self._radius = radius
        self._tint = QColor(tint) if tint else QColor(C["glass"])
        self._border_opacity = border_opacity

        if shadow:
            _soft_shadow(self, radius=shadow_radius, opacity=130, dy=shadow_dy)

    # ── paint ──────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        r = QRectF(1, 1, w - 2, h - 2)
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)

        # Gradiente topo→base — painel mais claro no topo, mais escuro na base
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

        # Inner shadow no topo — profundidade
        inner_grad = QLinearGradient(0, 0, 0, self._radius * 2)
        inner_grad.setColorAt(0.0, QColor(0, 0, 0, 28))
        inner_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        inner_path = QPainterPath()
        inner_path.addRoundedRect(QRectF(1, 1, w - 2, self._radius * 2), self._radius, self._radius)
        p.fillPath(inner_path, QBrush(inner_grad))

        # Highlight branco no topo — brilho de superfície
        ref_rect = QRectF(self._radius * 0.4, 1, w - self._radius * 0.8, min(self._radius * 1.2, 20))
        ref_path = QPainterPath()
        ref_path.addRoundedRect(ref_rect, self._radius * 0.3, self._radius * 0.3)
        ref_grad = QLinearGradient(0, 0, 0, ref_rect.height())
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, 22))
        ref_grad.setColorAt(0.5, QColor(255, 255, 255, 8))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.fillPath(ref_path, QBrush(ref_grad))

        # Borda translúcida
        border_color = QColor(C["glass_border"])
        border_color.setAlpha(self._border_opacity)
        p.setPen(QPen(border_color, 1.0))
        p.drawPath(path)

        p.end()


# ─────────────────────────────────────────────
#  GlassCard  — card menor, sem sombra pesada
# ─────────────────────────────────────────────

class GlassCard(QWidget):
    """Card compacto com hover animado."""

    def __init__(self, parent=None, radius=14, hover_color=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self._radius = radius
        self._base_color = QColor(C["glass"])
        self._hover_color = QColor(hover_color) if hover_color else QColor(C["glass_hover"])
        self._current_color = QColor(self._base_color)
        self._hovered = False
        self.setCursor(QCursor(Qt.PointingHandCursor))

        # Animação de cor no hover
        self._anim_alpha = QPropertyAnimation(self, b"_blend")
        self._anim_alpha.setDuration(150)
        self._anim_alpha.setEasingCurve(QEasingCurve.OutCubic)

        _shadow(self, radius=16, opacity=120, dy=4)

    # ── blend property para animar ──────────────

    def _get_blend(self):
        return self._blend_val if hasattr(self, "_blend_val") else 0

    def _set_blend(self, val):
        self._blend_val = val
        # Interpola entre base e hover
        t = val / 100.0
        r = int(self._base_color.red()   * (1-t) + self._hover_color.red()   * t)
        g = int(self._base_color.green() * (1-t) + self._hover_color.green() * t)
        b = int(self._base_color.blue()  * (1-t) + self._hover_color.blue()  * t)
        self._current_color = QColor(r, g, b, 210)
        self.update()

    _blend = Property(int, _get_blend, _set_blend)

    def enterEvent(self, event):
        self._anim_alpha.stop()
        self._anim_alpha.setStartValue(self._get_blend())
        self._anim_alpha.setEndValue(100)
        self._anim_alpha.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim_alpha.stop()
        self._anim_alpha.setStartValue(self._get_blend())
        self._anim_alpha.setEndValue(0)
        self._anim_alpha.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        t = self._get_blend() / 100.0
        w, h = self.width(), self.height()
        r = QRectF(0.5, 0.5, w - 1, h - 1)
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)

        # Gradiente base→hover com separação mais pronunciada
        grad = QLinearGradient(0, 0, 0, h)
        top_c = QColor(self._current_color)
        top_c.setRed(min(255, top_c.red() + 12))
        top_c.setGreen(min(255, top_c.green() + 10))
        top_c.setBlue(min(255, top_c.blue() + 16))
        top_c.setAlpha(min(255, self._current_color.alpha() + 20))
        grad.setColorAt(0.0, top_c)
        grad.setColorAt(1.0, self._current_color)
        p.fillPath(path, QBrush(grad))

        # Highlight interno no topo — brilho de superfície
        ref_path = QPainterPath()
        ref_path.addRoundedRect(QRectF(self._radius * 0.4, 0.5, w - self._radius * 0.8, h * 0.35), self._radius * 0.5, self._radius * 0.5)
        ref_grad = QLinearGradient(0, 0, 0, h * 0.35)
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, int(20 + t * 18)))
        ref_grad.setColorAt(0.5, QColor(255, 255, 255, int(6 + t * 6)))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.fillPath(ref_path, QBrush(ref_grad))

        # Borda
        bc = QColor(C["glass_border"])
        bc.setAlpha(int(60 + t * 100))
        p.setPen(QPen(bc, 1.0))
        p.drawPath(path)
        p.end()


# ─────────────────────────────────────────────
#  GlassButton  — botão VisionOS com animação
# ─────────────────────────────────────────────

class GlassButton(QPushButton):
    """
    Botão com fundo glass, gradiente, reflexo e animação de press.
    Substitui QPushButton com QSS.
    """

    def __init__(self, text="", parent=None, accent=False, danger=False,
                 icon_text="", radius=12, height=36):
        super().__init__(text, parent)
        self._accent = accent
        self._danger = danger
        self._icon_text = icon_text
        self._radius = radius
        self._press_scale = 1.0
        self._hover_t = 0.0
        self.setFixedHeight(height)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none;")

        # Cores base
        if accent:
            self._color_base = QColor(C["primary"])    # dourado
            self._color_hover = QColor(C["secondary"])  # dourado claro
            self._text_color = QColor(C["dark_text"])   # texto escuro sobre dourado
        elif danger:
            self._color_base = QColor(C["danger_bg"])
            self._color_hover = QColor(C["danger"])
            self._text_color = QColor(C["danger"])
        else:
            self._color_base = QColor(C["glass"])
            self._color_hover = QColor(C["glass_hover"])
            self._text_color = QColor(C["text"])

        # Animação hover
        self._hover_anim = QPropertyAnimation(self, b"_hover_prop")
        self._hover_anim.setDuration(150)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

        _soft_shadow(self, radius=24, opacity=140, dy=5)

    def _get_hover_prop(self):
        return int(self._hover_t * 100)

    def _set_hover_prop(self, val):
        self._hover_t = val / 100.0
        self.update()

    _hover_prop = Property(int, _get_hover_prop, _set_hover_prop)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._get_hover_prop())
        self._hover_anim.setEndValue(100)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._get_hover_prop())
        self._hover_anim.setEndValue(0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._press_scale = 0.97
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_scale = 1.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        t = self._hover_t
        w, h = self.width(), self.height()

        # Scale no press
        if self._press_scale < 1.0:
            p.translate(w / 2, h / 2)
            p.scale(self._press_scale, self._press_scale)
            p.translate(-w / 2, -h / 2)

        r = QRectF(1, 1, w - 2, h - 2)
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)

        # Cor interpolada
        cr = int(self._color_base.red()   * (1-t) + self._color_hover.red()   * t)
        cg = int(self._color_base.green() * (1-t) + self._color_hover.green() * t)
        cb = int(self._color_base.blue()  * (1-t) + self._color_hover.blue()  * t)
        fill = QColor(cr, cg, cb)

        # Gradiente vertical mais pronunciado no hover
        grad = QLinearGradient(0, 0, 0, h)
        top_fill = QColor(fill)
        top_fill.setAlpha(int(215 + t * 25))
        bot_fill = QColor(fill)
        bot_fill.setAlpha(int(195 + t * 20))
        # topo ligeiramente mais claro
        top_fill.setRed(min(255, top_fill.red() + int(t * 12)))
        top_fill.setGreen(min(255, top_fill.green() + int(t * 10)))
        grad.setColorAt(0.0, top_fill.lighter(int(108 + t * 8)))
        grad.setColorAt(1.0, bot_fill)
        p.fillPath(path, QBrush(grad))

        # Highlight topo (reflexo glass)
        ref = QRectF(self._radius * 0.5, 1, w - self._radius, h * 0.38)
        ref_path = QPainterPath()
        ref_path.addRoundedRect(ref, self._radius * 0.4, self._radius * 0.4)
        ref_grad = QLinearGradient(0, 0, 0, ref.height())
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, int(28 + t * 22)))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.fillPath(ref_path, QBrush(ref_grad))

        # Borda
        if self._accent:
            bc = QColor(C["neon_gold"])
            bc.setAlpha(int(140 + t * 115))
        elif self._danger:
            bc = QColor(C["danger"])
            bc.setAlpha(int(110 + t * 145))
        else:
            bc = QColor(C["glass_border"])
            bc.setAlpha(int(60 + t * 120))
        p.setPen(QPen(bc, 1.0))
        p.drawPath(path)

        # Glow sutil no accent ao hover
        if self._accent and t > 0.1:
            glow_c = QColor(C["primary"])
            glow_c.setAlpha(int(t * 30))
            glow_pen = QPen(glow_c, 3.0)
            p.setPen(glow_pen)
            p.drawPath(path)

        # Texto
        tc = QColor(self._text_color)
        if self._accent:
            tc.setAlpha(255)
        else:
            tc.setAlpha(int(170 + t * 85))
        p.setPen(tc)
        font = QFont("Segoe UI", 10, QFont.Bold)
        p.setFont(font)
        label = self._icon_text + ("  " if self._icon_text else "") + self.text()
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, label)

        p.end()

    def sizeHint(self):
        fm = QFontMetrics(QFont("Segoe UI", 10, QFont.Bold))
        tw = fm.horizontalAdvance(self.text()) + 32
        return QSize(max(tw, 80), self.height())


# ─────────────────────────────────────────────
#  BrowserTabBar  — abas estilo navegador web
# ─────────────────────────────────────────────

class BrowserTabBar(QWidget):
    """
    Tab bar estilo navegador web: abas com cantos arredondados no topo,
    aba ativa "conectada" ao conteúdo (sem borda inferior).
    """

    tab_clicked = Signal(int)

    def __init__(self, tabs: list[str], parent=None):
        super().__init__(parent)
        self._tabs = tabs
        self._active = 0
        self._hover = -1
        self.setFixedHeight(34)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _tab_rect(self, idx: int) -> QRectF:
        n = len(self._tabs)
        if n == 0:
            return QRectF()
        tw = self.width() / n
        return QRectF(idx * tw, 0, tw, self.height())

    def set_active(self, idx: int):
        self._active = idx
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        n = len(self._tabs)
        if n == 0:
            return

        tw = w / n
        R = 9  # raio dos cantos superiores

        # Linha de base (fundo das abas inativas)
        base_color = QColor(C["glass"])
        base_color.setAlpha(180)
        p.fillRect(QRectF(0, h - 1, w, 1), base_color)

        for i, tab in enumerate(self._tabs):
            rect = self._tab_rect(i)
            is_active = (i == self._active)
            is_hover = (i == self._hover and not is_active)

            # Fundo da aba
            tab_path = QPainterPath()
            # Cantos arredondados apenas no topo
            tab_path.moveTo(rect.left() + 2, rect.bottom())
            tab_path.lineTo(rect.left() + 2, rect.top() + R)
            tab_path.quadTo(rect.left() + 2, rect.top(), rect.left() + 2 + R, rect.top())
            tab_path.lineTo(rect.right() - 2 - R, rect.top())
            tab_path.quadTo(rect.right() - 2, rect.top(), rect.right() - 2, rect.top() + R)
            tab_path.lineTo(rect.right() - 2, rect.bottom())
            tab_path.closeSubpath()

            if is_active:
                # Aba ativa: fundo igual ao painel, sem borda inferior
                fill = QColor(C["glass"])
                fill.setAlpha(255)
                grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
                top_c = QColor(fill)
                top_c.setRed(min(255, fill.red() + 14))
                top_c.setGreen(min(255, fill.green() + 12))
                top_c.setBlue(min(255, fill.blue() + 18))
                grad.setColorAt(0.0, top_c)
                grad.setColorAt(1.0, fill)
                p.fillPath(tab_path, QBrush(grad))

                # Borda superior colorida (indicador ativo)
                accent = QColor(C["primary"])
                p.setPen(QPen(accent, 2))
                p.drawLine(QPointF(rect.left() + 2 + R, rect.top() + 1),
                           QPointF(rect.right() - 2 - R, rect.top() + 1))

                # Borda lateral esquerda e direita (sem borda inferior)
                bc = QColor(C["glass_border"])
                bc.setAlpha(60)
                p.setPen(QPen(bc, 1))
                # esquerda
                p.drawLine(QPointF(rect.left() + 2, rect.top() + R),
                           QPointF(rect.left() + 2, rect.bottom()))
                # direita
                p.drawLine(QPointF(rect.right() - 2, rect.top() + R),
                           QPointF(rect.right() - 2, rect.bottom()))
                # arco topo-esquerdo
                p.drawArc(QRect(int(rect.left() + 2), int(rect.top()), R * 2, R * 2), 90 * 16, 90 * 16)
                # arco topo-direito
                p.drawArc(QRect(int(rect.right() - 2 - R * 2), int(rect.top()), R * 2, R * 2), 0, 90 * 16)

            elif is_hover:
                hover_fill = QColor(C["glass_hover"])
                hover_fill.setAlpha(120)
                p.fillPath(tab_path, hover_fill)
                bc = QColor(C["glass_border"])
                bc.setAlpha(30)
                p.setPen(QPen(bc, 1))
                p.drawPath(tab_path)

            # Texto
            p.setPen(Qt.NoPen)
            if is_active:
                color = QColor(C["text"])
            elif is_hover:
                color = QColor(C["text2"])
                color.setAlpha(200)
            else:
                color = QColor(C["text3"])
                color.setAlpha(160)

            p.setPen(color)
            font = QFont("Segoe UI", 9, QFont.Bold if is_active else QFont.Normal)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, tab)

        p.end()

    def mousePressEvent(self, event):
        n = len(self._tabs)
        if n == 0:
            return
        tw = self.width() / n
        idx = int(event.position().x() / tw)
        idx = max(0, min(n - 1, idx))
        self.set_active(idx)
        self.tab_clicked.emit(idx)

    def mouseMoveEvent(self, event):
        n = len(self._tabs)
        if n == 0:
            return
        tw = self.width() / n
        new_hover = int(event.position().x() / tw)
        new_hover = max(0, min(n - 1, new_hover))
        if new_hover != self._hover:
            self._hover = new_hover
            self.update()

    def leaveEvent(self, event):
        self._hover = -1
        self.update()


# ─────────────────────────────────────────────
#  GlassTabBar  — tab bar VisionOS pill-style
# ─────────────────────────────────────────────

class GlassTabBar(QWidget):
    """
    Tab bar estilo VisionOS: pílula deslizante animada sob a aba ativa.
    """

    tab_clicked = Signal(int)

    def __init__(self, tabs: list[str], parent=None):
        super().__init__(parent)
        self._tabs = tabs
        self._active = 0
        self._hover = -1
        self._pill_x = 0.0          # posição animada da pílula
        self._pill_target = 0.0
        self.setFixedHeight(38)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Animação da pílula
        self._pill_anim = QPropertyAnimation(self, b"_pill_pos")
        self._pill_anim.setDuration(220)
        self._pill_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _get_pill_pos(self):
        return int(self._pill_x)

    def _set_pill_pos(self, val):
        self._pill_x = val
        self.update()

    _pill_pos = Property(int, _get_pill_pos, _set_pill_pos)

    def _tab_rect(self, idx: int) -> QRectF:
        n = len(self._tabs)
        if n == 0:
            return QRectF()
        tw = self.width() / n
        return QRectF(idx * tw, 0, tw, self.height())

    def set_active(self, idx: int):
        if idx == self._active:
            return
        self._active = idx
        target = self._tab_rect(idx).x()
        self._pill_anim.stop()
        self._pill_anim.setStartValue(int(self._pill_x))
        self._pill_anim.setEndValue(int(target))
        self._pill_anim.start()
        self.tab_clicked.emit(idx)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        n = len(self._tabs)
        if n == 0:
            return

        tw = w / n

        # Fundo da barra com gradiente sutil
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(0, 0, w, h), 12, 12)
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_top = QColor(C["dark"])
        bg_top.setAlpha(180)
        bg_bot = QColor(C["dark"])
        bg_bot.setAlpha(140)
        bg_grad.setColorAt(0.0, bg_top)
        bg_grad.setColorAt(1.0, bg_bot)
        p.fillPath(bg_path, QBrush(bg_grad))

        # Borda da barra
        bc = QColor(C["glass_border"])
        bc.setAlpha(40)
        p.setPen(QPen(bc, 0.8))
        p.drawPath(bg_path)
        p.setPen(Qt.NoPen)

        # Pílula ativa com gradiente dourado
        pill_rect = QRectF(self._pill_x + 3, 3, tw - 6, h - 6)
        pill_path = QPainterPath()
        pill_path.addRoundedRect(pill_rect, 9, 9)

        pill_grad = QLinearGradient(pill_rect.left(), pill_rect.top(), pill_rect.left(), pill_rect.bottom())
        pc = QColor(C["primary"])
        pill_grad.setColorAt(0.0, pc.lighter(135))
        pill_grad.setColorAt(0.5, pc)
        pill_grad.setColorAt(1.0, pc.darker(110))
        p.fillPath(pill_path, QBrush(pill_grad))

        # Highlight na pílula
        ref_rect = QRectF(self._pill_x + 6, 4, tw - 12, (h - 6) * 0.42)
        ref_path = QPainterPath()
        ref_path.addRoundedRect(ref_rect, 7, 7)
        ref_grad = QLinearGradient(0, ref_rect.top(), 0, ref_rect.bottom())
        ref_grad.setColorAt(0.0, QColor(255, 255, 255, 55))
        ref_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(ref_path, QBrush(ref_grad))

        # Textos
        for i, tab in enumerate(self._tabs):
            rect = self._tab_rect(i)
            is_active = (i == self._active)
            is_hover = (i == self._hover and not is_active)

            if is_active:
                color = QColor(C["dark_text"])
                color.setAlpha(230)
            elif is_hover:
                color = QColor(C["text"])
                color.setAlpha(200)
            else:
                color = QColor(C["text2"])
                color.setAlpha(160)

            p.setPen(color)
            font = QFont("Segoe UI", 9, QFont.Bold if is_active else QFont.Normal)
            p.setFont(font)
            p.drawText(rect, Qt.AlignCenter, tab)

        p.end()

    def mousePressEvent(self, event):
        n = len(self._tabs)
        if n == 0:
            return
        tw = self.width() / n
        idx = int(event.position().x() / tw)
        idx = max(0, min(n - 1, idx))
        self.set_active(idx)

    def mouseMoveEvent(self, event):
        n = len(self._tabs)
        if n == 0:
            return
        tw = self.width() / n
        new_hover = int(event.position().x() / tw)
        new_hover = max(0, min(n - 1, new_hover))
        if new_hover != self._hover:
            self._hover = new_hover
            self.update()

    def leaveEvent(self, event):
        self._hover = -1
        self.update()


# ─────────────────────────────────────────────
#  SectionLabel  — label de seção com linha
# ─────────────────────────────────────────────

class SectionLabel(QWidget):
    """Label de seção com linha decorativa à direita."""

    def __init__(self, text: str, color=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._color = QColor(color) if color else QColor(C["primary"])
        self.setFixedHeight(22)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        font = QFont("Segoe UI", 8, QFont.Bold)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self._text)

        # Texto
        p.setPen(self._color)
        p.drawText(0, fm.ascent() + 4, self._text)

        # Linha
        lx = tw + 8
        ly = self.height() // 2
        line_color = QColor(self._color)
        line_color.setAlpha(40)
        p.setPen(QPen(line_color, 1))
        p.drawLine(lx, ly, self.width(), ly)

        p.end()


# ─────────────────────────────────────────────
#  GlowDot  — indicador de status animado
# ─────────────────────────────────────────────

class GlowDot(QWidget):
    """Ponto pulsante de status (verde=ativo, vermelho=erro, etc.)."""

    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._color = QColor(color) if color else QColor(C["track_sfx"])
        self._alpha = 255
        self.setFixedSize(10, 10)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(30)
        self._pulse_dir = -4
        self._pulse_timer.timeout.connect(self._tick)
        self._pulse_timer.start()

    def _tick(self):
        self._alpha += self._pulse_dir
        if self._alpha <= 80:
            self._pulse_dir = 4
        elif self._alpha >= 255:
            self._pulse_dir = -4
        self.update()

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() // 2, self.height() // 2

        # Halo externo
        halo = QRadialGradient(cx, cy, 5)
        halo_c = QColor(self._color)
        halo_c.setAlpha(int(self._alpha * 0.3))
        halo.setColorAt(0.0, halo_c)
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(cx - 5, cy - 5, 10, 10)

        # Ponto central
        dot = QColor(self._color)
        dot.setAlpha(self._alpha)
        p.setBrush(dot)
        p.drawEllipse(cx - 3, cy - 3, 6, 6)

        p.end()


# ─────────────────────────────────────────────
#  TopbarButton  — botão de menu da topbar
# ─────────────────────────────────────────────

class TopbarButton(QWidget):
    """Botão da topbar com underline animado no hover."""

    clicked = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text
        self._hover_t = 0.0
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(46)

        self._hover_anim = QPropertyAnimation(self, b"_hover_prop")
        self._hover_anim.setDuration(180)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)

    def text(self):
        return self._text

    def _get_hover_prop(self):
        return int(self._hover_t * 100)

    def _set_hover_prop(self, val):
        self._hover_t = val / 100.0
        self.update()

    _hover_prop = Property(int, _get_hover_prop, _set_hover_prop)

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._get_hover_prop())
        self._hover_anim.setEndValue(100)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._get_hover_prop())
        self._hover_anim.setEndValue(0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        t = self._hover_t
        w, h = self.width(), self.height()

        if t > 0:
            bg = QColor(C["glass_hover"])
            bg.setAlpha(int(t * 80))
            path = QPainterPath()
            path.addRoundedRect(QRectF(2, 4, w - 4, h - 8), 8, 8)
            p.fillPath(path, bg)

        tc = QColor(C["text"] if t > 0.3 else C["text2"])
        p.setPen(tc)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(QRectF(0, 0, w, h - 3), Qt.AlignCenter, self._text)

        if t > 0:
            uw = int((w - 16) * t)
            ux = (w - uw) // 2
            uy = h - 5
            line_color = QColor(C["primary"])
            line_color.setAlpha(int(t * 200))
            p.setPen(QPen(line_color, 2, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(ux, uy, ux + uw, uy)

        p.end()

    def sizeHint(self):
        fm = QFontMetrics(QFont("Segoe UI", 10, QFont.Bold))
        return QSize(fm.horizontalAdvance(self._text) + 28, 46)
