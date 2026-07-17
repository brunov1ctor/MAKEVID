"""Waveform Cut Service - Lógica de recorte interativo de regiões de áudio."""

import logging
from typing import Optional, Tuple, List

_log = logging.getLogger(__name__)


class WaveformCutService:
    """Gerencia múltiplas seleções de recorte e aplica os cortes no item."""

    EDGE_THRESHOLD = 0.04

    def __init__(self):
        self._active_item_id: Optional[str] = None
        self._selections: List[Tuple[float, float]] = []
        self._wip_start: Optional[float] = None
        self._wip_end: Optional[float] = None
        self._pending_point: Optional[float] = None
        self._edge_drag: Optional[Tuple[int, str]] = None

    def activate(self, item_id: str):
        self._active_item_id = item_id
        self._selections = []
        self._wip_start = None
        self._wip_end = None
        self._pending_point = None
        self._edge_drag = None
        _log.info("RECORTE ativado | item=%s", item_id)

    def deactivate(self):
        self._active_item_id = None
        self._selections = []
        self._wip_start = None
        self._wip_end = None
        self._pending_point = None
        self._edge_drag = None

    def is_active(self, item_id: str) -> bool:
        return self._active_item_id == item_id

    def begin_selection(self, ratio: float):
        self._wip_start = max(0.0, min(1.0, ratio))
        self._wip_end = self._wip_start
        self._pending_point = None

    def update_selection(self, ratio: float):
        if self._wip_start is not None:
            self._wip_end = max(0.0, min(1.0, ratio))

    def commit_wip(self):
        if self._wip_start is None or self._wip_end is None:
            return
        a, b = sorted((self._wip_start, self._wip_end))
        self._wip_start = None
        self._wip_end = None
        if b - a < 0.01:
            return
        a, b = self._clamp_to_gaps(a, b)
        if b - a >= 0.01:
            self._selections.append((a, b))
            self._selections.sort(key=lambda s: s[0])
            _log.info("RECORTE seleção adicionada: %.2f→%.2f | total=%d", a, b, len(self._selections))

    def get_wip(self) -> Tuple[Optional[float], Optional[float]]:
        if self._wip_start is None:
            return None, None
        a, b = sorted((self._wip_start, self._wip_end))
        return a, b

    def click_point(self, ratio: float) -> bool:
        ratio = max(0.0, min(1.0, ratio))
        if self._pending_point is None:
            self._pending_point = ratio
            return False
        a, b = sorted((self._pending_point, ratio))
        self._pending_point = None
        if b - a < 0.01:
            return False
        a, b = self._clamp_to_gaps(a, b)
        if b - a >= 0.01:
            self._selections.append((a, b))
            self._selections.sort(key=lambda s: s[0])
            _log.info("RECORTE seleção (2 cliques): %.2f→%.2f | total=%d", a, b, len(self._selections))
            return True
        return False

    def get_pending_point(self) -> Optional[float]:
        return self._pending_point

    def hit_edge(self, x_ratio: float, hit_px: int, widget_w: int) -> Optional[Tuple[int, str]]:
        threshold = hit_px / max(1, widget_w)
        for i, (a, b) in enumerate(self._selections):
            if abs(x_ratio - a) <= threshold:
                return (i, "start")
            if abs(x_ratio - b) <= threshold:
                return (i, "end")
        return None

    def begin_edge_drag(self, sel_index: int, edge: str):
        self._edge_drag = (sel_index, edge)

    def update_edge_drag(self, ratio: float):
        if self._edge_drag is None:
            return
        idx, edge = self._edge_drag
        if idx >= len(self._selections):
            return
        a, b = self._selections[idx]
        ratio = max(0.0, min(1.0, ratio))
        if edge == "start":
            new_a = min(ratio, b - 0.01)
            new_a = self._clamp_edge_start(idx, new_a)
            self._selections[idx] = (new_a, b)
        else:
            new_b = max(ratio, a + 0.01)
            new_b = self._clamp_edge_end(idx, new_b)
            self._selections[idx] = (a, new_b)

    def end_edge_drag(self):
        if self._edge_drag and self._edge_drag[0] < len(self._selections):
            idx = self._edge_drag[0]
            a, b = self._selections[idx]
            _log.info("RECORTE borda ajustada [%d]: %.2f→%.2f", idx, a, b)
        self._edge_drag = None

    def is_edge_dragging(self) -> bool:
        return self._edge_drag is not None

    def _clamp_to_gaps(self, a: float, b: float) -> Tuple[float, float]:
        for sa, sb in self._selections:
            if a >= sa and a < sb:
                return (a, a)
            if b > sa and b <= sb:
                b = sa
            if a < sa and b > sb:
                b = sa
        return (min(a, b), max(a, b))

    def _clamp_edge_start(self, idx: int, new_a: float) -> float:
        if idx > 0:
            _, prev_b = self._selections[idx - 1]
            new_a = max(new_a, prev_b + 0.005)
        return max(0.0, new_a)

    def _clamp_edge_end(self, idx: int, new_b: float) -> float:
        if idx < len(self._selections) - 1:
            next_a, _ = self._selections[idx + 1]
            new_b = min(new_b, next_a - 0.005)
        return min(1.0, new_b)

    def get_selections(self) -> List[Tuple[float, float]]:
        return list(self._selections)

    def has_selection(self) -> bool:
        return len(self._selections) > 0

    def undo_last(self) -> bool:
        if self._wip_start is not None:
            self._wip_start = None
            self._wip_end = None
            return True
        if self._pending_point is not None:
            self._pending_point = None
            return True
        if self._selections:
            self._selections.pop()
            return True
        return False

    def clear_selection(self):
        self._selections = []
        self._wip_start = None
        self._wip_end = None
        self._pending_point = None

    def get_selection(self) -> Tuple[Optional[float], Optional[float]]:
        if not self._selections:
            return None, None
        return self._selections[0]

    def touches_start(self) -> bool:
        if not self._selections:
            return False
        return self._selections[0][0] <= self.EDGE_THRESHOLD

    def touches_end(self) -> bool:
        if not self._selections:
            return False
        return self._selections[-1][1] >= (1.0 - self.EDGE_THRESHOLD)

    def apply_cut(self, item, project, slice_keyframes_fn, commit_fn):
        if not self._selections:
            _log.warning("RECORTE apply_cut sem seleções ativas")
            return False

        file_duration = float(item.params.get('file_duration', 0.0)) or float(getattr(item, 'duration', 1.0))
        existing = list(item.muted_regions) if hasattr(item, 'muted_regions') and item.muted_regions else []
        for a, b in self._selections:
            existing.append({
                "start": round(a * file_duration, 4),
                "end":   round(b * file_duration, 4),
            })
        item.muted_regions = existing
        item.params['file_duration'] = str(round(file_duration, 4))

        if getattr(item, 'clip_index', -1) < 0:
            total_muted = sum(
                max(0.0, float(r['end']) - float(r['start']))
                for r in existing
            )
            item.duration = max(0.05, round(file_duration - total_muted, 3))

        _log.info(
            "RECORTE aplicado | item=%s | %d corte(s) | duration=%.2fs",
            item.id, len(self._selections), item.duration,
        )
        commit_fn(item)
        self.deactivate()
        return True
