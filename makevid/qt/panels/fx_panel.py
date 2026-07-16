"""FX Panel — orquestrador: browser de efeitos + editor de item FX."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget
from PySide6.QtCore import Qt, Signal

from makevid.qt.theme import C
from makevid.qt.panels.fx_browser import FxBrowser
from makevid.qt.panels.fx_fade_editor import FxFadeEditor
from makevid.qt.panels.fx_generic_editor import FxGenericEditor


class FxPanel(QWidget):
    """Painel de efeitos: alterna entre browser e editor de item."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setObjectName("fxPanel")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setContentsMargins(10, 6, 6, 4)
        self._title = QLabel("EFEITOS")
        self._title.setStyleSheet(
            f"color: {C['purple']}; font-size: 13pt; font-weight: bold; background: transparent; border: none;"
        )
        hdr.addWidget(self._title)
        hdr.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(close_btn)
        layout.addLayout(hdr)

        # ── Stack: browser | fade editor | generic editor ─────────────────────
        self._stack = QStackedWidget()

        self._browser = FxBrowser()
        self._browser.fx_clicked.connect(self._on_fx_clicked)

        self._fade_editor = FxFadeEditor()
        self._generic_editor = FxGenericEditor()

        self._stack.addWidget(self._browser)
        self._stack.addWidget(self._fade_editor)
        self._stack.addWidget(self._generic_editor)

        layout.addWidget(self._stack)
        self._stack.setCurrentWidget(self._browser)

    # ── API pública ───────────────────────────────────────────────────────────

    def show_item(self, item, project=None):
        """Mostra editor do item FX selecionado na timeline."""
        self._title.setText(f"FX: {item.name}")
        name_lower = item.name.lower()
        if "fade" in name_lower or "flash" in name_lower:
            self._fade_editor.load(item, project)
            self._stack.setCurrentWidget(self._fade_editor)
        else:
            self._generic_editor.load(item, project)
            self._stack.setCurrentWidget(self._generic_editor)

    def show_browser(self):
        """Volta para o grid de seleção de efeitos."""
        self._title.setText("EFEITOS")
        self._stack.setCurrentWidget(self._browser)

    # ── Interno ───────────────────────────────────────────────────────────────

    def _on_fx_clicked(self, name):
        from makevid.qt.app import MakeVidWindow
        app = self.window()
        if isinstance(app, MakeVidWindow):
            app._add_fx_to_timeline(name)
