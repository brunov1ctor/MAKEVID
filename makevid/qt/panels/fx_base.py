"""FX Editor Base — classe base compartilhada pelos editores de FX."""

import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
from PySide6.QtCore import Qt

from makevid.qt.theme import C

_log = logging.getLogger(__name__)


class FxEditorBase(QWidget):
    """Base para FxFadeEditor e FxGenericEditor.

    Fornece: scroll container, _auto_save, _section_frame,
             _preview_fx, _remove_fx, _build_action_buttons.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project = None
        self._item = None

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none;")
        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)
        self._scroll.setWidget(self._inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    # ── API pública ───────────────────────────────────────────────────────────

    def load(self, item, project=None):
        self._item = item
        self._project = project
        self._clear_layout()
        self._build(item)
        self._layout.addStretch()

    # ── Subclasses implementam ────────────────────────────────────────────────

    def _build(self, item):
        raise NotImplementedError

    # ── Helpers compartilhados ────────────────────────────────────────────────

    def _clear_layout(self):
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _auto_save(self):
        if self._project:
            try:
                from makevid.config import PROJECTS_DIR
                self._project.save(PROJECTS_DIR)
            except Exception:
                _log.exception("Erro ao salvar projeto")

    @staticmethod
    def _param_int(params, key, default=0):
        try:
            return int(params.get(key, default))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _param_float(params, key, default=0.0):
        try:
            return float(params.get(key, default))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _param_color(params, key, default=(0, 0, 0)):
        """Lê 'r,g,b' de params e retorna tupla (r, g, b) com fallback seguro."""
        try:
            parts = str(params.get(key, "")).split(",")
            return tuple(max(0, min(255, int(p))) for p in parts[:3]) if len(parts) == 3 else default
        except (ValueError, TypeError):
            return default

    def _section_frame(self, title):
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 10px; }}"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 8, 10, 10)
        fl.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        fl.addWidget(lbl)
        return frame

    def _build_action_buttons(self, item):
        btn_preview = QPushButton("▶  PREVIEW")
        btn_preview.setFixedHeight(30)
        btn_preview.setStyleSheet(
            f"background: {C['card']}; color: {C['purple']}; font-weight: bold; "
            f"border: 2px solid {C['purple']}; border-radius: 6px;"
        )
        btn_preview.clicked.connect(lambda: self._preview_fx(item))
        self._layout.addWidget(btn_preview)

        btn_remove = QPushButton("REMOVER FX")
        btn_remove.setFixedHeight(28)
        btn_remove.setStyleSheet(
            f"background: {C['danger_bg']}; color: {C['danger']}; font-weight: bold; "
            f"border: 1px solid {C['danger']}; border-radius: 6px;"
        )
        btn_remove.clicked.connect(lambda: self._remove_fx(item))
        self._layout.addWidget(btn_remove)

    def _preview_fx(self, item):
        try:
            app = self.window()
            app.timeline.set_playhead(item.start_time)
            app.preview._on_display_click(None)
        except Exception:
            _log.exception("Erro ao fazer preview do FX")

    def _remove_fx(self, item):
        if not (self._project and item):
            return
        try:
            from makevid.config import PROJECTS_DIR
            self._project.remove_track_item(item.id)
            self._project.save(PROJECTS_DIR)
            app = self.window()
            app.timeline.redraw()
            app._show_generator()
        except Exception:
            _log.exception("Erro ao remover FX")
