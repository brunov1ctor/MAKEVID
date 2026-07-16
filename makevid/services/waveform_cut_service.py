"""Waveform Cut Service - Lógica de recorte interativo de regiões de áudio."""

from typing import Optional, Tuple, List


class WaveformCutService:
    """Gerencia múltiplas seleções de recorte e aplica os cortes no item."""

    EDGE_THRESHOLD = 0.04

    def __init__(self):
        self._active_item_id: Optional[str] = None
        # Lista de seleções confirmadas: [(a, b), ...]
        self._selections: List[Tuple[float, float]] = []
        # Seleção em construção
        self._wip_start: Optional[float] = None
        self._wip_end: Optional[float] = None
        self._pending_point: Optional[float] = None  # primeiro clique (modo dois cliques)
        # Drag de borda: (sel_index, "start"|"end")
        self._edge_drag: Optional[Tuple[int, str]] = None

    # ------------------------------------------------------------------
    # Estado de modo
    # ------------------------------------------------------------------

    def activate(self, item_id: str):
        self._active_item_id = item_id
        self._selections = []
        self._wip_start = None
        self._wip_end = None
        self._pending_point = None
        self._edge_drag = None

    def deactivate(self):
        self._active_item_id = None
        self._selections = []
        self._wip_start = None
        self._wip_end = None
        self._pending_point = None
        self._edge_drag = None

    def is_active(self, item_id: str) -> bool:
        return self._active_item_id == item_id

    # ------------------------------------------------------------------
    # Seleção em construção (WIP) — arrasto
    # ------------------------------------------------------------------

    def begin_selection(self, ratio: float):
        self._wip_start = max(0.0, min(1.0, ratio))
        self._wip_end = self._wip_start
        self._pending_point = None

    def update_selection(self, ratio: float):
        if self._wip_start is not None:
            self._wip_end = max(0.0, min(1.0, ratio))

    def commit_wip(self):
        """Confirma a seleção em construção se for válida e não colidir."""
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

    def get_wip(self) -> Tuple[Optional[float], Optional[float]]:
        if self._wip_start is None:
            return None, None
        a, b = sorted((self._wip_start, self._wip_end))
        return a, b

    # ------------------------------------------------------------------
    # Dois cliques para marcar A→B
    # ------------------------------------------------------------------

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
            return True
        return False

    def get_pending_point(self) -> Optional[float]:
        return self._pending_point

    # ------------------------------------------------------------------
    # Drag de borda
    # ------------------------------------------------------------------

    def hit_edge(self, x_ratio: float, hit_px: int, widget_w: int) -> Optional[Tuple[int, str]]:
        """Retorna (sel_index, 'start'|'end') se x_ratio está perto de uma borda."""
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
        self._edge_drag = None

    def is_edge_dragging(self) -> bool:
        return self._edge_drag is not None

    # ------------------------------------------------------------------
    # Colisão
    # ------------------------------------------------------------------

    def _clamp_to_gaps(self, a: float, b: float) -> Tuple[float, float]:
        """Apara [a,b] para não sobrepor seleções existentes."""
        for sa, sb in self._selections:
            # Qualquer sobreposição: corta pelo lado que preserva o início do arrasto
            if a >= sa and a < sb:  # início dentro de uma seleção existente
                return (a, a)       # rejeita
            if b > sa and b <= sb:  # fim dentro de uma seleção existente
                b = sa              # trunca antes da seleção existente
            if a < sa and b > sb:   # engloba uma seleção existente — trunca antes dela
                b = sa
        return (min(a, b), max(a, b))

    def _clamp_edge_start(self, idx: int, new_a: float) -> float:
        """Impede que a borda esquerda invada a seleção anterior."""
        if idx > 0:
            _, prev_b = self._selections[idx - 1]
            new_a = max(new_a, prev_b + 0.005)
        return max(0.0, new_a)

    def _clamp_edge_end(self, idx: int, new_b: float) -> float:
        """Impede que a borda direita invada a próxima seleção."""
        if idx < len(self._selections) - 1:
            next_a, _ = self._selections[idx + 1]
            new_b = min(new_b, next_a - 0.005)
        return min(1.0, new_b)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_selections(self) -> List[Tuple[float, float]]:
        return list(self._selections)

    def has_selection(self) -> bool:
        return len(self._selections) > 0

    def clear_selection(self):
        self._selections = []
        self._wip_start = None
        self._wip_end = None
        self._pending_point = None

    # Compat com código legado que usa get_selection() (singular)
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

    # ------------------------------------------------------------------
    # Aplicar cortes
    # ------------------------------------------------------------------

    def apply_cut(self, item, project, slice_keyframes_fn, commit_fn):
        """Salva as regioes selecionadas como zonas de silencio no item.
        As regioes sao salvas em segundos relativos ao inicio do item.
        """
        if not self._selections:
            return False

        duration = float(getattr(item, 'duration', 1.0))
        existing = list(item.muted_regions) if hasattr(item, 'muted_regions') and item.muted_regions else []
        for a, b in self._selections:
            existing.append({
                "start": round(a * duration, 4),
                "end": round(b * duration, 4),
            })
        item.muted_regions = existing

        commit_fn(item)
        self.deactivate()
        return True
