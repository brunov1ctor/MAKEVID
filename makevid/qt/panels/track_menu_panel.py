"""Track Menu Panel Qt - Menu de opcoes por track (ao clicar no label lateral)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from makevid.qt.theme import C
from makevid.config import AUDIO_DIR, PROJECTS_DIR
from makevid.data.fx_definitions import FX_TABS, FX_TAB_TOOLTIPS


TRACK_CONFIG = {
    "voice": (lambda: C["track_voice"], "\U0001f3a4 VOZ", [
        ("\U0001f4c2 Importar Voz", "WAV, MP3", "import"),
        ("\U0001f3a7 Gravar", "Gravar microfone", "record"),
        ("\U0001f5e3 Gerar TTS", "Texto para fala (edge-tts)", "tts"),
    ]),
    "sfx": (lambda: C["track_sfx"], "\U0001f50a SFX", [
        ("\U0001f4c2 Importar SFX", "WAV, MP3, OGG", "import"),
        ("\U0001f3a7 Gravar", "Gravar microfone", "record"),
    ]),
    "music": (lambda: C["track_music"], "\U0001f3b5 MUSICA", [
        ("\U0001f4c2 Importar Musica", "WAV, MP3, OGG", "import"),
    ]),
    "audio": (lambda: C["track_audio"], "\U0001f3a7 AUDIO", [
        ("\U0001f4c2 Importar Audio", "MP3, WAV, OGG", "import"),
        ("\U0001f3a7 Gravar", "Gravar microfone", "record"),
    ]),
}


def _mix(base_hex: str, tint_hex: str, t: float = 0.14) -> str:
    """Mistura base com tint em proporção t (0-1). Retorna hex."""
    b = QColor(base_hex)
    c = QColor(tint_hex)
    r = int(b.red()   * (1 - t) + c.red()   * t)
    g = int(b.green() * (1 - t) + c.green() * t)
    bl = int(b.blue()  * (1 - t) + c.blue()  * t)
    return QColor(r, g, bl).name()


class TrackMenuPanel(QWidget):
    """Menu de opcoes ao clicar no label lateral de uma track."""

    closed = Signal()
    action_import = Signal(str)
    action_record = Signal(str)
    action_tts = Signal()
    action_clear = Signal(str)
    action_add_fx = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setObjectName("trackMenuPanel")
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)
        self._content_host = None
        self._content_layout = None
        self._fx_tab_buttons = []
        self._fx_content_area = None
        self._apply_bg(C["glass"])
        self._reset_content_host()

    def _apply_bg(self, color_hex: str):
        """Aplica cor de fundo via stylesheet — garante repaint imediato."""
        mixed = _mix(C["glass"], color_hex)
        self.setStyleSheet(
            f"QWidget#trackMenuPanel {{ background: {mixed}; }}"
            f"QScrollArea {{ background: transparent; border: none; }}"
            f"QWidget {{ background: transparent; }}"
        )

    def _reset_content_host(self):
        if self._content_host is not None:
            self._outer.removeWidget(self._content_host)
            self._content_host.hide()
            self._content_host.deleteLater()

        from PySide6.QtWidgets import QWidget
        self._content_host = QWidget(self)
        self._content_host.setAttribute(Qt.WA_TranslucentBackground)
        self._content_host.setAutoFillBackground(False)
        self._content_layout = QVBoxLayout(self._content_host)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._outer.addWidget(self._content_host)

    def show_track(self, track_name, project):
        # Se já está mostrando a mesma track, não reconstrói
        if getattr(self, '_track', None) == track_name and getattr(self, '_project', None) is project:
            return

        self._track = track_name
        self._project = project

        self._reset_content_host()

        # Aplicar cor de fundo
        cfg = TRACK_CONFIG.get(track_name)
        if cfg:
            self._apply_bg(cfg[0]())
        elif track_name == "fx":
            self._apply_bg(C["purple"])
        elif track_name == "video":
            self._apply_bg(C["blue"])
        else:
            self._apply_bg(C["glass"])

        if track_name == "fx":
            self._build_fx_menu()
        else:
            self._build_audio_menu(track_name)

    def _build_audio_menu(self, track_name):
        config = TRACK_CONFIG.get(track_name)
        if not config:
            return
        color_fn, title, items = config
        color = color_fn()
        L = self._content_layout

        hdr = QWidget()
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(10, 6, 10, 4)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: bold;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        L.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(10, 6, 10, 10)
        cl.setSpacing(4)

        info = QLabel("Clique para adicionar na track")
        info.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        cl.addWidget(info)

        grid = QGridLayout()
        grid.setSpacing(6)
        for idx, (name, desc, action_type) in enumerate(items):
            item_frame = QFrame()
            item_frame.setObjectName("trackItem")
            item_frame.setStyleSheet(
                f"QFrame#trackItem {{ background: {color}; border: 2px solid {color}; border-radius: 6px; }}"
                f"QFrame#trackItem:hover {{ background: {C['secondary']}; border-color: {C['secondary']}; }}")
            il = QVBoxLayout(item_frame)
            il.setContentsMargins(10, 6, 10, 6)
            n_lbl = QLabel(name)
            n_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            n_lbl.setStyleSheet(f"color: {C['dark_text']}; font-size: 10pt; font-weight: bold;")
            il.addWidget(n_lbl)
            d_lbl = QLabel(desc)
            d_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            d_lbl.setStyleSheet(f"color: rgba(11,18,32,0.75); font-size: 8pt;")
            il.addWidget(d_lbl)

            if action_type == "import":
                item_frame.mousePressEvent = lambda e, t=track_name: self.action_import.emit(t)
            elif action_type == "record":
                item_frame.mousePressEvent = lambda e, t=track_name: self.action_record.emit(t)
            elif action_type == "tts":
                item_frame.mousePressEvent = lambda e: self.action_tts.emit()

            item_frame.setCursor(Qt.PointingHandCursor)
            grid.addWidget(item_frame, idx // 2, idx % 2)
        cl.addLayout(grid)
        cl.addStretch()
        scroll.setWidget(content)
        L.addWidget(scroll)

        clear_btn = QPushButton("Limpar Track")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['danger']}; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid {C['danger']}; border-radius: 4px; padding: 4px 12px; margin: 4px 10px; }}"
            f"QPushButton:hover {{ background: {C['danger_bg']}; }}")
        clear_btn.clicked.connect(lambda: self.action_clear.emit(track_name))
        L.addWidget(clear_btn)

    def _build_fx_menu(self):
        color = C["purple"]
        L = self._content_layout

        hdr = QWidget()
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(10, 6, 10, 4)
        lbl = QLabel("EFEITOS")
        lbl.setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: bold;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        L.addWidget(hdr)

        tabs_bar = QWidget()
        tabs_bar.setFixedHeight(36)
        tabs_bar.setStyleSheet(f"background: {C['card']}; border-radius: 4px;")
        tabs_h = QHBoxLayout(tabs_bar)
        tabs_h.setContentsMargins(4, 4, 4, 4)
        tabs_h.setSpacing(2)

        self._fx_tab_buttons = []
        tab_keys = list(FX_TABS.keys())
        for key in tab_keys:
            tab = FX_TABS[key]
            btn = QPushButton(f"{tab['icon']} {tab['label']}")
            btn.setFixedHeight(26)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
                f"font-weight: bold; border: none; border-radius: 3px; padding: 2px 6px; }}"
                f"QPushButton:hover {{ background: {C['card_hover']}; }}")
            btn.clicked.connect(lambda checked=False, k=key: self._select_fx_tab(k))
            tabs_h.addWidget(btn)
            self._fx_tab_buttons.append((key, btn))
            tip = FX_TAB_TOOLTIPS.get(key, "")
            if tip:
                btn.setToolTip(tip)
        L.addWidget(tabs_bar)

        self._fx_content_area = QScrollArea()
        self._fx_content_area.setWidgetResizable(True)
        L.addWidget(self._fx_content_area)

        clear_btn = QPushButton("Limpar Track")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['danger']}; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid {C['danger']}; border-radius: 4px; padding: 4px 12px; margin: 4px 10px; }}"
            f"QPushButton:hover {{ background: {C['danger_bg']}; }}")
        clear_btn.clicked.connect(lambda: self.action_clear.emit("fx"))
        L.addWidget(clear_btn)

        self._select_fx_tab(tab_keys[0])

    def _select_fx_tab(self, selected_key):
        color = C["purple"]
        for key, btn in self._fx_tab_buttons:
            if key == selected_key:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {color}; color: {C['text']}; font-size: 8pt; "
                    f"font-weight: bold; border: none; border-radius: 3px; padding: 2px 6px; }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
                    f"font-weight: bold; border: none; border-radius: 3px; padding: 2px 6px; }}"
                    f"QPushButton:hover {{ background: {C['card_hover']}; }}")

        tab = FX_TABS[selected_key]
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.setSpacing(4)

        grid = QGridLayout()
        grid.setSpacing(4)
        for idx, (name, desc) in enumerate(tab["items"]):
            item_frame = QFrame()
            item_frame.setObjectName("fxItem")
            item_frame.setStyleSheet(
                f"QFrame#fxItem {{ background: {color}; border: 2px solid {color}; border-radius: 5px; }}"
                f"QFrame#fxItem:hover {{ background: {C['secondary']}; border-color: {C['secondary']}; }}")
            il = QVBoxLayout(item_frame)
            il.setContentsMargins(8, 5, 8, 5)
            n_lbl = QLabel(name)
            n_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            n_lbl.setStyleSheet(f"color: {C['dark_text']}; font-size: 9pt; font-weight: bold;")
            il.addWidget(n_lbl)
            d_lbl = QLabel(desc)
            d_lbl.setWordWrap(True)
            d_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            d_lbl.setStyleSheet(f"color: rgba(11,18,32,0.75); font-size: 8pt;")
            il.addWidget(d_lbl)
            item_frame.setCursor(Qt.PointingHandCursor)
            item_frame.mousePressEvent = lambda e, n=name: self._add_fx(n)
            grid.addWidget(item_frame, idx // 2, idx % 2)
        cl.addLayout(grid)
        cl.addStretch()
        self._fx_content_area.setWidget(content)

    def _add_fx(self, name):
        self.action_add_fx.emit(name)
