"""Controlador de recorte de layers — lógica extraída de TrackEditorPanel."""

import logging

from makevid.config import PROJECTS_DIR
from makevid.core.audio_utils import slice_volume_keyframes

_log = logging.getLogger(__name__)


class LayerCutController:
    """Gerencia o ciclo de vida do modo de recorte para um conjunto de layers.

    Recebe referências ao cut_service, ao dict layer_refs e callbacks do painel
    orquestrador — sem dependência direta de widgets Qt.
    """

    def __init__(self, cut_service, layer_refs, commit_fn, changed_signal, playing_dict):
        """
        cut_service   : WaveformCutService
        layer_refs    : dict item_id -> {waveform, cut_btn, cut_confirm, action_row, ...}
        commit_fn     : callable(item) — salva projeto e emite changed
        changed_signal: Signal() do painel
        playing_dict  : dict item_id -> bool (referência ao _playing do painel)
        """
        self._svc      = cut_service
        self._refs     = layer_refs
        self._commit   = commit_fn
        self._changed  = changed_signal
        self._playing  = playing_dict

    # ── toggle mode ───────────────────────────────────────────────────────────

    def toggle_cut_mode(self, item, layer_widget):
        """Ativa ou desativa o modo de recorte interativo na waveform."""
        from makevid.qt.theme import C
        waveform = self._refs.get(item.id, {}).get("waveform")
        if waveform is None:
            return

        if self._svc.is_active(item.id):
            self._svc.deactivate()
            waveform.set_cut_mode(None)
            layer_widget.set_cut_container_mode("idle")
        else:
            self._svc.activate(item.id)
            waveform.set_cut_mode(self._svc)
            waveform.selection_changed.connect(
                lambda: self.on_selection_changed(item, layer_widget)
            )
            layer_widget.set_cut_container_mode("active")

    def on_selection_changed(self, item, layer_widget):
        """Alterna o container entre active e confirm conforme há seleção."""
        if self._svc.has_selection():
            layer_widget.set_cut_container_mode("confirm")
        else:
            layer_widget.set_cut_container_mode("active")

    # ── apply / undo ──────────────────────────────────────────────────────────

    def apply_cut(self, item, waveform, cut_btn, layer_widget):
        """Aplica todos os cortes e restaura o botão Recortar."""
        applied = self._svc.apply_cut(
            item, None,  # project passado via commit_fn
            self._slice_volume_keyframes,
            self._commit,
        )
        if applied:
            layer_widget.set_cut_container_mode("idle")
            waveform._load_waveform()
            waveform.update()

    def undo_selection(self, item, layer_widget):
        """Limpa seleções sem aplicar o corte."""
        self._svc.clear_selection()
        wf = self._refs.get(item.id, {}).get("waveform")
        if wf:
            wf.update()
        layer_widget.set_cut_container_mode("active")

    # ── trim helpers ──────────────────────────────────────────────────────────

    def trim_start(self, item, cut):
        dur = float(item.duration)
        cut = max(0.0, min(dur, float(cut)))
        if cut < 0.05 or cut >= dur - 0.01:
            return
        item.start_time        = round(item.start_time + cut, 3)
        item.duration          = round(max(0.05, dur - cut), 3)
        item.volume_keyframes  = slice_volume_keyframes(item.volume_keyframes, dur, cut, dur)
        self._commit(item)

    def trim_end(self, item, end_at):
        dur    = float(item.duration)
        end_at = max(0.0, min(dur, float(end_at)))
        if end_at <= 0.05 or end_at >= dur - 0.01:
            return
        item.duration         = round(max(0.05, end_at), 3)
        item.volume_keyframes = slice_volume_keyframes(item.volume_keyframes, dur, 0.0, end_at)
        self._commit(item)

    def range_cut(self, item, project, a, b):
        """Remove o trecho [a, b] em segundos, dividindo o layer se necessário."""
        dur = float(item.duration)
        a, b = sorted((float(a), float(b)))
        if b - a < 0.05:
            return

        if a <= 0.01:
            self.trim_start(item, b)
            return
        if b >= dur - 0.01:
            self.trim_end(item, a)
            return

        left_dur  = round(max(0.05, a), 3)
        right_dur = round(max(0.05, dur - b), 3)
        params_b  = dict(item.params)
        left_kf   = self._slice_volume_keyframes(item.volume_keyframes, dur, 0.0, a)
        right_kf  = self._slice_volume_keyframes(item.volume_keyframes, dur, b, dur)

        item.duration         = left_dur
        item.volume_keyframes = left_kf

        new_item = project.add_track_item(
            name=f"{item.name} (parte 2)",
            track=item.track,
            start_time=round(item.start_time + left_dur, 3),
            duration=right_dur,
            file_path=item.file_path,
            params=params_b,
            clip_index=item.clip_index,
        )
        new_item.volume_keyframes = right_kf
        self._commit(item)

    # ── internal ──────────────────────────────────────────────────────────────

    def _slice_volume_keyframes(self, keyframes, duration, seg_start, seg_end):
        return slice_volume_keyframes(keyframes, duration, seg_start, seg_end)
