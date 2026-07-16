"""Registry de painéis — mapeia nomes a factories com lazy loading."""

from typing import Callable, Dict, Optional
from PySide6.QtWidgets import QWidget


class PanelRegistry:
    """Registra factories de painéis. Instancia sob demanda e cacheia."""

    def __init__(self):
        self._factories: Dict[str, Callable[[], QWidget]] = {}
        self._instances: Dict[str, QWidget] = {}

    def register(self, name: str, factory: Callable[[], QWidget]):
        self._factories[name] = factory

    def get(self, name: str) -> Optional[QWidget]:
        """Retorna instância (cria na primeira vez)."""
        if name in self._instances:
            return self._instances[name]
        factory = self._factories.get(name)
        if factory is None:
            return None
        instance = factory()
        self._instances[name] = instance
        return instance

    def is_loaded(self, name: str) -> bool:
        return name in self._instances

    def names(self):
        return list(self._factories.keys())

    def instances(self):
        return dict(self._instances)
