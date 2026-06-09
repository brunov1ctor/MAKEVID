"""Timeline Widget - Compoe renderer, interaction, thumbnails, fx panel."""

import customtkinter as ctk
from tkinter import Canvas
from makevid.ui.theme import C
from makevid.ui.timeline.canvas_renderer import CanvasRenderer
from makevid.ui.timeline.interaction import TimelineInteraction
from makevid.ui.timeline.thumbnails import ThumbnailManager
from makevid.ui.timeline.fx_audio_panel import FxAudioPanel


class TimelineWidget:
    LBL_W = 62
    RULER_H = 28
    # Posicoes base (recalculadas no draw baseado na altura real)
    VIDEO_Y = 32
    VIDEO_H = 72
    TRANS_Y = 108
    TRANS_H = 32
    VOICE_Y = 144
    VOICE_H = 32
    SFX_Y = 180
    SFX_H = 32
    MUSIC_Y = 216
    MUSIC_H = 32
    AUDIO_Y = 252
    AUDIO_H = 38

    def __init__(self, parent, app):
        self.app = app
        self.zoom = 50
        self.scroll_x = 0
        self.playhead_pos = 0.0
        self.playback_speed = 1.0
        self.selected_clip_id = None
        self.selected_track_item_id = None
        self._dragging = None
        self._trim_preview = None
        self._split_mode = False
        self._audio_split_mode = None
        self._hover_clip_id = None
        self._gif_index = 0
        self._gif_job = None
        self._storyboard_markers = []
        self._hover_storyboard_marker = None
        self._hover_track_item = None
        self._hover_playhead = False
        self._resize_dragging = False

        # Sub-components
        self.thumbs = ThumbnailManager()
        self._renderer = CanvasRenderer(self)
        self._interaction = TimelineInteraction(self)

        # Build UI
        self._frame = ctk.CTkFrame(parent, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=0)
        parent.add(self._frame, minsize=140, height=180)

        # Toolbar
        tb = ctk.CTkFrame(self._frame, height=28, fg_color=C["card"], corner_radius=0)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        ctk.CTkLabel(tb, text="TIMELINE", font=("Segoe UI", 10, "bold"), text_color=C["gold"]).pack(side="left", padx=8)

        # Zoom
        ctk.CTkFrame(tb, width=1, fg_color=C["border"]).pack(side="left", padx=6, fill="y", pady=5)
        ctk.CTkButton(tb, text="-", width=20, height=18, fg_color=C["card"],
                      border_width=1, border_color=C["border"], text_color=C["text2"],
                      font=("Consolas", 12, "bold"), hover_color=C["card_hover"],
                      command=lambda: self._set_zoom(-10)).pack(side="left", padx=1)
        self.zoom_slider = ctk.CTkSlider(tb, from_=1, to=300, number_of_steps=299,
                                         width=80, height=14,
                                         fg_color=C["border"], progress_color=C["gold"],
                                         button_color=C["gold"], button_hover_color="#ffd700",
                                         command=self._on_zoom_slider)
        self.zoom_slider.set(self.zoom)
        self.zoom_slider.pack(side="left", padx=2)
        ctk.CTkButton(tb, text="+", width=20, height=18, fg_color=C["card"],
                      border_width=1, border_color=C["border"], text_color=C["text2"],
                      font=("Consolas", 12, "bold"), hover_color=C["card_hover"],
                      command=lambda: self._set_zoom(10)).pack(side="left", padx=1)

        # Scroll horizontal
        ctk.CTkFrame(tb, width=1, fg_color=C["border"]).pack(side="left", padx=6, fill="y", pady=5)
        self.scroll_slider = ctk.CTkSlider(tb, from_=0, to=100, number_of_steps=200,
                                           width=150, height=16,
                                           fg_color=C["border"], progress_color=C["border"],
                                           button_color=C["cyan"], button_hover_color="#00ffee",
                                           command=self._on_scroll_slider)
        self.scroll_slider.set(0)
        self.scroll_slider.pack(side="left", padx=2)

        # Velocidade
        ctk.CTkFrame(tb, width=1, fg_color=C["border"]).pack(side="left", padx=6, fill="y", pady=5)
        ctk.CTkButton(tb, text="-", width=18, height=18, fg_color=C["card"],
                      border_width=1, border_color=C["border"], text_color=C["text2"],
                      font=("Consolas", 11, "bold"), hover_color=C["card_hover"],
                      command=lambda: self._adjust_speed(-0.25)).pack(side="left", padx=1)
        self._speed_var = ctk.StringVar(value="1.0")
        self._speed_entry = ctk.CTkEntry(tb, textvariable=self._speed_var, width=38, height=20,
                                          fg_color=C["input"], border_color=C["border"],
                                          border_width=1, text_color=C["text"],
                                          font=("Consolas", 9), justify="center")
        self._speed_entry.pack(side="left", padx=1)
        self._speed_entry.bind("<Return>", self._on_speed_change)
        self._speed_entry.bind("<FocusOut>", self._on_speed_change)
        ctk.CTkButton(tb, text="+", width=18, height=18, fg_color=C["card"],
                      border_width=1, border_color=C["border"], text_color=C["text2"],
                      font=("Consolas", 11, "bold"), hover_color=C["card_hover"],
                      command=lambda: self._adjust_speed(0.25)).pack(side="left", padx=1)

        # Botao Exportar + seta para configuracoes
        ctk.CTkButton(tb, text="\u25b2", width=18, height=20,
                      font=("Segoe UI", 7), fg_color=C["purple"],
                      text_color=C["text"], hover_color="#bb77ff",
                      border_color="#bb77ff", border_width=1,
                      command=lambda: self._toggle_export_panel()).pack(side="right", padx=(0, 0))
        ctk.CTkButton(tb, text="EXPORTAR", width=65, height=20,
                      font=("Segoe UI", 8, "bold"), fg_color=C["purple"],
                      text_color=C["text"], hover_color="#bb77ff",
                      border_color="#bb77ff", border_width=1,
                      command=lambda: self._do_export_direct()).pack(side="right", padx=(4, 1))

        self.time_label = ctk.CTkLabel(tb, text="00:00.0 / 00:00.0", text_color=C["text"], font=("Consolas", 11, "bold"))
        self.time_label.pack(side="right", padx=(0, 2))

        # Canvas
        content = ctk.CTkFrame(self._frame, fg_color="transparent")
        content.pack(fill="both", expand=True)

        self.fx_panel = FxAudioPanel(self, self)

        canvas_frame = ctk.CTkFrame(content, fg_color="transparent")
        canvas_frame.pack(side="left", fill="both", expand=True)

        self.canvas = Canvas(canvas_frame, bg="#0a0c14", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Binds
        self.canvas.bind("<Button-1>", self._interaction.on_click)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<B1-Motion>", self._interaction.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._interaction.on_release)
        self.canvas.bind("<MouseWheel>", self._interaction.on_scroll)
        self.canvas.bind("<Motion>", self._interaction.on_hover)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Delete>", self._on_delete)
        self.canvas.configure(takefocus=True)
        self.canvas.bind("<Button-1>", self._interaction.on_click, add="+")
        self.canvas.bind("<space>", self._on_space)
        self.canvas.bind("<Button-3>", self._interaction.on_right_click)
        # Volume por track (scroll na label)
        self.canvas.bind("<Shift-MouseWheel>", self._on_volume_scroll)

    @property
    def project(self):
        return self.app.project

    def _recalc_track_positions(self):
        """Recalcula posicoes das tracks baseado na altura real do canvas."""
        h = self.canvas.winfo_height() or 200
        ruler_h = self.RULER_H
        available = h - ruler_h - 4

        weights = [3.0, 1.2, 1.2, 1.2, 1.2, 1.5]
        total_weight = sum(weights)
        gap = 2
        total_gaps = gap * 5
        track_space = max(96, available - total_gaps)

        sizes = [max(14, int(track_space * w / total_weight)) for w in weights]

        y = ruler_h + 2
        self.VIDEO_Y = y
        self.VIDEO_H = sizes[0]
        y += sizes[0] + gap
        self.TRANS_Y = y
        self.TRANS_H = sizes[1]
        y += sizes[1] + gap
        self.VOICE_Y = y
        self.VOICE_H = sizes[2]
        y += sizes[2] + gap
        self.SFX_Y = y
        self.SFX_H = sizes[3]
        y += sizes[3] + gap
        self.MUSIC_Y = y
        self.MUSIC_H = sizes[4]
        y += sizes[4] + gap
        self.AUDIO_Y = y
        self.AUDIO_H = sizes[5]

    def draw(self):
        self._recalc_track_positions()
        self._renderer.draw()

    def _on_canvas_configure(self, event=None):
        """Redesenha ao mudar tamanho - sem delay para evitar ghost."""
        self._recalc_track_positions()
        self._renderer.draw()

    def _update_playhead_only(self):
        c = self.canvas
        w = c.winfo_width() or 800
        h = c.winfo_height() or 205
        lbl_w = self.LBL_W
        pps = self.zoom
        px = lbl_w + int(self.playhead_pos * pps) - self.scroll_x

        # Mover playhead existente ou criar novo
        if c.find_withtag("playhead_fast"):
            # Mover todos os items do playhead
            items = c.find_withtag("playhead_fast")
            if items and hasattr(self, '_playhead_last_px'):
                dx = px - self._playhead_last_px
                for item_id in items:
                    c.move(item_id, dx, 0)
                self._playhead_last_px = px
            else:
                # Recrear se necessario
                c.delete("playhead_fast")
                c.delete("playhead_full")
                if lbl_w <= px <= w:
                    c.create_rectangle(px - 3, 0, px + 3, h, fill="#330000", outline="", tags="playhead_fast")
                    c.create_line(px, 0, px, h, fill="#ff2222", width=3, tags="playhead_fast")
                    c.create_polygon(px - 10, 0, px + 10, 0, px + 5, 7, px, 14, px - 5, 7,
                                     fill="#ff2222", outline="#ff6666", width=1, tags="playhead_fast")
                    c.create_oval(px - 2, 4, px + 2, 10, fill="#ffffff", outline="", tags="playhead_fast")
                self._playhead_last_px = px
        else:
            c.delete("playhead_full")
            if lbl_w <= px <= w:
                c.create_rectangle(px - 3, 0, px + 3, h, fill="#330000", outline="", tags="playhead_fast")
                c.create_line(px, 0, px, h, fill="#ff2222", width=3, tags="playhead_fast")
                c.create_polygon(px - 10, 0, px + 10, 0, px + 5, 7, px, 14, px - 5, 7,
                                 fill="#ff2222", outline="#ff6666", width=1, tags="playhead_fast")
                c.create_oval(px - 2, 4, px + 2, 10, fill="#ffffff", outline="", tags="playhead_fast")
            self._playhead_last_px = px

        total = self.project.total_duration()
        pm, ps = int(self.playhead_pos) // 60, self.playhead_pos % 60
        tm, ts = int(total) // 60, total % 60
        self.time_label.configure(text=f"{pm:02d}:{ps:04.1f} / {tm:02d}:{ts:04.1f}")

    def _set_zoom(self, delta):
        self.zoom = max(1, min(300, self.zoom + delta))
        self.zoom_slider.set(self.zoom)
        self.draw()

    def _on_zoom_slider(self, value):
        self.zoom = int(value)
        self.draw()

    def _on_speed_change(self, event=None):
        try:
            val = float(self._speed_var.get().replace(",", "."))
            self.playback_speed = max(0.1, min(10.0, val))
            self._speed_var.set(f"{self.playback_speed:.1f}")
        except ValueError:
            self._speed_var.set(f"{self.playback_speed:.1f}")
        # Reiniciar audio em tempo real se estiver tocando
        if hasattr(self, 'app') and hasattr(self.app, 'preview_panel'):
            player = self.app.preview_panel.player
            if player.is_playing and not player.is_paused:
                player._restart_audio_at_current_pos()

    def _adjust_speed(self, delta):
        import logging
        self.playback_speed = max(0.1, min(10.0, self.playback_speed + delta))
        self._speed_var.set(f"{self.playback_speed:.1f}")
        logging.getLogger("player").info(f"Speed changed to {self.playback_speed:.1f}x")
        # Reiniciar audio em tempo real se estiver tocando
        if hasattr(self, 'app') and hasattr(self.app, 'preview_panel'):
            player = self.app.preview_panel.player
            if player.is_playing and not player.is_paused:
                player._restart_audio_at_current_pos()
    def _on_scroll_slider(self, value):
        total_dur = max(self.project.total_duration(), 10)
        total_w = total_dur * self.zoom
        canvas_w = self.canvas.winfo_width() or 800
        max_scroll = max(0, total_w - canvas_w + 100)
        self.scroll_x = int((value / 100) * max_scroll)
        self.draw()

    def _on_delete(self, event=None):
        if self.selected_track_item_id:
            # Encontrar o item selecionado
            item = next((i for i in self.project.track_items if i.id == self.selected_track_item_id), None)
            if item:
                # Remover todos os items no mesmo bloco (mesmo clip_index)
                if item.clip_index >= 0:
                    overlapping = [i for i in self.project.get_track_items(item.track)
                                   if i.clip_index == item.clip_index]
                else:
                    overlapping = [i for i in self.project.get_track_items(item.track)
                                   if abs(i.start_time - item.start_time) < 0.05]
                for ov in overlapping:
                    self.project.remove_track_item(ov.id)
            self.selected_track_item_id = None
            from makevid.config import PROJECTS_DIR
            self.project.save(PROJECTS_DIR)
            self.fx_panel.hide()
            self.draw()
            return
        if self.selected_clip_id:
            # Mostrar dica em vez de deletar
            self._show_delete_hint()

    def _show_delete_hint(self):
        """Mostra balao de dica sobre como deletar clip."""
        clip = self.project.get_clip(self.selected_clip_id)
        if not clip:
            return
        # Posicao do clip na tela
        pps = self.zoom
        lbl_w = self.LBL_W
        current = sum(c.duration for c in sorted(self.project.clips, key=lambda c: c.position)
                      if c.position < clip.position)
        cx = lbl_w + int((current + clip.duration / 2) * pps) - self.scroll_x
        cy = self.VIDEO_Y + self.VIDEO_H + 4

        # Desenhar balao
        self.canvas.delete("hint_bubble")
        text = "Use o menu do clip\n(click direito)"
        # Fundo do balao
        bw, bh = 120, 30
        x1, y1 = cx - bw // 2, cy
        x2, y2 = cx + bw // 2, cy + bh
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#1a0808", outline="#ff4444",
                                     width=1, tags="hint_bubble")
        # Triangulo apontando para cima
        self.canvas.create_polygon(cx - 6, y1, cx + 6, y1, cx, y1 - 6,
                                   fill="#1a0808", outline="#ff4444", tags="hint_bubble")
        # Texto
        self.canvas.create_text(cx, y1 + bh // 2, text=text,
                                fill="#ff4444", font=("Segoe UI", 8, "bold"),
                                tags="hint_bubble")
        # Remover apos 3s
        self.canvas.after(3000, lambda: self.canvas.delete("hint_bubble"))

    def _on_space(self, event=None):
        player = self.app.preview_panel.player
        if player.is_playing:
            self.app.preview_panel._on_pause_click()
        elif player.is_paused:
            self.app.preview_panel._on_resume_click()
        else:
            self.app.preview_panel._on_play_click(lambda: player.play())

    def _on_volume_scroll(self, event):
        """Shift+Scroll ajusta volume da track sob o mouse."""
        y = event.y
        track_key = None
        if self.VOICE_Y <= y <= self.VOICE_Y + self.VOICE_H:
            track_key = "voice"
        elif self.SFX_Y <= y <= self.SFX_Y + self.SFX_H:
            track_key = "sfx"
        elif self.MUSIC_Y <= y <= self.MUSIC_Y + self.MUSIC_H:
            track_key = "music"
        elif self.AUDIO_Y <= y <= self.AUDIO_Y + self.AUDIO_H:
            track_key = "audio"
        if not track_key:
            return
        delta = 0.05 if event.delta > 0 else -0.05
        vol = self.project.track_volumes.get(track_key, 1.0)
        vol = max(0.0, min(2.0, vol + delta))
        self.project.track_volumes[track_key] = round(vol, 2)
        self.draw()
        # Reiniciar audio se tocando
        player = self.app.preview_panel.player
        if player.is_playing:
            player._stop_audio()
            player._start_audio()
        from makevid.config import PROJECTS_DIR
        self.project.save(PROJECTS_DIR)

    def _on_double_click(self, event):
        import os
        from pathlib import Path
        lbl_w = self.LBL_W
        if event.x < lbl_w:
            return
        x = (event.x - lbl_w) + self.scroll_x
        t = x / self.zoom
        vy, vh = self.VIDEO_Y, self.VIDEO_H
        if not (vy <= event.y <= vy + vh):
            return
        current = 0.0
        for clip in sorted(self.project.clips, key=lambda c: c.position):
            end = current + clip.duration
            if current <= t <= end:
                if clip.video_path and Path(clip.video_path).exists():
                    os.startfile(clip.video_path)
                return
            current = end

    def enter_split_mode(self):
        self._split_mode = True
        self.canvas.configure(cursor="crosshair")

    def enter_audio_split_mode(self, track):
        """Ativa modo de corte para faixas de audio."""
        self._audio_split_mode = track
        self.canvas.configure(cursor="crosshair")

    def exit_split_mode(self):
        self._split_mode = False
        self._audio_split_mode = None
        self.canvas.configure(cursor="")

    def _start_gif(self, clip_id):
        self._hover_clip_id = clip_id
        self._gif_index = 0
        self._animate_gif()

    def _stop_gif(self):
        self._hover_clip_id = None
        if self._gif_job:
            self.canvas.after_cancel(self._gif_job)
            self._gif_job = None
        self.draw()

    def _animate_gif(self):
        if self._hover_clip_id is None:
            return
        self._gif_index += 1
        self.draw()
        self._gif_job = self.canvas.after(150, self._animate_gif)

    def invalidate_thumbnail(self, clip_id):
        self.thumbs.invalidate(clip_id)

    def _quick_export(self):
        """Abre painel e dispara export."""
        if not self.fx_panel._visible:
            self.fx_panel.show_export()
        self.fx_panel._export_panel._do_export()

    def _toggle_export_panel(self):
        """Abre/fecha painel de configuracao de export."""
        if self.fx_panel._visible and hasattr(self.fx_panel, '_export_panel') and self.fx_panel._export_panel._export_status:
            self.fx_panel.hide()
        else:
            self.fx_panel.show_export()


    def _do_export_direct(self):
        """Exporta usando o painel lateral com progresso visual."""
        import time as _time
        import customtkinter as ctk
        from makevid.ui.theme import C
        from makevid.config import OUTPUTS_DIR
        from pathlib import Path
        import shutil, subprocess, re
        import numpy as np

        app = self.app
        clips = sorted(app.project.clips, key=lambda x: x.position)
        done = [c for c in clips if c.status == "done" and c.video_path]
        if not done:
            from tkinter import messagebox
            messagebox.showinfo("Info", "Nenhum clip pronto para exportar")
            return

        ep = self.fx_panel._export_panel
        name = ep.get_export_name()
        total_dur = app.project.total_duration()

        # Abrir painel lateral para mostrar progresso
        if self.fx_panel._visible:
            self.fx_panel.hide()
        app.generator_panel.container.pack_forget()
        if not app.preview_panel.panel.winfo_ismapped():
            app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self.fx_panel._frame = ctk.CTkFrame(app._main, width=280, fg_color=C["panel"],
                                             border_color=C["gold"], border_width=1, corner_radius=6)
        self.fx_panel._frame.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self.fx_panel._visible = True
        f = self.fx_panel._frame

        # Header
        header = ctk.CTkFrame(f, fg_color="transparent", height=28)
        header.pack(fill="x", padx=8, pady=(8, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="\U0001f3ac EXPORTANDO", font=("Segoe UI", 12, "bold"),
                     text_color=C["gold"]).pack(side="left")
        ctk.CTkFrame(f, height=2, fg_color=C["gold"]).pack(fill="x", padx=8, pady=(4, 8))

        # Info
        ctk.CTkLabel(f, text=f"{name}\n{len(done)} clips | {total_dur:.1f}s | {app.project.output_fps}fps",
                     font=("Consolas", 9), text_color=C["text"], justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        # Barra de progresso
        progress = ctk.CTkProgressBar(f, height=14, fg_color="#1a1a2e",
                                       progress_color=C["gold"], corner_radius=4)
        progress.pack(fill="x", padx=10, pady=(0, 4))
        progress.set(0)

        # Status
        status_lbl = ctk.CTkLabel(f, text="Preparando...", font=("Segoe UI", 10),
                                   text_color=C["text2"])
        status_lbl.pack(anchor="w", padx=10, pady=(0, 2))

        # Detalhes
        detail_lbl = ctk.CTkLabel(f, text="", font=("Consolas", 8),
                                   text_color=C["text3"])
        detail_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        # Resultado
        result_lbl = ctk.CTkLabel(f, text="", font=("Segoe UI", 10, "bold"),
                                   text_color=C["cyan"], wraplength=250, justify="left")
        result_lbl.pack(anchor="w", padx=10, pady=(0, 4))

        app.update()

        # Export
        try:
            safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') or "video_final"
            fps = app.project.output_fps or 16
            width = app.project.output_width or 832
            height = app.project.output_height or 480

            import cv2
            from makevid.core.fx_processor import apply_fx_to_frame
            tmp_video = OUTPUTS_DIR / app.project.id / f"_tmp_{safe_name}.mp4"
            tmp_video.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(tmp_video), fourcc, fps, (width, height))
            fx_items = app.project.get_track_items("fx")
            frame_count = 0
            total_frames = int(total_dur * fps)
            export_start = _time.time()

            for clip in clips:
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    cap = cv2.VideoCapture(str(clip.video_path))
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame = cv2.resize(frame, (width, height))
                        current_time = frame_count / fps
                        if fx_items:
                            frame_rgb = frame[:, :, ::-1]
                            frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, current_time, total_dur)
                            frame = frame_rgb[:, :, ::-1]
                        writer.write(frame)
                        frame_count += 1
                        if frame_count % 20 == 0 and total_frames > 0:
                            pct = frame_count / total_frames
                            elapsed = _time.time() - export_start
                            eta = int(elapsed / frame_count * (total_frames - frame_count))
                            try:
                                progress.set(pct * 0.7)
                                status_lbl.configure(text=f"Video: {int(pct*100)}%")
                                detail_lbl.configure(text=f"Frame {frame_count}/{total_frames} | ~{eta}s")
                                app.update()
                            except Exception:
                                pass
                    cap.release()
                else:
                    black = np.zeros((height, width, 3), dtype=np.uint8)
                    for _ in range(int(clip.duration * fps)):
                        writer.write(black)
                        frame_count += 1
            writer.release()

            # Audio
            try:
                progress.set(0.75)
                status_lbl.configure(text="Mixando audio...")
                detail_lbl.configure(text="")
                app.update()
            except Exception:
                pass

            tmp_audio = None
            enabled = ep.get_enabled_tracks()
            all_items = []
            for t in enabled:
                all_items.extend(app.project.get_track_items(t))
            if all_items:
                tmp_audio = ep._mix_audio(all_items, total_dur, OUTPUTS_DIR / app.project.id, safe_name)

            # Combinar
            try:
                progress.set(0.9)
                status_lbl.configure(text="Finalizando...")
                app.update()
            except Exception:
                pass

            output_path = OUTPUTS_DIR / app.project.id / f"{safe_name}.mp4"
            has_ffmpeg = shutil.which("ffmpeg")
            if tmp_audio and has_ffmpeg:
                cmd = [
                    "ffmpeg", "-y", "-i", str(tmp_video), "-i", str(tmp_audio),
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest",
                    str(output_path),
                ]
                subprocess.run(cmd, capture_output=True, check=True, timeout=300)
                tmp_video.unlink(missing_ok=True)
                tmp_audio.unlink(missing_ok=True)
            elif tmp_audio:
                shutil.move(str(tmp_video), str(output_path))
                audio_out = OUTPUTS_DIR / app.project.id / f"{safe_name}_audio.wav"
                shutil.move(str(tmp_audio), str(audio_out))
                downloads = Path.home() / "Downloads"
                shutil.copy2(str(audio_out), str(downloads / f"{safe_name}_audio.wav"))
            else:
                shutil.move(str(tmp_video), str(output_path))

            # Copiar para Downloads
            downloads = Path.home() / "Downloads"
            output_dl = downloads / f"{safe_name}.mp4"
            shutil.copy2(str(output_path), str(output_dl))

            size_mb = output_path.stat().st_size / 1e6
            elapsed_total = _time.time() - export_start

            progress.set(1.0)
            status_lbl.configure(text="")
            detail_lbl.configure(text=f"{elapsed_total:.1f}s | {size_mb:.1f} MB | {frame_count} frames")
            if tmp_audio and not has_ffmpeg:
                result_lbl.configure(
                    text="\u2714 Salvo em Downloads (video + audio separados)\n"
                         "\u26a0 Instale FFmpeg para unificar",
                    text_color="#ffaa00")
            else:
                result_lbl.configure(text=f"\u2714 {safe_name}.mp4 salvo em Downloads!")
            app.update()
            print(f"[Export] SUCESSO: {output_dl} ({size_mb:.1f} MB) em {elapsed_total:.1f}s")

            # Fechar apos 3s
            f.after(3000, self.fx_panel.hide)

        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                progress.set(0)
                status_lbl.configure(text=f"Erro: {str(e)[:50]}", text_color="#ff4444")
                app.update()
            except Exception:
                pass
