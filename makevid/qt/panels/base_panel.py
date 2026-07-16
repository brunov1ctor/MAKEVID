"""Base classes para painéis com lifecycle e transparência embutida."""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal


class BasePanel(QWidget):
    """Painel base com ciclo de vida controlado pelo PanelManager."""

    closed = Signal()

    def on_show(self):
        """Chamado quando o painel se torna visível."""
        pass

    def on_hide(self):
        """Chamado quando o painel é ocultado."""
        pass

    def on_project_changed(self, project):
        """Chamado quando o projeto muda."""
        pass

    def on_theme_changed(self):
        """Chamado quando o tema muda."""
        pass

    def cleanup(self):
        """Libera recursos pesados."""
        pass


class GlassPanelBase(BasePanel):
    """BasePanel que já nasce transparente — substitui _make_transparent()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
