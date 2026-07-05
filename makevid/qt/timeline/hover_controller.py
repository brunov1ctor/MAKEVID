"""Hover controller - estado de hover isolado da TimelineScene.

Responsabilidade única: identificar item/track sob o mouse,
atualizar destaque visual e evitar tocar em objetos Qt inválidos.
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
        if not self._is_valid(prev):
            prev = None
            self._hovered_item = None

        if item is prev:
            if item is not None and pos is not None:
                self._update_cursor(item, pos)
            return

        self._clear_item_hover(prev)
        self._hovered_item = item
        if item and hasattr(item, '_hovered') and self._is_valid(item):
            item._hovered = True
            self._update_cursor(item, pos)
            item.update()

    def _resolve_hover_item(self, pos):
        if pos is None:
            return None
        for item in self.scene.items(pos):
            while item and item.parentItem():
                item = item.parentItem()
            if not self._is_valid(item):
                continue
            if hasattr(item, '_hovered'):
                return item
        return None

    def _clear_item_hover(self, item):
        if not item or not hasattr(item, '_hovered'):
            return
        if not self._is_valid(item):
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

    def _update_cursor(self, item, pos):
        from makevid.qt.timeline.clip_item import ClipGraphicsItem
        from makevid.qt.timeline.track_item import TrackGraphicsItem
        # Converte pos de cena para local do item
        local_x = pos.x() - item.pos().x()
        w = getattr(item, '_w', None)
        if w is not None and isinstance(item, (ClipGraphicsItem, TrackGraphicsItem)):
            item.setCursor(Qt.SizeHorCursor if local_x <= 8 or (w - local_x) <= 8 else Qt.ArrowCursor)
        else:
            item.setCursor(Qt.ArrowCursor)

    def _is_valid(self, obj):
        try:
            return obj is not None and shiboken6.isValid(obj)
        except Exception:
            return False
