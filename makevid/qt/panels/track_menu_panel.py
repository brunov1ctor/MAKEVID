"""Track Menu Panel Qt - Menu de opcoes por track (ao clicar no label lateral)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog
)
from PySide6.QtCore import Qt, Signal
import shutil
from pathlib import Path

from makevid.qt.theme import C
from makevid.config import AUDIO_DIR, PROJECTS_DIR
from makevid.data.fx_definitions import FX_TABS, FX_TAB_TOOLTIPS


TRACK_CONFIG = {
    "voice": ("#ff9944", "\U0001f3a4 VOZ", [
        ("\U0001f4c2 Importar Voz", "WAV, MP3", "import"),
        ("\U0001f3a7 Gravar", "Gravar microfone", "record"),
        ("\U0001f5e3 Gerar TTS", "Texto para fala (edge-tts)", "tts"),
    ]),
    "sfx": ("#44cc88", "\U0001f50a SFX", [
        ("\U0001f4c2 Importar SFX", "WAV, MP3, OGG", "import"),
        ("\U0001f3a7 Gravar", "Gravar microfone", "record"),
    ]),
    "music": ("#cc44aa", "\U0001f3b5 MUSICA", [
        ("\U0001f4c2 Importar Musica", "WAV, MP3, OGG", "import"),
    ]),
    "audio": ("#0ac8b9", "\U0001f3a7 AUDIO", [
        ("\U0001f4c2 Importar Audio", "MP3, WAV, OGG", "import"),
        ("\U0001f3a7 Gravar", "Gravar microfone", "record"),
    ]),
}


class TrackMenuPanel(QWidget):
    """Menu de opcoes ao clicar no label lateral de uma track."""

    closed = Signal()
    action_import = Signal(str)   # emite track_name
    action_record = Signal(str)   # emite track_name
    action_tts = Signal()
    action_clear = Signal(str)    # emite track_name
    action_add_fx = Signal(str)    # emite fx_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setObjectName("trackMenuPanel")
        self.setStyleSheet(f"QWidget#trackMenuPanel {{ background-color: {C['panel']}; }}")
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)
    def show_track(self, track_name, project):
        """Mostra menu para a track especificada."""
        self._track = track_name
        self._project = project

        # Limpar
        while self._outer.count():
            child = self._outer.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                sub = child.layout()
                while sub.count():
                    item = sub.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

        if track_name == "fx":
            self._build_fx_menu()
        else:
            self._build_audio_menu(track_name)

        self.show()

    def _build_audio_menu(self, track_name):
        config = TRACK_CONFIG.get(track_name)
        if not config:
            return
        color, title, items = config

        L = self._outer

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 6, 10, 4)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: bold; background: transparent; border: none;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        L.addLayout(hdr_l)

        # Scroll com opcoes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(10, 6, 10, 10)
        cl.setSpacing(4)

        info = QLabel("Clique para adicionar na track")
        info.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; border: none;")
        cl.addWidget(info)

        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(6)
        for idx, (name, desc, action_type) in enumerate(items):
            item_frame = QFrame()
            item_frame.setObjectName("trackItem")
            item_frame.setStyleSheet(
                f"QFrame#trackItem {{ background: {color}; border: 2px solid {color}; border-radius: 6px; }}"
                f"QFrame#trackItem:hover {{ background: #ffd700; border-color: #ffd700; }}")
            il = QVBoxLayout(item_frame)
            il.setContentsMargins(10, 6, 10, 6)
            n_lbl = QLabel(name)
            n_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            n_lbl.setStyleSheet(f"color: #0a0a0f; font-size: 10pt; font-weight: bold; border: none; background: transparent;")
            il.addWidget(n_lbl)
            d_lbl = QLabel(desc)
            d_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            d_lbl.setStyleSheet(f"color: #1a1a2a; font-size: 8pt; border: none; background: transparent;")
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

        # Limpar Track button (embaixo de tudo)
        clear_btn = QPushButton("Limpar Track")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: #ff4444; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid #ff4444; border-radius: 4px; padding: 4px 12px; margin: 4px 10px; }}"
            f"QPushButton:hover {{ background: #2a0808; border-color: #ff6666; color: #ff6666; }}")
        clear_btn.clicked.connect(lambda: self.action_clear.emit(track_name))
        L.addWidget(clear_btn)

    def _build_fx_menu(self):
        """Menu de FX com abas por categoria."""
        color = C["purple"]
        L = self._outer

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 6, 10, 4)
        lbl = QLabel("EFEITOS")
        lbl.setStyleSheet(f"color: {color}; font-size: 13pt; font-weight: bold; background: transparent; border: none;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        L.addLayout(hdr_l)

        # Abas de FX
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(10, 6, 10, 10)
        cl.setSpacing(6)

        from PySide6.QtWidgets import QGridLayout

        for key, tab in FX_TABS.items():
            # Titulo da categoria
            cat_lbl = QLabel(f"{tab['icon']} {tab['label']}")
            cat_lbl.setStyleSheet(f"color: {color}; font-size: 10pt; font-weight: bold; border: none;")
            cl.addWidget(cat_lbl)

            grid = QGridLayout()
            grid.setSpacing(4)
            for idx, (name, desc) in enumerate(tab["items"]):
                item_frame = QFrame()
                item_frame.setObjectName("fxItem")
                item_frame.setStyleSheet(
                    f"QFrame#fxItem {{ background: {color}; border: 2px solid {color}; border-radius: 5px; }}"
                    f"QFrame#fxItem:hover {{ background: #bb77ff; border-color: #bb77ff; }}")
                il = QVBoxLayout(item_frame)
                il.setContentsMargins(8, 5, 8, 5)
                n_lbl = QLabel(name)
                n_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                n_lbl.setStyleSheet(f"color: #0a0a0f; font-size: 9pt; font-weight: bold; border: none; background: transparent;")
                il.addWidget(n_lbl)
                d_lbl = QLabel(desc)
                d_lbl.setWordWrap(True)
                d_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                d_lbl.setStyleSheet(f"color: #1a1a2a; font-size: 8pt; border: none; background: transparent;")
                il.addWidget(d_lbl)
                item_frame.setCursor(Qt.PointingHandCursor)
                item_frame.mousePressEvent = lambda e, n=name: self._add_fx(n)
                grid.addWidget(item_frame, idx // 2, idx % 2)
            cl.addLayout(grid)

        cl.addStretch()
        scroll.setWidget(content)
        L.addWidget(scroll)

        # Limpar Track button (embaixo de tudo)
        clear_btn = QPushButton("Limpar Track")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: #ff4444; font-weight: bold; font-size: 10pt; "
            f"border: 1px solid #ff4444; border-radius: 4px; padding: 4px 12px; margin: 4px 10px; }}"
            f"QPushButton:hover {{ background: #2a0808; border-color: #ff6666; color: #ff6666; }}")
        clear_btn.clicked.connect(lambda: self.action_clear.emit("fx"))
        L.addWidget(clear_btn)

    def _add_fx(self, name):
        """Adiciona FX item na timeline na posicao do playhead."""
        self.action_add_fx.emit(name)
