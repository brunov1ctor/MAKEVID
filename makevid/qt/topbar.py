"""Topbar — menus e botões superiores."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QFont, QFontMetrics, QPen, QCursor

from makevid.qt.theme import C
from makevid.qt.widgets import GlassPanel, TopbarButton, GlowDot


class _LogoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(130, 40)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 65, 0)
        grad.setColorAt(0.0, QColor(C["secondary"]))
        grad.setColorAt(1.0, QColor(C["primary"]))
        p.setPen(QColor(C["primary"]))
        p.setFont(QFont("Segoe UI", 15, QFont.Bold))
        p.drawText(0, 30, "MAKE")
        p.setPen(QColor(C["accent"]))
        p.setFont(QFont("Segoe UI", 15, QFont.Bold))
        p.drawText(68, 30, "VID")
        p.end()

class _DropMenu(QWidget):
    """
    Dropdown 100% Qt — sem janela nativa, sem flash.
    Filho do centralWidget da QMainWindow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropMenu")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.hide()

        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(1)
        self._items = []

    def add_action(self, label, callback, checkable=False, checked=False):
        item = _DropItem(label, callback, checkable=checkable, checked=checked)
        item.triggered.connect(self.hide)
        self._vbox.addWidget(item)
        self._items.append(item)
        return item

    def add_separator(self):
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']}; border: none;")
        self._vbox.addWidget(sep)

    def popup(self, anchor_widget):
        """Posiciona e exibe abaixo do widget âncora."""
        parent = self.parent()
        if parent is None:
            return
        self.adjustSize()
        # Converte canto inferior-esquerdo do botão para coordenadas do parent
        gpos = anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height() + 2))
        lpos = parent.mapFromGlobal(gpos)
        x = max(0, min(lpos.x(), parent.width() - self.width() - 4))
        y = lpos.y()
        self.move(x, y)
        self.raise_()
        self.show()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 12, 12)
        p.fillPath(path, QColor(14, 22, 42, 230))
        p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
        p.drawPath(path)
        p.end()


class _DropItem(QWidget):
    triggered = Signal()

    def __init__(self, label, callback, checkable=False, checked=False, parent=None):
        super().__init__(parent)
        self._callback = callback
        self._checkable = checkable
        self._checked = checked
        self._hover = False
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(32)
        self.setMinimumWidth(160)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(6)

        if checkable:
            self._dot = QLabel()
            self._dot.setFixedSize(8, 8)
            self._dot.setStyleSheet(
                f"background: {C['primary']}; border-radius: 4px;"
                if checked else "background: transparent;"
            )
            row.addWidget(self._dot)

        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(f"color: {C['text']}; font-size: 10pt; background: transparent;")
        row.addWidget(self._lbl)
        row.addStretch()

    def set_checked(self, val):
        self._checked = val
        if self._checkable:
            self._dot.setStyleSheet(
                f"background: {C['primary']}; border-radius: 4px;"
                if val else "background: transparent;"
            )

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if self._callback:
            self._callback()
        self.triggered.emit()

    def paintEvent(self, e):
        if self._hover:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(2, 1, self.width() - 4, self.height() - 2, 8, 8)
            p.fillPath(path, QColor(36, 58, 94, 120))
            p.end()


class _EngineBadge(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._text = text
        self.setFixedHeight(22)
        self.setMinimumWidth(80)

    def set_text(self, text):
        self._text = text
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        font = QFont("Consolas", 8)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self._text) + 16
        self.setFixedWidth(max(tw, 80))
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        bg = QColor(28, 46, 74, 180)
        p.fillPath(path, bg)
        bc = QColor(255, 255, 255, 80)
        p.setPen(QPen(bc, 1))
        p.drawPath(path)
        p.setPen(QColor(C["text3"]))
        p.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self._text)
        p.end()


class _ProjectBadge(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._text = text
        self.setFixedHeight(30)
        self.setMinimumWidth(100)

    def set_text(self, text):
        self._text = text
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        font = QFont("Segoe UI", 11, QFont.Bold)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self._text) + 20
        self.setFixedWidth(max(tw, 80))
        p.setPen(QColor(C["primary"]))
        p.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self._text)
        p.end()


def build_topbar(window) -> GlassPanel:
    """Constrói a topbar e injeta referências em `window`."""
    tb = GlassPanel(radius=22, shadow=True, shadow_radius=24, shadow_dy=6,
                    tint="#1a2d50", tint_alpha=210, border_opacity=80)
    tb.setFixedHeight(58)

    h = QHBoxLayout(tb)
    h.setContentsMargins(18, 8, 18, 8)
    h.setSpacing(6)

    h.addWidget(_LogoWidget())

    div = QWidget()
    div.setFixedSize(1, 22)
    div.setStyleSheet(f"background: {C['glass_border']};")
    h.addWidget(div)
    h.addSpacing(4)

    def _menu_btn(label, icon):
        btn = TopbarButton(f"{icon}  {label}")
        btn.setFixedHeight(38)
        return btn

    def _toggle(menu, btn):
        """Abre/fecha o dropdown; fecha os outros."""
        all_menus = getattr(window, "_all_drop_menus", [])
        for m in all_menus:
            if m is not menu and m.isVisible():
                m.hide()
        if menu.isVisible():
            menu.hide()
        else:
            menu.popup(btn)

    window._all_drop_menus = []

    def _make_menu():
        central = window.centralWidget()
        m = _DropMenu(parent=central)
        window._all_drop_menus.append(m)
        return m

    # Arquivo
    btn_arq = _menu_btn("Arquivo", "\U0001f4c1")
    m_arq = _make_menu()
    m_arq.add_action("Projetos",       window._show_projects_panel)
    m_arq.add_action("Limpar Projeto", window._clear_project)
    m_arq.add_separator()
    m_arq.add_action("Meus Videos",    window._show_video_browser)
    m_arq.add_action("Meus Audios",    window._show_audio_browser)
    btn_arq.clicked.connect(lambda: _toggle(m_arq, btn_arq))
    h.addWidget(btn_arq)

    # Engine
    btn_eng = _menu_btn("Engine", "\u2699")
    m_eng = _make_menu()
    _engine_items = {}
    for eng in ["Local (GPU)", "Local (CPU)", "Wan 2.2 TI2V", None,
                "VACE (Referencia)", "V2V (Refinar)", None, "HuggingFace API"]:
        if eng is None:
            m_eng.add_separator()
        else:
            item = m_eng.add_action(eng, lambda e=eng: window._set_engine(e),
                                    checkable=True, checked=(eng == window._engine))
            _engine_items[eng] = item
    btn_eng.clicked.connect(lambda: _toggle(m_eng, btn_eng))
    h.addWidget(btn_eng)
    window._engine_menu = m_eng
    window._engine_items = _engine_items

    # Tema
    btn_est = _menu_btn("Tema", "\U0001f58b")
    m_est = _make_menu()
    m_est.add_action("Storyboard",  lambda: window._show_style_tab(0))
    m_est.add_action("Personagens", lambda: window._show_style_tab(1))
    m_est.add_action("Ambientacao", lambda: window._show_style_tab(2))
    btn_est.clicked.connect(lambda: _toggle(m_est, btn_est))
    h.addWidget(btn_est)

    # Audio IA
    btn_aia = _menu_btn("Audio IA", "\u266b")
    m_aia = _make_menu()
    m_aia.add_action("Gerar Audio da Cena",           window._generate_scene_audio)
    m_aia.add_action("Gerar Audio de Todas as Cenas", window._generate_all_audio)
    btn_aia.clicked.connect(lambda: _toggle(m_aia, btn_aia))
    h.addWidget(btn_aia)

    # Logs
    btn_log = _menu_btn("Logs", "\U0001f4cb")
    m_log = _make_menu()
    m_log.add_action("Ver Logs", window._open_logs)
    btn_log.clicked.connect(lambda: _toggle(m_log, btn_log))
    h.addWidget(btn_log)

    h.addStretch()

    window._status_dot = GlowDot(color=C["track_sfx"])
    h.addWidget(window._status_dot)

    window._project_badge = _ProjectBadge(window.project.name)
    h.addWidget(window._project_badge)

    div2 = QWidget()
    div2.setFixedSize(1, 22)
    div2.setStyleSheet(f"background: {C['glass_border']};")
    h.addWidget(div2)

    window._engine_badge = _EngineBadge(window._engine)
    h.addWidget(window._engine_badge)

    return tb
