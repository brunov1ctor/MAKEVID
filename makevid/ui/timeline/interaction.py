"""Interaction - Click, drag, hover, split da timeline."""

from makevid.ui.theme import C


class TimelineInteraction:
    """Gerencia toda interacao do mouse com a timeline."""

    def __init__(self, timeline):
        self.tl = timeline

    def on_click(self, event):
        tl = self.tl
        tl.canvas.focus_set()  # Foco para receber teclas
        pps = tl.zoom
        lbl_w = tl.LBL_W

        # Audio split mode - cortar faixa de audio onde clicar
        if tl._audio_split_mode and event.x >= lbl_w:
            x = (event.x - lbl_w) + tl.scroll_x
            y = event.y
            t = x / pps
            # Verificar se clicou na track correta
            track_name = tl._audio_split_mode
            track_map = {"voice": (tl.VOICE_Y, tl.VOICE_H), "sfx": (tl.SFX_Y, tl.SFX_H),
                         "music": (tl.MUSIC_Y, tl.MUSIC_H), "audio": (tl.AUDIO_Y, tl.AUDIO_H),
                         "fx": (tl.TRANS_Y, tl.TRANS_H)}
            ty, th = track_map.get(track_name, (0, 0))
            if ty <= y <= ty + th:
                self._do_audio_split(t, track_name)
            tl.exit_split_mode()
            return

        if event.x < lbl_w:
            y = event.y
            if tl.TRANS_Y <= y <= tl.TRANS_Y + tl.TRANS_H:
                tl.fx_panel.show("fx")
            elif tl.VOICE_Y <= y <= tl.VOICE_Y + tl.VOICE_H:
                tl.fx_panel.show("voice")
            elif tl.SFX_Y <= y <= tl.SFX_Y + tl.SFX_H:
                tl.fx_panel.show("sfx")
            elif tl.MUSIC_Y <= y <= tl.MUSIC_Y + tl.MUSIC_H:
                tl.fx_panel.show("music")
            elif tl.AUDIO_Y <= y <= tl.AUDIO_Y + tl.AUDIO_H:
                tl.fx_panel.show("audio")
            return

        x = (event.x - lbl_w) + tl.scroll_x
        y = event.y
        t = x / pps

        # Playhead grab (apenas se nao esta sobre um item de track)
        ph_screen = lbl_w + int(tl.playhead_pos * pps) - tl.scroll_x
        if abs(event.x - ph_screen) < 8 and y < tl.VIDEO_Y:
            tl._dragging = (None, "playhead", event.x, tl.playhead_pos, 0)
            self._scrub_frame_at(tl.playhead_pos)
            return

        # Ruler
        if y < tl.RULER_H:
            # Check click em storyboard marker
            markers = getattr(tl, '_storyboard_markers', [])
            for m in markers:
                if abs(event.x - m["x"]) < 10:
                    self._copy_marker_prompt(m)
                    return
            tl._dragging = (None, "playhead", event.x, t, 0)
            tl.playhead_pos = max(0, t)
            tl.draw()
            # Scrub ou seek
            player = tl.app.preview_panel.player
            if player.is_playing or player.is_paused:
                total_dur = tl.project.total_duration()
                if total_dur > 0:
                    target_time = tl.playhead_pos
                    player._seek_to_time(target_time)
            else:
                self._scrub_frame_at(tl.playhead_pos)
            return

        # Video track
        if tl.VIDEO_Y <= y <= tl.VIDEO_Y + tl.VIDEO_H:
            tl.selected_track_item_id = None
            self._click_video(x, t, event)
            return

        # FX track
        if tl.TRANS_Y <= y <= tl.TRANS_Y + tl.TRANS_H:
            item = self._find_track_item_at(t, "fx")
            if item:
                tl.selected_track_item_id = item.id
                tl.selected_clip_id = None
                tl.draw()
                self._start_item_drag(item, x, t, event)
            else:
                tl.selected_track_item_id = None
                tl.fx_panel.show("fx")
            return

        # VOICE track
        if tl.VOICE_Y <= y <= tl.VOICE_Y + tl.VOICE_H:
            item = self._find_track_item_at(t, "voice")
            if item:
                tl.selected_track_item_id = item.id
                tl.selected_clip_id = None
                tl.draw()
                self._start_item_drag(item, x, t, event)
            else:
                tl.selected_track_item_id = None
                tl.fx_panel.show("voice")
            return

        # SFX track
        if tl.SFX_Y <= y <= tl.SFX_Y + tl.SFX_H:
            item = self._find_track_item_at(t, "sfx")
            if item:
                tl.selected_track_item_id = item.id
                tl.selected_clip_id = None
                tl.draw()
                self._start_item_drag(item, x, t, event)
            else:
                tl.selected_track_item_id = None
                tl.fx_panel.show("sfx")
            return

        # MUSIC track
        if tl.MUSIC_Y <= y <= tl.MUSIC_Y + tl.MUSIC_H:
            item = self._find_track_item_at(t, "music")
            if item:
                tl.selected_track_item_id = item.id
                tl.selected_clip_id = None
                tl.draw()
                self._start_item_drag(item, x, t, event)
            else:
                tl.selected_track_item_id = None
                tl.fx_panel.show("music")
            return

        # Audio track
        if tl.AUDIO_Y <= y <= tl.AUDIO_Y + tl.AUDIO_H:
            item = self._find_track_item_at(t, "audio")
            if item:
                tl.selected_track_item_id = item.id
                tl.selected_clip_id = None
                tl.draw()
                self._start_item_drag(item, x, t, event)
            else:
                tl.selected_track_item_id = None
                tl.fx_panel.show("audio")
            return

        # Empty
        tl._dragging = (None, "playhead", event.x, t, 0)
        tl.playhead_pos = max(0, t)
        tl.draw()
        self._scrub_frame_at(tl.playhead_pos)

    def _click_video(self, x, t, event):
        tl = self.tl
        pps = tl.zoom
        current = 0.0

        for clip in sorted(tl.project.clips, key=lambda c: c.position):
            end = current + clip.duration
            if current <= t <= end:
                # Split mode
                if tl._split_mode:
                    split_point = t - current
                    self._do_split(clip, split_point)
                    return

                # Normal
                local = x - current * pps
                if local <= 10:
                    tl._dragging = (clip.id, "trim_left", event.x, clip.duration, current)
                elif (end * pps - x) <= 10:
                    tl._dragging = (clip.id, "trim_right", event.x, clip.duration, current)
                else:
                    tl._dragging = (clip.id, "move", event.x, clip.position, 0)
                    tl.selected_clip_id = clip.id
                    tl.draw()
                    tl.app.on_clip_selected(clip)
                    tl.canvas.focus_set()
                return
            current = end

        if tl._split_mode:
            tl.exit_split_mode()

    def _do_split(self, clip, split_point):
        tl = self.tl
        if split_point < 0.5 or split_point > clip.duration - 0.5:
            return

        new_clip = tl.project.add_clip(prompt=clip.prompt, position=clip.position + 1)
        new_clip.duration = round(clip.duration - split_point, 1)
        new_clip.seed = clip.seed
        new_clip.status = clip.status
        new_clip.video_path = clip.video_path
        clip.duration = round(split_point, 1)

        from makevid.config import PROJECTS_DIR
        tl.project.save(PROJECTS_DIR)
        tl._split_mode = False
        tl.canvas.configure(cursor="")
        tl.draw()

    def on_drag(self, event):
        tl = self.tl
        if not tl._dragging:
            return

        clip_id, mode, start_x, orig, _ = tl._dragging
        dx = event.x - start_x
        lbl_w = tl.LBL_W

        if mode == "playhead":
            x = (event.x - lbl_w) + tl.scroll_x
            tl.playhead_pos = max(0, x / tl.zoom)
            # Throttle: scrub a cada 50ms no maximo
            import time
            now = time.time()
            last = getattr(tl, '_last_scrub_time', 0)
            if now - last > 0.05:
                tl._last_scrub_time = now
                self._scrub_frame_at(tl.playhead_pos)
            tl._update_playhead_only()
        elif mode == "trim_right":
            amt = max(0, min(orig - 1.0, -dx / tl.zoom))
            tl._trim_preview = (clip_id, "right", amt)
            tl.draw()
        elif mode == "trim_left":
            amt = max(0, min(orig - 1.0, dx / tl.zoom))
            tl._trim_preview = (clip_id, "left", amt)
            tl.draw()
        elif mode == "move":
            moved = int(dx / 60)
            if moved != 0:
                clip = tl.project.get_clip(clip_id)
                if clip:
                    new_pos = max(0, min(len(tl.project.clips) - 1, int(orig) + moved))
                    if new_pos != clip.position:
                        tl.project.move_clip(clip_id, new_pos)
                        tl._dragging = (clip_id, "move", event.x, new_pos, 0)
                        tl.draw()
        elif mode == "item_move":
            dt = dx / tl.zoom
            item = next((i for i in tl.project.track_items if i.id == clip_id), None)
            if item:
                # Mover todo o grupo de items sobrepostos junto
                group = getattr(tl, '_drag_group', None)
                if group is None:
                    # Primeira vez: capturar grupo e offsets relativos
                    if item.clip_index >= 0:
                        group_items = [i for i in tl.project.get_track_items(item.track)
                                       if i.clip_index == item.clip_index]
                    else:
                        group_items = [i for i in tl.project.get_track_items(item.track)
                                       if abs(i.start_time - item.start_time) < 0.05]
                    group = [(i, i.start_time - item.start_time) for i in group_items]
                    tl._drag_group = group
                new_start = max(0, orig + dt)
                for gi, offset in group:
                    gi.start_time = max(0, new_start + offset)
                tl._drag_guide_time = new_start
                tl.draw()
        elif mode == "item_trim_right":
            dt = dx / tl.zoom
            item = next((i for i in tl.project.track_items if i.id == clip_id), None)
            if item:
                max_dur = self._get_wav_duration(item) or orig
                item.duration = max(0.5, min(max_dur, orig + dt))
                self._invalidate_waveform_cache(item)
                tl.draw()
        elif mode == "item_trim_left":
            dt = dx / tl.zoom
            item = next((i for i in tl.project.track_items if i.id == clip_id), None)
            if item:
                orig_start = tl._dragging[4]
                trim = max(0, min(orig - 0.5, dt))
                item.start_time = orig_start + trim
                item.duration = orig - trim
                self._invalidate_waveform_cache(item)
                tl.draw()

    def on_release(self, event):
        tl = self.tl
        if not tl._dragging:
            return
        clip_id, mode, start_x, orig, _ = tl._dragging
        dx_total = abs(event.x - start_x)

        if mode in ("trim_left", "trim_right") and tl._trim_preview:
            _, _, amt = tl._trim_preview
            clip = tl.project.get_clip(clip_id)
            if clip and amt > 0:
                clip.duration = round(max(1.0, orig - amt) * 2) / 2

        if mode != "playhead":
            from makevid.config import PROJECTS_DIR
            tl.project.save(PROJECTS_DIR)
        else:
            # Ao soltar playhead: scrub final + cleanup + play button
            self._scrub_frame_at(tl.playhead_pos)
            self._scrub_cleanup()
            tl.draw()

        tl._dragging = None
        tl._trim_preview = None
        tl._drag_group = None
        tl._drag_guide_time = None
        tl.draw()

        # Se era clip de video, atualizar preview
        if mode in ("trim_left", "trim_right", "move"):
            clip = tl.project.get_clip(clip_id)
            if clip:
                tl.app.on_clip_selected(clip)
            tl.canvas.focus_set()

        # Se era item sem movimento = abrir editor
        if mode == "item_move" and dx_total == 0:
            item = next((i for i in tl.project.track_items if i.id == clip_id), None)
            if item:
                if item.track == "fx":
                    tl.fx_panel.show_fx_editor(item)
                else:
                    tl.fx_panel.show_track_editor(item)
                # Manter foco no canvas para Delete funcionar
                tl.canvas.focus_set()

    def on_scroll(self, event):
        tl = self.tl
        tl.scroll_x = max(0, tl.scroll_x - event.delta // 2)
        tl.draw()

    def _do_audio_split(self, t, track):
        """Divide todos os items sobrepostos na posicao t."""
        tl = self.tl
        items = [i for i in tl.project.get_track_items(track)
                 if i.start_time < t < i.start_time + i.duration]
        if not items:
            return
        for item in items:
            cut_point = t - item.start_time
            if cut_point <= 0.1 or cut_point >= item.duration - 0.1:
                continue
            new_dur = item.duration - cut_point
            tl.project.add_track_item(
                name=item.name, track=item.track,
                start_time=t, duration=new_dur,
                file_path=item.file_path, params=dict(item.params))
            item.duration = cut_point
        from makevid.config import PROJECTS_DIR
        tl.project.save(PROJECTS_DIR)
        tl.draw()

    def on_right_click(self, event):
        """Click direito - remove item de qualquer track na posicao."""
        tl = self.tl
        lbl_w = tl.LBL_W
        if event.x < lbl_w:
            return

        x = (event.x - lbl_w) + tl.scroll_x
        y = event.y
        t = x / tl.zoom

        # Todas as tracks
        all_tracks = [
            (tl.TRANS_Y, tl.TRANS_H, "fx"),
            (tl.VOICE_Y, tl.VOICE_H, "voice"),
            (tl.SFX_Y, tl.SFX_H, "sfx"),
            (tl.MUSIC_Y, tl.MUSIC_H, "music"),
            (tl.AUDIO_Y, tl.AUDIO_H, "audio"),
        ]

        for track_y, track_h, track_name in all_tracks:
            if track_y <= y <= track_y + track_h:
                # Encontrar item clicado
                item_at = next((i for i in tl.project.get_track_items(track_name)
                                if i.start_time <= t <= i.start_time + i.duration), None)
                if item_at:
                    # Remover todo o grupo (mesmo clip)
                    if item_at.clip_index >= 0:
                        group = [i for i in tl.project.get_track_items(track_name)
                                 if i.clip_index == item_at.clip_index]
                    else:
                        group = [i for i in tl.project.get_track_items(track_name)
                                 if abs(i.start_time - item_at.start_time) < 0.05]
                    from makevid.config import PROJECTS_DIR
                    for item in group:
                        tl.project.remove_track_item(item.id)
                    tl.project.save(PROJECTS_DIR)
                    tl.draw()
                return

    def on_hover(self, event):
        tl = self.tl
        lbl_w = tl.LBL_W
        vy, vh = tl.VIDEO_Y, tl.VIDEO_H
        ty, th = tl.TRANS_Y, tl.TRANS_H
        ay, ah = tl.AUDIO_Y, tl.AUDIO_H

        if event.x < lbl_w:
            tl.canvas.configure(cursor="")
            self._hide_marker_tooltip()
            # Tooltip das labels de track
            self._check_label_tooltip(event)
            return

        # Storyboard marker hover
        markers = getattr(tl, '_storyboard_markers', [])
        ruler_h = tl.RULER_H
        self._hide_label_tooltip()
        if event.y < ruler_h and markers:
            tl._ruler_hover_x = event.x
            for m in markers:
                if abs(event.x - m["x"]) < 10:
                    if getattr(tl, '_hover_storyboard_marker', None) != m["idx"]:
                        tl._hover_storyboard_marker = m["idx"]
                        tl.draw()
                    self._show_marker_tooltip(event, m)
                    tl.canvas.configure(cursor="hand2")
                    return
            # Sem marker mas na ruler - atualizar hover dos numeros
            tl.draw()
            return
        elif event.y < ruler_h:
            tl._ruler_hover_x = event.x
            tl.draw()
            return
        else:
            if getattr(tl, '_ruler_hover_x', -100) >= 0:
                tl._ruler_hover_x = -100
                tl.draw()
        if getattr(tl, '_hover_storyboard_marker', None) is not None:
            tl._hover_storyboard_marker = None
            tl.draw()
        self._hide_marker_tooltip()

        # Split mode
        if tl._split_mode:
            tl.canvas.configure(cursor="crosshair" if vy <= event.y <= vy + vh else "X_cursor")
            self._hide_label_tooltip()
            return

        # Audio split mode
        if tl._audio_split_mode:
            track_name = tl._audio_split_mode
            track_map = {"voice": (tl.VOICE_Y, tl.VOICE_H), "sfx": (tl.SFX_Y, tl.SFX_H),
                         "music": (tl.MUSIC_Y, tl.MUSIC_H), "audio": (tl.AUDIO_Y, tl.AUDIO_H)}
            ty2, th2 = track_map.get(track_name, (0, 0))
            tl.canvas.configure(cursor="crosshair" if ty2 <= event.y <= ty2 + th2 else "X_cursor")
            self._hide_label_tooltip()
            return

        # Detectar track hover (para cursor)
        if vy <= event.y <= vy + vh:
            pass
        elif ty <= event.y <= ty + th:
            pass
        elif ay <= event.y <= ay + ah:
            pass

        # Playhead
        ph_screen = lbl_w + int(tl.playhead_pos * tl.zoom) - tl.scroll_x
        if abs(event.x - ph_screen) < 12:
            tl.canvas.configure(cursor="sb_h_double_arrow")
            if not getattr(tl, '_hover_playhead', False):
                tl._hover_playhead = True
                tl.draw()
            self._check_gif_hover(event, None)
            return
        elif getattr(tl, '_hover_playhead', False):
            tl._hover_playhead = False
            tl.draw()

        # FX/Audio/Voice/SFX/Music tracks hover
        all_tracks = [
            (tl.TRANS_Y, tl.TRANS_H, "fx"),
            (tl.VOICE_Y, tl.VOICE_H, "voice"),
            (tl.SFX_Y, tl.SFX_H, "sfx"),
            (tl.MUSIC_Y, tl.MUSIC_H, "music"),
            (tl.AUDIO_Y, tl.AUDIO_H, "audio"),
        ]
        for track_y, track_h, track_name in all_tracks:
            if track_y <= event.y <= track_y + track_h:
                x = (event.x - lbl_w) + tl.scroll_x
                t = x / tl.zoom
                item = self._find_track_item_at(t, track_name)
                if item:
                    ix1 = item.start_time * tl.zoom
                    ix2 = (item.start_time + item.duration) * tl.zoom
                    local = x - ix1
                    if local <= 6 or (ix2 - x) <= 6:
                        tl.canvas.configure(cursor="sb_h_double_arrow")
                    else:
                        tl.canvas.configure(cursor="fleur")
                    if tl._hover_track_item != item.id:
                        tl._hover_track_item = item.id
                        tl.draw()
                else:
                    tl.canvas.configure(cursor="hand2")
                    if tl._hover_track_item is not None:
                        tl._hover_track_item = None
                        tl.draw()
                self._check_gif_hover(event, None)
                return

        if tl._hover_track_item is not None:
            tl._hover_track_item = None
            tl.draw()

        # Video track
        if vy <= event.y <= vy + vh:
            x = (event.x - lbl_w) + tl.scroll_x
            current = 0.0
            for clip in sorted(tl.project.clips, key=lambda c: c.position):
                s, e = current * tl.zoom, (current + clip.duration) * tl.zoom
                if s <= x <= e:
                    local = x - s
                    if local <= 10 or (e - x) <= 10:
                        tl.canvas.configure(cursor="sb_h_double_arrow")
                    else:
                        tl.canvas.configure(cursor="hand2")
                    self._set_hover_clip(clip.id)
                    self._check_gif_hover(event, clip)
                    return
                current += clip.duration
            self._set_hover_clip(None)

        self._check_gif_hover(event, None)
        tl.canvas.configure(cursor="")

    def _set_hover_clip(self, clip_id):
        """Seta qual clip individual esta com hover."""
        tl = self.tl
        old = getattr(tl, '_hover_clip_for_glow', None)
        if old != clip_id:
            tl._hover_clip_for_glow = clip_id
            tl.draw()

    def _check_gif_hover(self, event, clip):
        """Inicia/para gif baseado no clip sob o mouse."""
        tl = self.tl
        new_id = clip.id if (clip and clip.status == "done" and clip.video_path) else None

        if new_id != tl._hover_clip_id:
            if tl._hover_clip_id:
                tl._stop_gif()
            if new_id:
                tl._start_gif(new_id)

    # --- Track Items (FX/Audio) ---

    def _find_track_item_at(self, t, track):
        """Encontra item na posicao temporal t. Se sobrepostos, retorna o mais proximo do mouse (centro mais perto de t)."""
        candidates = [item for item in self.tl.project.get_track_items(track)
                      if item.start_time <= t <= item.start_time + item.duration]
        if not candidates:
            return None
        return min(candidates, key=lambda i: abs((i.start_time + i.duration / 2) - t))

    def _invalidate_waveform_cache(self, item):
        """Limpa cache da waveform pra forcar recalculo visual."""
        renderer = self.tl._renderer
        if hasattr(renderer, '_waveform_cache'):
            keys_to_remove = [k for k in renderer._waveform_cache if k.startswith(item.id)]
            for k in keys_to_remove:
                del renderer._waveform_cache[k]

    def _get_wav_duration(self, item):
        """Retorna duracao real do arquivo de audio em segundos."""
        from pathlib import Path
        if not item.file_path or not Path(item.file_path).exists():
            return 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            return get_audio_duration(item.file_path)
        except Exception:
            return 0

    def _start_item_drag(self, item, x, t, event):
        """Inicia drag de um track item."""
        tl = self.tl
        pps = tl.zoom
        local = (t - item.start_time) * pps
        item_w = item.duration * pps

        # Guardar duracao original do WAV pra calcular speed ratio
        self._drag_original_wav_dur = self._get_wav_duration(item)

        if local <= 6:
            tl._dragging = (item.id, "item_trim_left", event.x, item.duration, item.start_time)
        elif (item_w - local) <= 6:
            tl._dragging = (item.id, "item_trim_right", event.x, item.duration, item.start_time)
        else:
            tl._dragging = (item.id, "item_move", event.x, item.start_time, 0)

    # --- Storyboard Marker Tooltip ---

    def _show_marker_tooltip(self, event, marker):
        """Mostra tooltip com conteudo da cena do storyboard."""
        tl = self.tl
        if hasattr(tl, '_marker_tooltip_id'):
            return  # ja visivel

        scene = marker["scene"]
        idx = marker["idx"]
        visual = scene.get("visual", "")[:60]
        camera = scene.get("camera", "")
        text = f"CENA {idx+1}: {visual}"
        if camera:
            text += f"\n[{camera}]"
        text += "\n(clique para copiar prompt)"

        # Background do tooltip
        tx = event.x + 10
        ty = event.y + 15
        tid = tl.canvas.create_rectangle(tx - 4, ty - 2, tx + len(text) * 4 + 10, ty + 36,
                                          fill="#1a1a2a", outline="#c89b3c", width=1)
        ttid = tl.canvas.create_text(tx, ty, text=text, anchor="nw",
                                      fill="#f0e6d2", font=("Segoe UI", 8))
        tl._marker_tooltip_id = (tid, ttid)

    def _hide_marker_tooltip(self):
        tl = self.tl
        if hasattr(tl, '_marker_tooltip_id') and tl._marker_tooltip_id:
            for item_id in tl._marker_tooltip_id:
                tl.canvas.delete(item_id)
            tl._marker_tooltip_id = None

    def _copy_marker_prompt(self, marker):
        """Copia o prompt da cena para o clipboard e cola no prompt box."""
        scene = marker["scene"]
        visual = scene.get("visual", "")
        camera = scene.get("camera", "")
        prompt = f"{visual}, {camera}" if camera else visual

        app = self.tl.app
        # Copiar para clipboard
        app.clipboard_clear()
        app.clipboard_append(prompt)
        # Colar no prompt box do gerador
        app.generator_panel.prompt_box.delete("0.0", "end")
        app.generator_panel.prompt_box.insert("0.0", prompt)

    def _scrub_frame_at(self, time_pos):
        """Mostra no display o frame correspondente a posicao temporal.
        Usa a mesma logica do player: frames reais proporcionais a total_duration."""
        from pathlib import Path
        try:
            import cv2
        except ImportError:
            return

        tl = self.tl
        clips = sorted(tl.project.clips, key=lambda c: c.position)
        if not clips:
            return

        # Calcular frame counts reais (mesma logica do player.play())
        project_fps = tl.project.output_fps or 16
        total_frames = 0
        clip_frame_counts = []
        for clip in clips:
            if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                if getattr(tl, '_scrub_clip_id', None) == clip.id and hasattr(tl, '_scrub_total'):
                    fc = tl._scrub_total
                else:
                    cap = cv2.VideoCapture(str(clip.video_path))
                    fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cap.release()
            else:
                fc = int(clip.duration * project_fps)
            clip_frame_counts.append(fc)
            total_frames += fc

        if total_frames <= 0:
            return

        # Converter time_pos em frame number (mesma formula do player)
        total_dur = tl.project.total_duration()
        if total_dur <= 0:
            return
        ratio = time_pos / total_dur
        target_frame = int(ratio * total_frames)
        target_frame = max(0, min(target_frame, total_frames - 1))

        # Encontrar clip e frame local
        accumulated = 0
        for i, clip in enumerate(clips):
            fc = clip_frame_counts[i]
            if accumulated + fc > target_frame:
                frame_in_clip = target_frame - accumulated
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    # Reusar cap se mesmo clip
                    if getattr(tl, '_scrub_clip_id', None) != clip.id:
                        if hasattr(tl, '_scrub_cap') and tl._scrub_cap:
                            tl._scrub_cap.release()
                        tl._scrub_cap = cv2.VideoCapture(str(clip.video_path))
                        tl._scrub_clip_id = clip.id
                        tl._scrub_total = fc

                    tl._scrub_cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_in_clip))
                    ret, frame = tl._scrub_cap.read()
                    if ret:
                        pp = tl.app.preview_panel
                        from PIL import Image
                        import customtkinter as ctk
                        frame_rgb = frame[:, :, ::-1]

                        # Aplicar FX ativos neste tempo
                        from makevid.core.fx_processor import apply_fx_to_frame
                        fx_items = tl.project.get_track_items("fx")
                        if fx_items:
                            total_dur = tl.project.total_duration()
                            if total_dur > 0:
                                frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, time_pos, total_dur)

                        img = Image.fromarray(frame_rgb)
                        img, w, h = pp._fit_image(img)
                        pp._preview_img_ref = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                        pp._hide_play_button()
                        if not pp.preview_label.winfo_ismapped():
                            pp.preview_label.pack(expand=True)
                        pp.preview_label.configure(image=pp._preview_img_ref, text="", compound="center")
                        pp.clip_info.configure(text=f"{time_pos:.1f}s | Clip {clip.position+1}")
                return
            accumulated += fc

    def _scrub_cleanup(self):
        """Libera recursos do scrub."""
        tl = self.tl
        if hasattr(tl, '_scrub_cap') and tl._scrub_cap:
            tl._scrub_cap.release()
            tl._scrub_cap = None
            tl._scrub_clip_id = None

    def _check_label_tooltip(self, event):
        """Mostra tooltip informativa sobre a track quando hover no label."""
        tl = self.tl
        renderer = tl._renderer
        tooltips = getattr(renderer, '_label_tooltips', {})
        y = event.y

        for track_key, (y1, y2, text) in tooltips.items():
            if y1 <= y <= y2:
                if getattr(tl, '_label_tooltip_track', None) != track_key:
                    self._hide_label_tooltip()
                    tl._label_tooltip_track = track_key
                    # Desenhar tooltip
                    tx = 68
                    ty = event.y
                    lines = text.split("\n")
                    max_line = max(len(l) for l in lines)
                    box_w = max_line * 6 + 16
                    box_h = len(lines) * 14 + 10
                    tid = tl.canvas.create_rectangle(
                        tx, ty, tx + box_w, ty + box_h,
                        fill="#1a1a2a", outline="#c89b3c", width=1, tags="label_tooltip")
                    for i, line in enumerate(lines):
                        color = "#f0e6d2" if i == 0 else "#a09b8c"
                        font = ("Segoe UI", 9, "bold") if i == 0 else ("Segoe UI", 8)
                        tl.canvas.create_text(
                            tx + 8, ty + 6 + i * 14, text=line, anchor="nw",
                            fill=color, font=font, tags="label_tooltip")
                return

        self._hide_label_tooltip()

    def _hide_label_tooltip(self):
        tl = self.tl
        tl.canvas.delete("label_tooltip")
        tl._label_tooltip_track = None
