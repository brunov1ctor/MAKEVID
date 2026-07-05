"""Estado de seleção da timeline."""

from dataclasses import dataclass


@dataclass
class SelectionState:
    selected_clip_id: str | None = None
    selected_track_item_id: str | None = None
    active_track_key: str | None = None

    def clear_clip(self):
        self.selected_clip_id = None

    def clear_track_item(self):
        self.selected_track_item_id = None

    def clear_active_track(self):
        self.active_track_key = None
