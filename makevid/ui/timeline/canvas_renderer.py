"""Canvas Renderer - Desenho do canvas da timeline (visual premium)."""

from makevid.ui.theme import C


class CanvasRenderer:
    """Responsavel por desenhar todos os elementos visuais da timeline."""

    def __init__(self, timeline):
        self.tl = timeline

    def draw(self):
        tl = self.tl
        c = tl.canvas
        c.delete("all")

        w = c.winfo_width() or 800
        h = c.winfo_height() or 300
        pps = tl.zoom
        lbl_w = tl.LBL_W
        vy, vh = tl.VIDEO_Y, tl.VIDEO_H
        ty, th = tl.TRANS_Y, tl.TRANS_H
        voy, voh = tl.VOICE_Y, tl.VOICE_H
        sy, sh = tl.SFX_Y, tl.SFX_H
        my, mh = tl.MUSIC_Y, tl.MUSIC_H
        ay, ah = tl.AUDIO_Y, tl.AUDIO_H

        total_dur = max(tl.project.total_duration(), 30)
        sb_dur = tl.project.world.total_storyboard_duration()
        if sb_dur > total_dur:
            total_dur = sb_dur + 5

        self._draw_bg_gradient(c, lbl_w, w, h)
        self._draw_track_labels(c, lbl_w, h, vy, vh, ty, th, voy, voh, sy, sh, my, mh, ay, ah)
        self._draw_track_backgrounds(c, lbl_w, w, h, vy, vh, ty, th, voy, voh, sy, sh, my, mh, ay, ah)
        self._draw_ruler(c, lbl_w, w, pps, total_dur, tl.scroll_x)
        self._draw_storyboard_markers(c, lbl_w, w, h, pps, tl)
        self._draw_clips(c, lbl_w, w, pps, vy, vh, ty, th, tl)
        self._draw_playhead(c, lbl_w, w, h, pps, tl.playhead_pos, tl.scroll_x)
        self._draw_drag_guide(c, lbl_w, w, h, pps, tl)
        self._update_time_label(tl, total_dur)
        self._update_scrollbar(tl, lbl_w, w, pps, total_dur)

    def _draw_bg_gradient(self, c, lbl_w, w, h):
        """Fundo sutil com faixas horizontais para dar profundidade."""
        # Faixa escura de base
        c.create_rectangle(lbl_w, 0, w, h, fill="#07090e", outline="")
        # Linha de chao brilhante no fundo
        c.create_rectangle(lbl_w, h - 3, w, h, fill="#0d1020", outline="")
        c.create_line(lbl_w, h - 1, w, h - 1, fill="#1a2a4a", width=1)

    def _draw_track_labels(self, c, lbl_w, h, vy, vh, ty, th, voy, voh, sy, sh, my, mh, ay, ah):
        """Labels laterais estilo mixer profissional."""
        c.create_rectangle(0, 0, lbl_w, h, fill="#060810", outline="")
        c.create_line(lbl_w - 1, 0, lbl_w - 1, h, fill="#1a2a4a", width=1)
        c.create_line(lbl_w, 0, lbl_w, h, fill=C["gold"], width=2)

        def _label(y, track_h, text, sub, color):
            cy = y + track_h // 2
            # Card de fundo
            c.create_rectangle(3, y + 1, lbl_w - 4, y + track_h - 1,
                               fill="#0a0e1a", outline="#151a30", width=1)
            # Barra lateral colorida
            c.create_rectangle(3, y + 1, 7, y + track_h - 1, fill=color, outline="")
            # Texto
            c.create_text(12, cy - (4 if sub else 0), text=text, anchor="w",
                          fill="#e0d8c8", font=("Segoe UI", 8, "bold"))
            if sub:
                # Mostrar volume da track
                track_key = {"VIDEO": None, "FX": None, "VOICE": "voice", "SFX": "sfx", "MUSIC": "music", "AUDIO": "audio"}.get(text)
                if track_key:
                    vol = self.tl.project.track_volumes.get(track_key, 1.0)
                    vol_pct = int(vol * 100)
                    c.create_text(12, cy + 7, text=f"{vol_pct}%", anchor="w",
                                  fill=C["text3"], font=("Consolas", 7, "bold"))
                else:
                    c.create_text(12, cy + 7, text=sub, anchor="w",
                                  fill=C["text3"], font=("Segoe UI", 6))

        _label(vy, vh, "VIDEO", "Track", "#3399ff")
        _label(ty, th, "FX", "Effects", C["purple"])
        _label(voy, voh, "VOICE", "TTS", "#ff9944")
        _label(sy, sh, "SFX", "Foley", "#44cc88")
        _label(my, mh, "MUSIC", "Score", "#cc44aa")
        _label(ay, ah, "AUDIO", "Mix", "#0ac8b9")

        # Tooltip areas para labels (guardadas para hover)
        self._label_tooltips = {
            "voice": (voy, voy + voh, "VOZ (TTS)\nFalas e narracoes geradas por IA.\nEx: dialogo de personagem, narracao off"),
            "sfx": (sy, sy + sh, "SFX (Efeitos Sonoros)\nSons reais do Freesound.\nEx: tiro, porta, passos, motor"),
            "music": (my, my + mh, "MUSICA\nTrilha sonora buscada por mood.\nEx: cinematic ambient, epic action"),
            "audio": (ay, ay + ah, "AUDIO (Mix)\nAudios importados ou gravados.\nEx: gravacao de microfone, foley manual"),
            "fx": (ty, ty + th, "FX (Efeitos Visuais)\nEfeitos aplicados ao video.\nEx: fade in, glitch, shake, sepia"),
            "video": (vy, vy + vh, "VIDEO\nClips de video na timeline.\nEx: imagens geradas, videos importados"),
        }

    def _draw_track_backgrounds(self, c, lbl_w, w, h, vy, vh, ty, th, voy, voh, sy, sh, my, mh, ay, ah):
        """Tracks com bordas, separadores e profundidade."""
        tl = self.tl

        def _track_bg(y, track_h, top_color, bg_color):
            # Fundo principal
            c.create_rectangle(lbl_w + 2, y, w, y + track_h, fill=bg_color, outline="")
            # Borda superior brilhante
            c.create_line(lbl_w + 2, y, w, y, fill=top_color, width=2)
            # Borda inferior sutil
            c.create_line(lbl_w + 2, y + track_h, w, y + track_h, fill="#0a1020", width=1)

        def _separator(y1_end, y2_start):
            """Desenha separador entre tracks."""
            c.create_rectangle(lbl_w + 2, y1_end, w, y2_start, fill="#050710", outline="")

        _track_bg(vy, vh, "#1a3a6a", "#0b0e18")
        _separator(vy + vh, ty)
        _track_bg(ty, th, "#3a1a6a", "#0c0818")
        _separator(ty + th, voy)
        _track_bg(voy, voh, "#6a3a1a", "#0e0a08")
        _separator(voy + voh, sy)
        _track_bg(sy, sh, "#1a6a3a", "#080e0a")
        _separator(sy + sh, my)
        _track_bg(my, mh, "#6a1a4a", "#0e080c")
        _separator(my + mh, ay)
        _track_bg(ay, ah, "#0a6a5a", "#080e16")

        # Centerline no audio (DAW style)
        mid_audio = ay + ah // 2
        c.create_line(lbl_w + 2, mid_audio, w, mid_audio, fill="#0a1a20", width=1, dash=(3, 6))

        # Footer
        footer_y = ay + ah + 1
        if footer_y < h:
            c.create_rectangle(lbl_w + 2, footer_y, w, h, fill="#050710", outline="")
            c.create_line(lbl_w + 2, footer_y, w, footer_y, fill="#1a2a4a", width=1)
            c.create_rectangle(0, footer_y, lbl_w, h, fill="#060810", outline="")

    def _draw_ruler(self, c, lbl_w, w, pps, total_dur, scroll_x):
        """Barra de tempo (ruler) com marcas robustas e highlight no hover."""
        ruler_h = self.tl.RULER_H

        # Fundo com profundidade
        c.create_rectangle(lbl_w, 0, w, ruler_h // 3, fill="#181c32", outline="")
        c.create_rectangle(lbl_w, ruler_h // 3, w, 2 * ruler_h // 3, fill="#141830", outline="")
        c.create_rectangle(lbl_w, 2 * ruler_h // 3, w, ruler_h, fill="#10142a", outline="")
        # Borda inferior dourada forte
        c.create_line(lbl_w, ruler_h - 1, w, ruler_h - 1, fill=C["gold"], width=2)
        c.create_line(lbl_w, ruler_h - 3, w, ruler_h - 3, fill="#3a2a10", width=1)
        # Borda superior
        c.create_line(lbl_w, 0, w, 0, fill="#2a3050", width=1)

        # Step adaptativo
        if pps >= 80:
            step = 1.0
        elif pps >= 40:
            step = 2.0
        elif pps >= 20:
            step = 5.0
        elif pps >= 10:
            step = 10.0
        else:
            step = 15.0

        subdivs = 4 if step <= 2 else 5
        sub_step = step / subdivs

        # Hover position do mouse
        hover_x = getattr(self.tl, '_ruler_hover_x', -100)

        t = 0.0
        while t <= total_dur + step:
            x = lbl_w + int(t * pps) - scroll_x
            if lbl_w <= x <= w:
                # Marca principal grossa
                c.create_line(x, ruler_h - 16, x, ruler_h - 2, fill=C["gold"], width=2)
                c.create_line(x, 2, x, 6, fill="#4a4a6a", width=1)

                m, s = int(t) // 60, t % 60
                txt = f"{m:02d}:{int(s):02d}" if step >= 10 else f"{m:02d}:{s:04.1f}"

                # Highlight se mouse proximo
                is_hovered = abs(x - hover_x) < 25
                if is_hovered:
                    c.create_rectangle(x - 1, 2, x + len(txt) * 7 + 5, 17,
                                       fill="#2a2040", outline="")
                    c.create_text(x + 3, 3, text=txt, anchor="nw",
                                  fill="#ffffff", font=("Consolas", 10, "bold"))
                else:
                    c.create_text(x + 3, 3, text=txt, anchor="nw",
                                  fill="#9999bb", font=("Consolas", 10, "bold"))

            # Sub-marcas
            for si in range(1, subdivs):
                st = t + sub_step * si
                sx = lbl_w + int(st * pps) - scroll_x
                if lbl_w <= sx <= w:
                    if si == subdivs // 2:
                        c.create_line(sx, ruler_h - 10, sx, ruler_h - 2, fill="#5a5a7a", width=1)
                    else:
                        c.create_line(sx, ruler_h - 6, sx, ruler_h - 2, fill="#3a3a5a", width=1)

            t += step

        # Canto do ruler (label area)
        c.create_rectangle(0, 0, lbl_w, ruler_h, fill="#0c0e1a", outline="")
        c.create_line(0, ruler_h - 1, lbl_w, ruler_h - 1, fill=C["gold"], width=2)
        c.create_text(lbl_w // 2, ruler_h // 2, text="⏱", fill=C["gold"], font=("Segoe UI", 11))

    def _draw_clips(self, c, lbl_w, w, pps, vy, vh, ty, th, tl):
        from pathlib import Path

        current_time = 0.0
        clips = sorted(tl.project.clips, key=lambda cl: cl.position)

        for clip in clips:
            x1 = lbl_w + int(current_time * pps) - tl.scroll_x
            x2 = x1 + int(clip.duration * pps)

            if x2 >= lbl_w and x1 <= w:
                sel = clip.id == tl.selected_clip_id
                hovered = clip.id == getattr(tl, '_hover_clip_for_glow', None)
                fill, border = self._clip_colors(clip, sel)

                # Neon glow no hover do clip individual
                if hovered and not sel:
                    border = "#00ffee"  # neon cyan
                    c.create_rectangle(x1 - 1, vy, x2 + 1, vy + vh, fill="", outline="#004444", width=1)

                # Body
                c.create_rectangle(x1 + 1, vy + 2, x2 - 1, vy + vh - 2, fill=fill, outline=border, width=2 if (sel or hovered) else 1)

                # Thumbnail/gif
                clip_w = x2 - x1 - 2
                clip_h = vh - 4
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists() and clip_w > 10:
                    if tl._hover_clip_id == clip.id:
                        frames = tl.thumbs.get_gif_frames(clip, clip_w, clip_h)
                        if frames:
                            idx = tl._gif_index % len(frames)
                            c.create_image(x1 + 1, vy + 2, image=frames[idx], anchor="nw")
                    else:
                        thumb = tl.thumbs.get_thumb(clip, clip_w, clip_h)
                        if thumb:
                            c.create_image(x1 + 1, vy + 2, image=thumb, anchor="nw")

                # Label
                label = clip.prompt[:18] if clip.prompt else "(vazio)"
                c.create_text(x1 + 8, vy + 9, text=f"{clip.position+1}. {label}",
                              anchor="nw", fill="#ffffff", font=("Segoe UI", 10, "bold"))
                c.create_text(x1 + 8, vy + 28, text=f"{clip.duration:.1f}s",
                              anchor="nw", fill=C["cyan"], font=("Consolas", 10, "bold"))

                if clip.status == "done":
                    c.create_text(x2 - 8, vy + 9, text="OK", anchor="ne", fill="#00ffcc", font=("Consolas", 9, "bold"))

                # Trim handles
                hw = 6
                c.create_rectangle(x1 + 1, vy + 2, x1 + hw, vy + vh - 2, fill=C["trim_handle"], outline="#e8c44a")
                c.create_rectangle(x2 - hw, vy + 2, x2 - 1, vy + vh - 2, fill=C["trim_handle"], outline="#e8c44a")
                for gy in range(vy + 14, vy + vh - 14, 6):
                    c.create_line(x1 + 2, gy, x1 + hw - 1, gy, fill="#0a0a0f")
                    c.create_line(x2 - hw + 1, gy, x2 - 2, gy, fill="#0a0a0f")

                # Trim preview
                if tl._trim_preview and tl._trim_preview[0] == clip.id:
                    self._draw_trim_preview(c, x1, x2, vy, vh, pps, tl._trim_preview)

            # FX diamond (transicao entre clips)
            if clip.position > 0:
                tx = lbl_w + int(current_time * pps) - tl.scroll_x
                if lbl_w <= tx <= w:
                    tcy = ty + th // 2
                    diamond_id = f"diamond_{clip.position}"
                    is_marked = diamond_id in getattr(tl, '_marked_diamonds', set())
                    is_hovered = getattr(tl, '_hover_diamond', None) == diamond_id

                    # Tamanho: maior no hover ou marcado
                    sz = 12 if (is_hovered or is_marked) else 8

                    if is_marked:
                        # Marcado: preenchido com cor vibrante + borda neon
                        c.create_polygon(tx - sz-2, tcy, tx, tcy - sz-2, tx + sz+2, tcy, tx, tcy + sz+2,
                                         fill="", outline="#00ffee", width=1)
                        c.create_polygon(tx - sz, tcy, tx, tcy - sz, tx + sz, tcy, tx, tcy + sz,
                                         fill="#6b3fa0", outline="#bb77ff", width=2)
                        # Icone interno se tem efeito aplicado
                        fx_at = [i for i in tl.project.get_track_items("fx")
                                 if abs(i.start_time - current_time) < 0.1]
                        if fx_at:
                            c.create_text(tx, tcy, text="\u2713", fill="#00ffee",
                                          font=("Segoe UI", 7, "bold"))
                    elif is_hovered:
                        # Hover: destacado com borda colorida
                        c.create_polygon(tx - sz-2, tcy, tx, tcy - sz-2, tx + sz+2, tcy, tx, tcy + sz+2,
                                         fill="", outline=C["neon_purple"], width=1)
                        c.create_polygon(tx - sz, tcy, tx, tcy - sz, tx + sz, tcy, tx, tcy + sz,
                                         fill="#3a1a6a", outline=C["neon_purple"], width=2)
                    else:
                        # Normal
                        c.create_polygon(tx - sz, tcy, tx, tcy - sz, tx + sz, tcy, tx, tcy + sz,
                                         fill="#2a1a4a", outline=C["purple"], width=2)

            current_time += clip.duration

        # --- Track Items (FX e Audio) com posicao independente ---
        self._draw_track_items(c, lbl_w, w, pps, tl)

    def _draw_storyboard_markers(self, c, lbl_w, w, h, pps, tl):
        """Desenha checkpoints do storyboard como marcadores na ruler."""
        # Only show markers after user explicitly generates timeline
        if not getattr(tl.project, '_storyboard_applied', False):
            tl._storyboard_markers = []
            return
        scenes = tl.project.world.scenes
        if not scenes:
            tl._storyboard_markers = []
            return

        ruler_h = tl.RULER_H
        current_time = 0.0
        markers = []
        hover_marker = getattr(tl, '_hover_storyboard_marker', None)

        for i, scene in enumerate(scenes):
            dur = float(scene.get("duration", 5))
            x = lbl_w + int(current_time * pps) - tl.scroll_x

            if lbl_w <= x <= w:
                is_hover = (hover_marker == i)

                # Linha vertical pontilhada
                line_color = "#ffd700" if is_hover else "#c89b3c"
                line_w = 2 if is_hover else 1
                c.create_line(x, ruler_h, x, h, fill=line_color, width=line_w, dash=(4, 4))

                # Badge circular no topo
                badge_r = 10 if is_hover else 8
                by = ruler_h - badge_r - 2

                if is_hover:
                    # Glow neon
                    c.create_oval(x - badge_r - 3, by - badge_r - 3, x + badge_r + 3, by + badge_r + 3,
                                  fill="", outline="#00ffee", width=2)
                    c.create_oval(x - badge_r, by - badge_r, x + badge_r, by + badge_r,
                                  fill="#ffd700", outline="#00ffee", width=2)
                else:
                    c.create_oval(x - badge_r, by - badge_r, x + badge_r, by + badge_r,
                                  fill="#c89b3c", outline="#ffd700", width=1)

                c.create_text(x, by, text=str(i + 1),
                              fill="#0a0a0f", font=("Consolas", 9 if is_hover else 8, "bold"))

            markers.append({"x": x, "time": current_time, "scene": scene, "idx": i})
            current_time += dur

        tl._storyboard_markers = markers

    def _draw_playhead(self, c, lbl_w, w, h, pps, pos, scroll_x):
        """Playhead destacado que invade todas as tracks."""
        c.delete("playhead_fast")
        c.delete("playhead_full")
        px = lbl_w + int(pos * pps) - scroll_x
        if px < lbl_w or px > w:
            return

        tag = "playhead_full"
        is_hovered = getattr(self.tl, '_hover_playhead', False)

        if is_hovered:
            c.create_rectangle(px - 8, 0, px + 8, h, fill="#330000", outline="", tags=tag)
            c.create_rectangle(px - 5, 0, px + 5, h, fill="#550000", outline="", tags=tag)
            c.create_rectangle(px - 3, 0, px + 3, h, fill="#770000", outline="", tags=tag)
            c.create_line(px, 0, px, h, fill="#ff4444", width=5, tags=tag)
            c.create_polygon(px - 14, 0, px + 14, 0, px + 8, 10, px, 20, px - 8, 10,
                             fill="#ff3333", outline="#ffaaaa", width=2, tags=tag)
            c.create_oval(px - 4, 6, px + 4, 14, fill="#ffffff", outline="#ff6666", tags=tag)
            c.create_polygon(px - 8, h, px + 8, h, px, h - 10, fill="#ff3333", outline="#ffaaaa", width=1, tags=tag)
        else:
            c.create_rectangle(px - 4, 0, px + 4, h, fill="#220000", outline="", tags=tag)
            c.create_rectangle(px - 2, 0, px + 2, h, fill="#440000", outline="", tags=tag)
            c.create_line(px, 0, px, h, fill="#ff2222", width=3, tags=tag)
            for ty in [self.tl.VIDEO_Y, self.tl.TRANS_Y, self.tl.AUDIO_Y,
                       self.tl.VIDEO_Y + self.tl.VIDEO_H,
                       self.tl.TRANS_Y + self.tl.TRANS_H,
                       self.tl.AUDIO_Y + self.tl.AUDIO_H]:
                c.create_line(px - 6, ty, px + 6, ty, fill="#ff4444", width=1, tags=tag)
            c.create_polygon(px - 12, 0, px + 12, 0, px + 6, 8, px, 16, px - 6, 8,
                             fill="#ff2222", outline="#ff6666", width=2, tags=tag)
            c.create_oval(px - 3, 5, px + 3, 11, fill="#ffffff", outline="", tags=tag)
            c.create_polygon(px - 6, h, px + 6, h, px, h - 8, fill="#ff2222", outline="", tags=tag)

    def _draw_trim_preview(self, c, x1, x2, vy, vh, pps, preview):
        _, side, amount = preview
        px = int(amount * pps)
        if px <= 0:
            return
        tx1 = (x2 - px) if side == "right" else (x1 + 1)
        tx2 = (x2 - 1) if side == "right" else (x1 + px)
        c.create_rectangle(tx1, vy + 2, tx2, vy + vh - 2, fill="#0a0a0f", stipple="gray50", outline="")
        for hx in range(int(tx1), int(tx2), 8):
            c.create_line(hx, vy + 2, hx + 12, vy + vh - 2, fill="#ff3333", width=1)
        cut_x = tx1 if side == "right" else tx2
        c.create_line(cut_x, vy + 2, cut_x, vy + vh - 2, fill="#ff3333", width=2, dash=(4, 2))
        anc = "w" if side == "right" else "e"
        c.create_text(cut_x + (4 if side == "right" else -4), vy + vh // 2,
                      text=f"-{amount:.1f}s", anchor=anc, fill="#ff6666", font=("Consolas", 9, "bold"))

    def _clip_colors(self, clip, selected):
        if clip.status == "done":
            return ("#2a6a3a" if selected else "#1a4a2a", C["cyan"] if selected else "#1a5a2a")
        elif clip.status == "generating":
            return ("#3a2a0a", C["gold"])
        elif clip.status == "error":
            return ("#3a1010", C["red"])
        return ("#2a2a4e" if selected else "#1a1a2e", C["gold"] if selected else "#2a2a4a")

    def _draw_track_items(self, c, lbl_w, w, pps, tl):
        """Desenha itens de todas as tracks."""
        hover_item = getattr(tl, '_hover_track_item', None)

        # Mapeamento track → (y, h, color)
        track_map = {
            "fx": (tl.TRANS_Y, tl.TRANS_H, C["purple"]),
            "voice": (tl.VOICE_Y, tl.VOICE_H, "#ff9944"),
            "sfx": (tl.SFX_Y, tl.SFX_H, "#44cc88"),
            "music": (tl.MUSIC_Y, tl.MUSIC_H, "#cc44aa"),
            "audio": (tl.AUDIO_Y, tl.AUDIO_H, "#0ac8b9"),
        }

        for track_name, (track_y, track_h, color) in track_map.items():
            items = sorted(tl.project.get_track_items(track_name), key=lambda i: i.start_time)
            if track_name == "fx":
                for item in items:
                    self._draw_fx_item(c, item, lbl_w, w, pps, tl, hover_item)
            else:
                # Agrupar items pelo clip_index (mesmo video)
                groups = []
                for item in items:
                    placed = False
                    for group in groups:
                        g0 = group[0]
                        if item.clip_index >= 0 and g0.clip_index == item.clip_index:
                            group.append(item)
                            placed = True
                            break
                        elif item.clip_index < 0 and g0.clip_index < 0 and abs(item.start_time - g0.start_time) < 0.05:
                            group.append(item)
                            placed = True
                            break
                    if not placed:
                        groups.append([item])

                # Desenhar grupo arrastado por ultimo (por cima de tudo)
                dragging_id = tl._dragging[0] if tl._dragging and tl._dragging[1] == "item_move" else None
                for group in groups:
                    rep = group[0]
                    g_start = min(i.start_time for i in group)
                    g_end = max(i.start_time + i.duration for i in group)
                    group_ids = [i.id for i in group]

                    # Se este grupo esta sendo arrastado, pular (desenhar por ultimo)
                    if dragging_id and dragging_id in group_ids:
                        continue

                    effective_hover = rep.id if hover_item in group_ids else hover_item
                    orig_sel = getattr(tl, 'selected_track_item_id', None)
                    if orig_sel in group_ids:
                        tl.selected_track_item_id = rep.id
                    orig_start, orig_dur = rep.start_time, rep.duration
                    rep.start_time = g_start
                    rep.duration = g_end - g_start
                    self._draw_generic_track_item(c, rep, lbl_w, w, pps, tl, effective_hover,
                                                  track_y, track_h, color, waveform=True)
                    rep.start_time, rep.duration = orig_start, orig_dur
                    tl.selected_track_item_id = orig_sel
                    # Badge de layers
                    if len(group) > 1:
                        x1 = lbl_w + int(g_start * pps) - tl.scroll_x
                        if x1 >= lbl_w:
                            iy1 = track_y + 3
                            c.create_oval(x1 + 2, iy1 + 1, x1 + 14, iy1 + 13,
                                          fill=color, outline="")
                            c.create_text(x1 + 8, iy1 + 7, text=str(len(group)),
                                          fill="#0a0a0f", font=("Consolas", 7, "bold"))

                # Desenhar grupo arrastado por ultimo (por cima de tudo)
                if dragging_id:
                    for group in groups:
                        group_ids = [i.id for i in group]
                        if dragging_id not in group_ids:
                            continue
                        rep = group[0]
                        g_start = min(i.start_time for i in group)
                        g_end = max(i.start_time + i.duration for i in group)
                        effective_hover = rep.id if hover_item in group_ids else hover_item
                        orig_sel = getattr(tl, 'selected_track_item_id', None)
                        if orig_sel in group_ids:
                            tl.selected_track_item_id = rep.id
                        orig_start, orig_dur = rep.start_time, rep.duration
                        rep.start_time = g_start
                        rep.duration = g_end - g_start
                        self._draw_generic_track_item(c, rep, lbl_w, w, pps, tl, effective_hover,
                                                      track_y, track_h, color, waveform=True)
                        rep.start_time, rep.duration = orig_start, orig_dur
                        tl.selected_track_item_id = orig_sel
                        if len(group) > 1:
                            x1 = lbl_w + int(g_start * pps) - tl.scroll_x
                            if x1 >= lbl_w:
                                iy1 = track_y + 3
                                c.create_oval(x1 + 2, iy1 + 1, x1 + 14, iy1 + 13,
                                              fill=color, outline="")
                                c.create_text(x1 + 8, iy1 + 7, text=str(len(group)),
                                              fill="#0a0a0f", font=("Consolas", 7, "bold"))

    def _draw_fx_item(self, c, item, lbl_w, w, pps, tl, hover_item):
        """Desenha item FX com efeito visual interno."""
        import math
        x1 = lbl_w + int(item.start_time * pps) - tl.scroll_x
        x2 = x1 + int(item.duration * pps)

        if x2 < lbl_w or x1 > w:
            return

        track_y = tl.TRANS_Y
        track_h = tl.TRANS_H
        color = C["purple"]
        is_hover = hover_item == item.id
        is_selected = getattr(tl, 'selected_track_item_id', None) == item.id

        iy1 = track_y + 3
        iy2 = track_y + track_h - 3
        item_fill = "#1a1a3a" if is_selected else "#1a0a2a"

        # Glow neon no hover
        if is_hover and not is_selected:
            c.create_rectangle(x1 - 2, iy1 - 2, x2 + 2, iy2 + 2, fill="", outline="#00ffee", width=2)
            border = "#00ffee"
            bw = 2
        elif is_selected:
            border = "#ffffff"
            bw = 2
        else:
            border = color
            bw = 1

        # Body
        c.create_rectangle(x1, iy1, x2, iy2, fill=item_fill, outline=border, width=bw)

        # Efeito interno baseado no tipo
        name_lower = item.name.lower()
        ix1 = max(x1 + 4, lbl_w)
        ix2 = min(x2 - 4, w)
        mid_y = (iy1 + iy2) // 2

        if "fade in" in name_lower:
            for i in range(0, ix2 - ix1, 3):
                alpha = i / max(1, ix2 - ix1)
                if alpha < 0.8:
                    c.create_line(ix1 + i, iy1 + 2, ix1 + i, iy2 - 2, fill="#4a2a6a", width=1)
        elif "fade out" in name_lower:
            for i in range(0, ix2 - ix1, 3):
                alpha = 1.0 - (i / max(1, ix2 - ix1))
                if alpha < 0.8:
                    c.create_line(ix1 + i, iy1 + 2, ix1 + i, iy2 - 2, fill="#4a2a6a", width=1)
        elif "dissolve" in name_lower or "cross" in name_lower:
            c.create_line(ix1, iy1 + 2, ix2, iy2 - 2, fill="#6b3fa0", width=1)
            c.create_line(ix1, iy2 - 2, ix2, iy1 + 2, fill="#6b3fa0", width=1)
        elif "wipe" in name_lower:
            arrow_y = mid_y
            if "right" in name_lower:
                c.create_line(ix1, arrow_y, ix2, arrow_y, fill="#8855bb", width=2, arrow="last")
            else:
                c.create_line(ix2, arrow_y, ix1, arrow_y, fill="#8855bb", width=2, arrow="last")
        elif "flash" in name_lower:
            cx = (ix1 + ix2) // 2
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                ex = cx + int(8 * math.cos(rad))
                ey = mid_y + int(6 * math.sin(rad))
                c.create_line(cx, mid_y, ex, ey, fill="#bb99dd", width=1)
        elif "glitch" in name_lower:
            import random
            rng = random.Random(hash(item.id))
            for gy in range(iy1 + 3, iy2 - 3, 4):
                gx = ix1 + rng.randint(0, max(1, (ix2 - ix1) // 2))
                gw = rng.randint(4, min(12, ix2 - gx))
                c.create_line(gx, gy, gx + gw, gy, fill="#aa44ff", width=1)
        else:
            for i in range(0, ix2 - ix1, 6):
                c.create_line(ix1 + i, iy2 - 2, ix1 + i + 4, iy1 + 2, fill="#3a1a5a", width=1)

        # Label
        c.create_text(x1 + 5, iy1 + 2, text=item.name, anchor="nw",
                      fill=color, font=("Segoe UI", 7, "bold"))

        # Trim handles
        hw = 4
        c.create_rectangle(x1, iy1, x1 + hw, iy2, fill=color, outline="")
        c.create_rectangle(x2 - hw, iy1, x2, iy2, fill=color, outline="")

    def _draw_generic_track_item(self, c, item, lbl_w, w, pps, tl, hover_item,
                                  track_y, track_h, color, waveform=False):
        """Desenha item generico em qualquer track."""
        x1 = lbl_w + int(item.start_time * pps) - tl.scroll_x
        x2 = x1 + int(item.duration * pps)

        if x2 < lbl_w or x1 > w:
            return

        is_hover = hover_item == item.id
        is_selected = getattr(tl, 'selected_track_item_id', None) == item.id

        iy1 = track_y + 3
        iy2 = track_y + track_h - 3
        item_fill = "#1a1a3a" if is_selected else "#0a1520"

        if is_hover and not is_selected:
            c.create_rectangle(x1 - 2, iy1 - 2, x2 + 2, iy2 + 2, fill="", outline="#00ffee", width=2)
            border = "#00ffee"
            bw = 2
        elif is_selected:
            border = "#ffffff"
            bw = 2
        else:
            border = color
            bw = 1

        c.create_rectangle(x1, iy1, x2, iy2, fill=item_fill, outline=border, width=bw)

        # Waveform se aplicavel
        ix1 = max(x1 + 4, lbl_w)
        ix2 = min(x2 - 4, w)
        mid_y = (iy1 + iy2) // 2
        width_px = ix2 - ix1

        from pathlib import Path
        if waveform and width_px > 2 and item.file_path and Path(item.file_path).exists():
            wf_data = self._get_audio_waveform(item, width_px)
            if wf_data is not None and len(wf_data) > 1:
                # Normalize waveform to fill available height
                peak = max(abs(wf_data.max()), abs(wf_data.min()), 0.01)
                wf_data = wf_data / peak
                amp = (iy2 - iy1) // 2 - 2
                wave_color = color if (is_hover or is_selected) else "#1a3a3a"
                for i in range(len(wf_data) - 1):
                    y1_pt = mid_y - int(wf_data[i] * amp)
                    y2_pt = mid_y - int(wf_data[i+1] * amp)
                    c.create_line(ix1 + i, y1_pt, ix1 + i + 1, y2_pt, fill=wave_color, width=1)
        elif width_px > 2:
            c.create_line(ix1, mid_y, ix2, mid_y, fill=color, width=1, dash=(2, 4))

        # Label
        display_name = item.params.get("block_name", item.name)[:20]
        c.create_text(x1 + 5, iy1 + 1, text=display_name, anchor="nw",
                      fill="#ffffff", font=("Segoe UI", 8, "bold"))

        # Trim handles
        hw = 4
        c.create_rectangle(x1, iy1, x1 + hw, iy2, fill=color, outline="")
        c.create_rectangle(x2 - hw, iy1, x2, iy2, fill=color, outline="")

    def _get_audio_waveform(self, item, width_px):
        """Retorna array representando a waveform real do arquivo de audio (WAV, MP3, OGG, FLAC)."""
        import numpy as np

        cache_key = f"{item.id}_{width_px}"
        if not hasattr(self, '_waveform_cache'):
            self._waveform_cache = {}
        if cache_key in self._waveform_cache:
            return self._waveform_cache[cache_key]

        try:
            from makevid.core.audio_utils import read_audio_mono
            audio, sr = read_audio_mono(item.file_path)

            if len(audio) < width_px:
                result = np.interp(
                    np.linspace(0, len(audio)-1, width_px),
                    np.arange(len(audio)), audio)
            else:
                block_size = max(1, len(audio) // width_px)
                result = np.zeros(width_px)
                for i in range(width_px):
                    start = i * block_size
                    end = min(start + block_size, len(audio))
                    block = audio[start:end]
                    if len(block) > 0:
                        result[i] = block[np.argmax(np.abs(block))]

            self._waveform_cache[cache_key] = result
            return result
        except Exception:
            return None

    def _draw_drag_guide(self, c, lbl_w, w, h, pps, tl):
        """Linha pontilhada vertical + balao com tempo durante drag de track items."""
        guide_time = getattr(tl, '_drag_guide_time', None)
        if guide_time is None:
            return
        px = lbl_w + int(guide_time * pps) - tl.scroll_x
        if px < lbl_w or px > w:
            return
        ruler_h = tl.RULER_H
        # Linha pontilhada do ruler ate o fundo
        c.create_line(px, ruler_h, px, h, fill="#00ccff", width=1, dash=(4, 3))
        # Balao no ruler
        m, s = int(guide_time) // 60, guide_time % 60
        txt = f"{m:02d}:{s:04.1f}"
        tw = len(txt) * 7 + 8
        bx1 = px - tw // 2
        bx2 = px + tw // 2
        by1 = 2
        by2 = 18
        c.create_rectangle(bx1, by1, bx2, by2, fill="#00ccff", outline="#005577")
        c.create_polygon(px - 4, by2, px + 4, by2, px, by2 + 5, fill="#00ccff", outline="")
        c.create_text(px, 10, text=txt, fill="#0a0a0f", font=("Consolas", 9, "bold"))

    def _update_time_label(self, tl, total_dur):
        total = tl.project.total_duration()
        pm, ps = int(tl.playhead_pos) // 60, tl.playhead_pos % 60
        tm, ts = int(total) // 60, total % 60
        tl.time_label.configure(text=f"{pm:02d}:{ps:04.1f} / {tm:02d}:{ts:04.1f}")

    def _update_scrollbar(self, tl, lbl_w, w, pps, total_dur):
        total_w = max(total_dur * pps, 1)
        canvas_w = w - lbl_w
        max_scroll = max(1, total_w - canvas_w + 100)
        pos = (tl.scroll_x / max_scroll) * 100
        tl.scroll_slider.set(min(100, max(0, pos)))
