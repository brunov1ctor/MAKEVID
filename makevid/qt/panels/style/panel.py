"""Style Panel Qt - Shell principal com tabs."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget
)
from PySide6.QtCore import Signal, Qt

from makevid.qt.theme import C
from makevid.qt.panels.style.storyboard import StoryboardMixin
from makevid.qt.panels.style.characters import CharactersMixin
from makevid.qt.panels.style.ambience import AmbienceMixin
from makevid.qt.panels.style.voice_config import VoiceConfigMixin


class StylePanel(StoryboardMixin, CharactersMixin, VoiceConfigMixin, AmbienceMixin, QWidget):
    """Painel de estilo: Storyboard, Personagens, Ambientacao."""

    closed = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setStyleSheet(f"background: {C['panel']};")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QFrame()
        hdr.setFixedHeight(38)
        hdr.setStyleSheet(f"background: {C['card']};")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 0, 6, 0)
        lbl = QLabel("\U0001f3a5 PROJETO")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(30, 26)
        close_btn.setStyleSheet(f"background: transparent; color: #ff4444; font-size: 14pt; font-weight: bold;")
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        layout.addWidget(hdr)

        # Tab bar — estilo abas de navegador
        tab_bar_frame = QFrame()
        tab_bar_frame.setFixedHeight(34)
        tab_bar_frame.setObjectName("styleTabBar")
        tab_bar_frame.setStyleSheet(
            f"QFrame#styleTabBar {{ background: {C['card']}; border: none; "
            f"border-bottom: 2px solid {C['border']}; }}")
        tab_bar_l = QHBoxLayout(tab_bar_frame)
        tab_bar_l.setContentsMargins(8, 0, 8, 0)
        tab_bar_l.setSpacing(0)

        self._style_tab_btns = []
        tab_defs = [
            ("\U0001f3ac", "Storyboard", C['cyan']),
            ("\U0001f464", "Personagens", "#ff9944"),
            ("\U0001f30c", "Ambientação", "#cc44aa"),
        ]
        for i, (icon, label, accent) in enumerate(tab_defs):
            btn = QPushButton(f"{icon} {label}")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("tabIndex", i)
            btn.setProperty("accent", accent)
            btn.clicked.connect(lambda checked=False, idx=i: self._switch_style_tab(idx))
            self._style_tab_btns.append(btn)
            tab_bar_l.addWidget(btn)

        tab_bar_l.addStretch()
        layout.addWidget(tab_bar_frame)

        # Stacked content
        self._style_stack = QStackedWidget()
        self._style_stack.setStyleSheet(f"background: {C['panel']}; border: none;")
        self._style_stack.addWidget(self._build_storyboard_tab())
        self._style_stack.addWidget(self._build_characters_tab())
        self._style_stack.addWidget(self._build_ambience_tab())
        layout.addWidget(self._style_stack)

        self._switch_style_tab(0)

    def _switch_style_tab(self, idx):
        self._style_stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._style_tab_btns):
            accent = btn.property("accent")
            if i == idx:
                # Aba ativa: fundo do painel, borda superior colorida, sem borda inferior
                btn.setStyleSheet(
                    f"QPushButton {{ "
                    f"background: {C['panel']}; color: {accent}; "
                    f"font-size: 9pt; font-weight: bold; "
                    f"border: 1px solid {C['border']}; "
                    f"border-top: 2px solid {accent}; "
                    f"border-bottom: 2px solid {C['panel']}; "
                    f"border-radius: 4px 4px 0 0; "
                    f"padding: 2px 12px; margin-bottom: -2px; }}")
            else:
                # Aba inativa: transparente, discreta
                btn.setStyleSheet(
                    f"QPushButton {{ "
                    f"background: transparent; color: {C['text3']}; "
                    f"font-size: 9pt; font-weight: bold; "
                    f"border: 1px solid transparent; border-bottom: none; "
                    f"border-radius: 4px 4px 0 0; "
                    f"padding: 2px 12px; }}"
                    f"QPushButton:hover {{ color: {accent}; "
                    f"background: {C['card_hover']}; "
                    f"border: 1px solid {C['border']}; "
                    f"border-bottom: none; }}")

    # Helpers compartilhados
    def _gold_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 13pt; font-weight: bold;")
        return lbl

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return lbl

    def _btn_style(self, color):
        return (f"background: {C['card']}; color: {color}; font-weight: bold; "
                f"border: 1px solid {color}; border-radius: 4px; padding: 4px 10px;")

    def _input_qss(self):
        return (
            f"QLineEdit, QComboBox {{ background: {C['input']}; color: {C['cyan']}; "
            f"border: 2px solid {C['border']}; border-radius: 8px; "
            f"padding: 4px 8px; font-family: Consolas; font-size: 11pt; font-weight: bold; }}"
            f"QLineEdit:hover, QComboBox:hover {{ border: 3px solid {C['gold']}; }}"
            f"QLineEdit:focus {{ border: 3px solid {C['gold']}; }}")

    def _mini_label(self, text, color, bold=False):
        lbl = QLabel(text)
        weight = "font-weight: bold;" if bold else ""
        lbl.setStyleSheet(f"color: {color}; font-size: 9pt; {weight} border: none; background: none;")
        return lbl
