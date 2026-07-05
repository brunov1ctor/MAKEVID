"""Hover controller - estado de hover isolado da TimelineScene.

Mantem responsabilidade unica: identificar item/track sob o mouse,
atualizar destaque visual e evitar tocar em objetos Qt invalidos.
"""

from PySide6.QtCore import Qt
import shiboken6


class HoverController:
    def __init__(self, scene):
        self.scene = scene
        self._hovered_item = None
        self._hovered_track_key = None

    def reset(self):
        self.clear()

    def clear(self):
        self._set_hovered_track(None)
        self._clear_item_hover(self._hovered_item)
        self._hovered_item = None

    def update(self, pos):
        # Coluna de labels não recebe hover dinâmico.
        if pos is not None and pos.x() < self.scene.tl.LBL_W:
            self._set_hovered_track(None)
            self._clear_item_hover(self._hovered_item)
            self._hovered_item = None
            return

        item = self._resolve_hover_item(pos)
        hovering_rect_item = bool(item) and (hasattr(item, 'track_item') or hasattr(item, 'clip'))
        hovered_track = None if hovering_rect_item else self.scene._track_key_at_pos(pos)
        self._set_hovered_track(hovered_track)

        prev = self._hovered_item
        if not self._is_valid_qobj(prev):
            prev = None
            self._hovered_item = None

        if item is prev:
            if item is not None and pos is not None:
                self.scene._update_item_cursor(item, pos)
            return

        self._clear_item_hover(prev)
        self._hovered_item = item
        if item and hasattr(item, '_hovered') and self._is_valid_qobj(item):
            item._hovered = True
            if pos is not None:
                self.scene._update_item_cursor(item, pos)
            item.update()

    def _resolve_hover_item(self, pos):
        if pos is None:
            return None

        item = self.scene.itemAt(pos, self.scene.tl._view.transform())
        while item and item.parentItem():
            item = item.parentItem()

        if item and not item.acceptHoverEvents():
            return None
        if not self._is_valid_qobj(item):
            return None
        return item

    def _clear_item_hover(self, item):
        if not item or not hasattr(item, '_hovered'):
            return
        if not self._is_valid_qobj(item):
            return
        item._hovered = False
        item.setCursor(Qt.ArrowCursor)
        item.update()

    def _set_hovered_track(self, track_key):
        if self._hovered_track_key == track_key:
            return
        self._hovered_track_key = track_key
        for key, bg in self.scene._bg_items.items():
            bg.set_hovered(key == track_key)

    def _is_valid_qobj(self, obj):
        try:
            return obj is not None and shiboken6.isValid(obj)
        except Exception:
            return False
