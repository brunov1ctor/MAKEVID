"""PanelManager — controlador de troca de painéis com lifecycle."""

from typing import Optional
from PySide6.QtWidgets import QStackedWidget
from PySide6.QtCore import Qt, Signal, QObject

from makevid.qt.panels.panel_registry import PanelRegistry
from makevid.qt.panels.base_panel import BasePanel


class PanelManager(QObject):
    """Gerencia o QStackedWidget do painel esquerdo com lifecycle."""

    panel_changed = Signal(str, str)  # (old_name, new_name)

    def __init__(self, stack: QStackedWidget, parent=None):
        super().__init__(parent)
        self._stack = stack
        self._registry = PanelRegistry()
        self._current_name: Optional[str] = None
        self._prev_name: Optional[str] = None

    @property
    def registry(self) -> PanelRegistry:
        return self._registry

    @property
    def current_name(self) -> Optional[str]:
        return self._current_name

    @property
    def current_widget(self):
        return self._stack.currentWidget()

    def register(self, name: str, factory):
        self._registry.register(name, factory)

    def show(self, name: str, **kwargs):
        """Troca para o painel `name`, chamando on_hide/on_show."""
        panel = self._registry.get(name)
        if panel is None:
            return

        # Adiciona ao stack se ainda não está
        if self._stack.indexOf(panel) == -1:
            self._stack.addWidget(panel)

        # Lifecycle: hide anterior
        old_name = self._current_name
        if old_name and old_name != name:
            old_panel = self._registry.get(old_name)
            if old_panel and isinstance(old_panel, BasePanel):
                old_panel.on_hide()

        # Troca
        self._prev_name = old_name
        self._current_name = name
        self._stack.setCurrentWidget(panel)

        # Lifecycle: show novo
        if isinstance(panel, BasePanel):
            panel.on_show()

        self.panel_changed.emit(old_name or "", name)

    def show_previous(self, fallback: str = "generator"):
        """Volta ao painel anterior."""
        self.show(self._prev_name or fallback)

    def get(self, name: str):
        """Acessa um painel pelo nome (cria se necessário)."""
        return self._registry.get(name)

    def notify_project_changed(self, project):
        """Propaga mudança de projeto para painéis já instanciados."""
        for name, panel in self._registry.instances().items():
            if isinstance(panel, BasePanel):
                panel.on_project_changed(project)
            elif hasattr(panel, '_on_project_changed'):
                panel._on_project_changed(project)
