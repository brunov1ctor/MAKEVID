"""Topbar — menus e botões superiores."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QFont, QFontMetrics, QPen

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
        bg = QColor(C["glass"])
        bg.setAlpha(180)
        p.fillPath(path, bg)
        bc = QColor(C["glass_border"])
        bc.setAlpha(80)
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
    tb = GlassPanel(radius=22, shadow=True, shadow_radius=24, shadow_dy=6)
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

    mqss = (
        f"QMenu {{ background: {C['card']}; color: {C['text']}; "
        f"border: 1px solid {C['glass_border']}; border-radius: 12px; padding: 6px 4px; }}"
        f"QMenu::item {{ padding: 7px 22px; border-radius: 8px; margin: 1px 4px; }}"
        f"QMenu::item:selected {{ background: {C['glass_hover']}; color: {C['primary']}; }}"
        f"QMenu::item:pressed {{ background: {C['primary']}; color: {C['dark_text']}; }}"
        f"QMenu::separator {{ height: 1px; background: {C['border']}; margin: 4px 10px; }}"
        f"QMenu::indicator:checked {{ width: 8px; height: 8px; border-radius: 4px; "
        f"background: {C['primary']}; margin-left: 6px; }}"
    )

    def _menu_btn(label, icon):
        btn = TopbarButton(f"{icon}  {label}")
        btn.setFixedHeight(38)
        return btn

    # Arquivo
    btn_arq = _menu_btn("Arquivo", "📁")
    m_arq = QMenu(btn_arq)
    m_arq.setStyleSheet(mqss)
    m_arq.addAction("Projetos", window._show_projects_panel)
    m_arq.addAction("Limpar Projeto", window._clear_project)
    m_arq.addSeparator()
    m_arq.addAction("Meus Videos", window._show_video_browser)
    m_arq.addAction("Meus Audios", window._show_audio_browser)
    btn_arq.setMenu(m_arq)
    h.addWidget(btn_arq)

    # Engine
    btn_eng = _menu_btn("Engine", "⚙")
    engine_menu = QMenu(btn_eng)
    engine_menu.setStyleSheet(mqss)
    for eng in ["Local (GPU)", "Local (CPU)", "Wan 2.2 TI2V", None,
                "VACE (Referencia)", "V2V (Refinar)", None, "HuggingFace API"]:
        if eng is None:
            engine_menu.addSeparator()
        else:
            a = engine_menu.addAction(eng, lambda e=eng: window._set_engine(e))
            a.setCheckable(True)
            a.setChecked(eng == window._engine)
    btn_eng.setMenu(engine_menu)
    h.addWidget(btn_eng)
    window._engine_menu = engine_menu

    # Tema
    btn_est = _menu_btn("Tema", "🎨")
    m_est = QMenu(btn_est)
    m_est.setStyleSheet(mqss)
    m_est.addAction("Storyboard",  lambda: window._show_style_tab(0))
    m_est.addAction("Personagens", lambda: window._show_style_tab(1))
    m_est.addAction("Ambientacao", lambda: window._show_style_tab(2))
    btn_est.setMenu(m_est)
    h.addWidget(btn_est)

    # Audio IA
    btn_aia = _menu_btn("Audio IA", "♫")
    m_aia = QMenu(btn_aia)
    m_aia.setStyleSheet(mqss)
    m_aia.addAction("Gerar Audio da Cena",           window._generate_scene_audio)
    m_aia.addAction("Gerar Audio de Todas as Cenas", window._generate_all_audio)
    btn_aia.setMenu(m_aia)
    h.addWidget(btn_aia)

    # Logs
    btn_log = _menu_btn("Logs", "📋")
    m_log = QMenu(btn_log)
    m_log.setStyleSheet(mqss)
    m_log.addAction("Ver Logs", window._open_logs)
    btn_log.setMenu(m_log)
    h.addWidget(btn_log)

    h.addStretch()

    window._status_dot = GlowDot(color=C["track_sfx"])
    h.addWidget(window._status_dot)

    window._project_badge = _ProjectBadge(window.project.name or window.project.id)
    h.addWidget(window._project_badge)

    div2 = QWidget()
    div2.setFixedSize(1, 22)
    div2.setStyleSheet(f"background: {C['glass_border']};")
    h.addWidget(div2)

    window._engine_badge = _EngineBadge(window._engine)
    h.addWidget(window._engine_badge)

    return tb
