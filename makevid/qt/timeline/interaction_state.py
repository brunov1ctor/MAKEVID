"""Estado de interação da timeline.

Responsabilidade única: armazenar estado transitório de drag/seleção
da interação de mouse sem misturar com regras de negócio.
"""

from dataclasses import dataclass


@dataclass
class DragState:
    mode: str | None = None
    target: object | None = None
    start_x: float = 0.0
    orig: float = 0.0
    orig_start: float = 0.0
    group: object | None = None
    ghost_pos: int | None = None
    clip_item: object | None = None
    clip_orig_x: float = 0.0

    def reset(self):
        self.mode = None
        self.target = None
        self.start_x = 0.0
        self.orig = 0.0
        self.orig_start = 0.0
        self.group = None
        self.ghost_pos = None
        self.clip_item = None
        self.clip_orig_x = 0.0
