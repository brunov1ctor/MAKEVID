"""Track Editor - Paineis de edicao para tracks VOICE, SFX e MUSIC com layers individuais."""

import customtkinter as ctk
import tkinter as tk
from makevid.ui.theme import C


class TrackEditor:
    """Editor que abre painel com layers separados por item na track."""

    def __init__(self, fx_panel):
        self.fx_panel = fx_panel
        self._preview_playing = False
        self._preview_job = None
        self._preview_canvas = None
        self._layer_previews = {}  # id -> playing state
        self._layer_canvases = {}  # id -> {canvas, time_lbl, btn, color}

    def build(self, frame, item):
        """Despacha para o editor correto baseado no track do item."""
        self._stop_all_previews()
        self._current_item = item
        self._play_all_playing = False
        self._play_all_btn = None
        # Limpar estados de loop anteriores
        self._voice_loop = None
        self._sfx_loop = None
        self._music_loop = None
        self._audio_loop = None
        if item.track == "voice":
            self._build_voice_editor(frame, item)
        elif item.track == "sfx":
            self._build_sfx_editor(frame, item)
        elif item.track == "music":
            self._build_music_editor(frame, item)
        elif item.track == "audio":
            self._build_audio_editor(frame, item)

    def _build_header(self, frame, title, color, item):
        header = ctk.CTkFrame(frame, fg_color="transparent", height=32)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 13, "bold"),
                     text_color=color).pack(side="left")
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=self._close_editor).pack(side="right")
        ctk.CTkFrame(frame, height=2, fg_color=color).pack(fill="x", padx=10, pady=(4, 4))

        # Registrar todo o frame do painel como drop target
        self._register_panel_drop(frame, item.track, color)

    def _register_panel_drop(self, frame, track, color):
        """Registra o painel inteiro como alvo de drag-and-drop."""
        try:
            # Verificar se tkdnd esta carregado na app
            app = self.fx_panel.timeline.app
            if not getattr(app, '_has_dnd', False):
                return
            from tkinterdnd2 import DND_FILES
            frame.drop_target_register(DND_FILES)
            frame.dnd_bind('<<Drop>>', lambda e: self._on_drop_files(e, track))
        except Exception:
            pass

    def _on_drop_files(self, event, track):
        """Processa arquivos soltos na zona de drop."""
        from pathlib import Path
        from makevid.config import AUDIO_DIR, PROJECTS_DIR
        import shutil

        # Parsear paths (tkdnd retorna paths entre {} se tem espacos)
        raw = event.data
        paths = []
        if '{' in raw:
            import re
            paths = re.findall(r'\{([^}]+)\}', raw)
        else:
            paths = raw.split()

        tl = self.fx_panel.timeline
        added = 0
        # Usar posicao e duracao do item atual (layer dentro do mesmo bloco)
        ref_item = self._current_item
        for p in paths:
            src = Path(p)
            if not src.exists():
                continue
            if src.suffix.lower() not in ('.wav', '.mp3', '.ogg', '.flac'):
                continue

            dest_dir = AUDIO_DIR / tl.project.id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            if not dest.exists():
                shutil.copy2(str(src), str(dest))

            # Duracao real do arquivo
            dur = ref_item.duration
            try:
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(str(dest)) or ref_item.duration
            except Exception:
                pass

            # Mesmo clip_index do item clicado = fica como layer no mesmo retangulo
            tl.project.add_track_item(
                name=src.stem[:20], track=track,
                start_time=ref_item.start_time, duration=dur, file_path=str(dest),
                clip_index=ref_item.clip_index)
            added += 1

        if added > 0:
            tl.project.save(PROJECTS_DIR)
            tl.draw()
            # Reabrir editor para mostrar novos layers
            item = self._current_item
            self.fx_panel.hide()
            self.fx_panel.show_track_editor(item)

    def _build_layer_item(self, parent, item, color, show_params=True):
        """Constroi um layer completo para um item: waveform destacada + playhead + controles."""
        folder = ctk.CTkFrame(parent, fg_color="#0c1018", corner_radius=6,
                              border_color=color, border_width=2)
        folder.pack(fill="x", pady=4)

        # Header do layer - mais destaque
        lh = ctk.CTkFrame(folder, fg_color=color, corner_radius=4, height=26)
        lh.pack(fill="x", padx=4, pady=(4, 0))
        lh.pack_propagate(False)

        expanded_var = ctk.BooleanVar(value=True)
        toggle_btn = ctk.CTkButton(lh, text="\u25bc", width=16, height=16,
                                    font=("Consolas", 8, "bold"), fg_color="transparent",
                                    text_color="#0a0a0f", hover_color="#cccccc")
        toggle_btn.pack(side="left", padx=(4, 0))

        # Nome editavel (click para renomear)
        name_lbl = ctk.CTkLabel(lh, text=f"\u266b {item.name[:20]}", font=("Segoe UI", 9, "bold"),
                     text_color="#0a0a0f", cursor="xterm")
        name_lbl.pack(side="left", padx=4)
        def _make_rename_click(itm, lbl, header):
            def cmd(e):
                self._inline_rename(itm, lbl, header, color)
            return cmd
        name_lbl.bind("<Button-1>", _make_rename_click(item, name_lbl, lh))

        # Botao excluir layer
        def _make_delete_cmd(itm):
            def cmd():
                self._delete_layer(itm)
            return cmd
        ctk.CTkButton(lh, text="\u2715", width=16, height=16,
                      font=("Consolas", 9, "bold"), fg_color="transparent",
                      text_color="#0a0a0f", hover_color="#ff4444",
                      command=_make_delete_cmd(item)).pack(side="right", padx=(0, 4))

        ctk.CTkLabel(lh, text=f"{item.duration:.1f}s", font=("Consolas", 9, "bold"),
                     text_color="#0a0a0f").pack(side="right", padx=2)

        # Conteudo colapsavel
        content = ctk.CTkFrame(folder, fg_color="transparent")
        content.pack(fill="x", padx=4, pady=(4, 6))

        toggle_btn.configure(command=lambda c=content, b=toggle_btn, v=expanded_var:
                             self._toggle_layer(c, b, v))

        # === WAVEFORM DESTACADA ===
        wf_frame = ctk.CTkFrame(content, fg_color="#040810", corner_radius=4,
                                 border_color=color, border_width=1)
        wf_frame.pack(fill="x", padx=2, pady=(2, 4))

        # Canvas para waveform - altura fixa, largura segue o parent
        wf_canvas = tk.Canvas(wf_frame, height=44, bg="#040810", highlightthickness=0,
                              cursor="hand2")
        wf_canvas.pack(fill="x", padx=2, pady=2)

        # Tempo label
        time_lbl = ctk.CTkLabel(wf_frame, text="0.0s / {:.1f}s".format(item.duration),
                                 font=("Consolas", 7), text_color=C["text3"])
        time_lbl.pack(anchor="e", padx=4, pady=(0, 2))

        # Redesenhar waveform quando canvas muda de tamanho (com debounce)
        def _on_canvas_resize(event, cv=wf_canvas, it=item, cl=color):
            if event.width > 10:
                # Debounce: cancelar redraw anterior
                job_attr = f'_resize_job_{id(cv)}'
                prev = getattr(self, job_attr, None)
                if prev:
                    cv.after_cancel(prev)
                setattr(self, job_attr, cv.after(100, lambda: self._draw_layer_waveform(cv, it, cl)))
        wf_canvas.bind("<Configure>", _on_canvas_resize)

        # Click na waveform = seek
        def _make_seek_cmd(it, cv, cl, tl):
            return lambda e: self._seek_layer(e, it, cv, cl, tl)
        wf_canvas.bind("<Button-1>", _make_seek_cmd(item, wf_canvas, color, time_lbl))

        # === BOTAO PREVIEW INDIVIDUAL ===
        preview_frame = ctk.CTkFrame(content, fg_color="transparent", height=30)
        preview_frame.pack(fill="x", padx=2, pady=(2, 4))
        preview_frame.pack_propagate(False)

        play_btn = ctk.CTkButton(preview_frame, text="\u25b6 Play", width=60, height=22,
                                  font=("Segoe UI", 9, "bold"), fg_color=color,
                                  text_color="#0a0a0f", hover_color="#ffffff",
                                  corner_radius=4)
        play_btn.pack(side="left", padx=(0, 6))

        # Usar closure com dict para evitar problemas de captura
        def _make_play_cmd(it, bt, cl, cv, tl):
            def cmd():
                self._play_single_item(it, bt, cl, cv, tl)
            return cmd
        play_btn.configure(command=_make_play_cmd(item, play_btn, color, wf_canvas, time_lbl))

        # Botao duplicar
        def _make_dup_cmd(itm):
            def cmd():
                self._duplicate_layer(itm)
            return cmd
        ctk.CTkButton(preview_frame, text="Duplicar", width=50, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color=C["card"],
                      text_color=C["text2"], hover_color="#1a2a3a",
                      corner_radius=4, command=_make_dup_cmd(item)).pack(side="left", padx=(0, 4))

        ctk.CTkLabel(preview_frame, text=f"Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(side="right")

        # Guardar canvas ref para animacao
        if not hasattr(self, '_layer_canvases'):
            self._layer_canvases = {}
        self._layer_canvases[item.id] = {
            "canvas": wf_canvas, "time_lbl": time_lbl, "btn": play_btn, "color": color,
            "item": item
        }

        if show_params:
            self._build_layer_params(content, item, color)

        return folder

    def _build_layer_params(self, parent, item, color):
        """Controles profissionais: volume, pan, fade, speed, reverb, room."""
        from makevid.ui.menus import _ToolTip
        pf = ctk.CTkFrame(parent, fg_color="#080c14", corner_radius=4)
        pf.pack(fill="x", padx=2, pady=(4, 0))

        def _make_param_slider(parent_f, label, param_key, from_, to, default, unit, tip, sl_color):
            """Cria slider que salva no item.params em tempo real e reinicia play."""
            f = ctk.CTkFrame(parent_f, fg_color="transparent")
            f.pack(fill="x", padx=4, pady=2)
            lbl = ctk.CTkLabel(f, text=label, font=("Segoe UI", 9, "bold"), text_color=C["text"],
                               width=56)
            lbl.pack(side="left")
            _ToolTip(lbl, tip)
            val_lbl = ctk.CTkLabel(f, text=f"{default}{unit}", font=("Consolas", 9, "bold"),
                                    text_color=C["text"], width=50)
            val_lbl.pack(side="right")
            slider = ctk.CTkSlider(f, from_=from_, to=to, height=14,
                                    fg_color="#1a1a2a", progress_color=sl_color,
                                    button_color=sl_color, button_hover_color="#ffffff")
            slider.set(default)
            slider.pack(side="left", fill="x", expand=True, padx=(4, 4))

            def _on_change(v, l=val_lbl, u=unit, k=param_key, itm=item):
                l.configure(text=f"{int(v)}{u}")
                itm.params[k] = str(int(v))
                # Reiniciar play em tempo real
                if self._layer_previews.get(itm.id, False):
                    layer_info = self._layer_canvases.get(itm.id)
                    if layer_info:
                        import sounddevice as sd
                        sd.stop()
                        self._layer_previews[itm.id] = False
                        layer_info["canvas"].delete("playhead")
                        self._start_single_item(itm, layer_info["btn"], layer_info["color"],
                                                layer_info["canvas"], layer_info["time_lbl"])
            slider.configure(command=_on_change)
            # Efeito hover no label
            lbl.bind("<Enter>", lambda e, l=lbl: l.configure(font=("Segoe UI", 10, "bold"), text_color=color))
            lbl.bind("<Leave>", lambda e, l=lbl: l.configure(font=("Segoe UI", 9, "bold"), text_color=C["text"]))
            return slider

        # Offset visual (mini-timeline arrastavel)
        # O bloco eh definido pelo span do grupo de items sobrepostos
        group = self._get_overlapping_items(self._current_item, self._current_item.track)
        g_start = min(i.start_time for i in group)
        g_end = max(i.start_time + i.duration for i in group)
        # Se o layer ocupa o bloco inteiro, nao precisa de offset
        max_offset = max(0, (g_end - g_start) - item.duration)

        if max_offset > 0.1:
            import tkinter as tk
            block_dur = g_end - g_start
            off_frame = ctk.CTkFrame(pf, fg_color="#060a12", corner_radius=4,
                                     border_color="#44aaff", border_width=1)
            off_frame.pack(fill="x", padx=4, pady=(4, 2))

            ctk.CTkLabel(off_frame, text="POSICAO", font=("Segoe UI", 7, "bold"),
                         text_color="#44aaff").pack(anchor="w", padx=4, pady=(2, 0))

            off_canvas = tk.Canvas(off_frame, height=24, bg="#060a12",
                                   highlightthickness=0, cursor="sb_h_double_arrow")
            off_canvas.pack(fill="x", padx=3, pady=(1, 3))

            # Guardar info para drag
            off_data = {"item": item, "g_start": g_start, "block_dur": block_dur,
                        "canvas": off_canvas, "dragging": False}

            def _draw_offset_bar(od=off_data):
                c = od["canvas"]
                c.delete("all")
                w = c.winfo_width() or 200
                h = 24
                bd = od["block_dur"]
                itm = od["item"]
                if bd <= 0:
                    return
                # Fundo (bloco inteiro)
                c.create_rectangle(0, 0, w, h, fill="#0a0e18", outline="")
                # Posicao do layer dentro do bloco
                ratio_start = (itm.start_time - od["g_start"]) / bd
                ratio_end = (itm.start_time + itm.duration - od["g_start"]) / bd
                x1 = int(w * ratio_start)
                x2 = int(w * ratio_end)
                # Mini-waveform no bloco do layer
                c.create_rectangle(x1, 2, x2, h - 2, fill="#1a2a3a", outline="#44aaff", width=1)
                # Waveform simplificada dentro
                from pathlib import Path
                if itm.file_path and Path(itm.file_path).exists():
                    try:
                        from makevid.core.audio_utils import read_audio_mono
                        import numpy as np
                        audio, sr = read_audio_mono(itm.file_path)
                        if len(audio) > 10:
                            seg_w = x2 - x1
                            if seg_w > 4:
                                block_size = max(1, len(audio) // seg_w)
                                mid = h // 2
                                amp = mid - 4
                                for px in range(seg_w):
                                    s = px * block_size
                                    e = min(s + block_size, len(audio))
                                    blk = audio[s:e]
                                    if len(blk) > 0:
                                        mn, mx = float(blk.min()), float(blk.max())
                                        y1p = mid - int(mx * amp)
                                        y2p = mid - int(mn * amp)
                                        if y1p == y2p:
                                            y2p += 1
                                        c.create_line(x1 + px, y1p, x1 + px, y2p,
                                                      fill="#44aaff", width=1)
                    except Exception:
                        pass
                # Labels
                c.create_text(x1 + 3, 3, text=f"{itm.start_time - od['g_start']:.1f}s",
                              anchor="nw", fill="#88ccff", font=("Consolas", 6))

            def _on_off_press(e, od=off_data):
                od["dragging"] = True
                od["drag_x"] = e.x

            def _on_off_drag(e, od=off_data):
                if not od["dragging"]:
                    return
                c = od["canvas"]
                w = c.winfo_width() or 200
                bd = od["block_dur"]
                itm = od["item"]
                dx = e.x - od["drag_x"]
                dt = (dx / w) * bd
                new_start = itm.start_time + dt
                # Limitar ao bloco
                new_start = max(od["g_start"], min(new_start, od["g_start"] + bd - itm.duration))
                itm.start_time = round(new_start, 2)
                od["drag_x"] = e.x
                _draw_offset_bar(od)
                self.fx_panel.timeline.draw()

            def _on_off_release(e, od=off_data):
                od["dragging"] = False
                from makevid.config import PROJECTS_DIR
                self.fx_panel.timeline.project.save(PROJECTS_DIR)

            off_canvas.bind("<Button-1>", _on_off_press)
            off_canvas.bind("<B1-Motion>", _on_off_drag)
            off_canvas.bind("<ButtonRelease-1>", _on_off_release)
            off_canvas.bind("<Configure>", lambda e: _draw_offset_bar(off_data))
        # Volume
        vol = int(item.params.get("volume", 80))
        vol_slider = _make_param_slider(pf, "VOL", "volume", 0, 200, vol, "%",
            "Volume de 0% a 200%.\n100% = original. >100% = amplificado.", color)

        # Pan
        pan = int(item.params.get("pan", 0))
        pan_f = ctk.CTkFrame(pf, fg_color="transparent")
        pan_f.pack(fill="x", padx=4, pady=2)
        pan_label = ctk.CTkLabel(pan_f, text="PAN", font=("Segoe UI", 9, "bold"),
                                  text_color=C["text"], width=56)
        pan_label.pack(side="left")
        _ToolTip(pan_label, "Posicao estereo.\nL = esquerdo, R = direito, C = centro.")
        pan_lbl = ctk.CTkLabel(pan_f, text="C" if pan == 0 else f"L{abs(pan)}" if pan < 0 else f"R{pan}",
                                font=("Consolas", 9, "bold"), text_color=C["text"], width=50)
        pan_lbl.pack(side="right")
        pan_slider = ctk.CTkSlider(pan_f, from_=-100, to=100, height=14,
                                    fg_color="#1a1a2a", progress_color=color,
                                    button_color=color, button_hover_color="#ffffff")
        pan_slider.set(pan)
        pan_slider.pack(side="left", fill="x", expand=True, padx=(4, 4))
        def _pan_change(v, l=pan_lbl, itm=item):
            iv = int(v)
            l.configure(text="C" if iv == 0 else f"L{abs(iv)}" if iv < 0 else f"R{iv}")
            itm.params["pan"] = str(iv)
            # Reiniciar play em tempo real
            if self._layer_previews.get(itm.id, False):
                layer_info = self._layer_canvases.get(itm.id)
                if layer_info:
                    import sounddevice as sd
                    sd.stop()
                    self._layer_previews[itm.id] = False
                    layer_info["canvas"].delete("playhead")
                    self._start_single_item(itm, layer_info["btn"], layer_info["color"],
                                            layer_info["canvas"], layer_info["time_lbl"])
        pan_slider.configure(command=_pan_change)
        pan_label.bind("<Enter>", lambda e: pan_label.configure(font=("Segoe UI", 10, "bold"), text_color=color))
        pan_label.bind("<Leave>", lambda e: pan_label.configure(font=("Segoe UI", 9, "bold"), text_color=C["text"]))

        # Fade In
        fi = int(item.params.get("fade_in", 0))
        fi_s = _make_param_slider(pf, "FADE IN", "fade_in", 0, 100, fi, "%",
            "Audio entra gradualmente.\n0 = corte seco, 100 = fade na duracao total.", "#6b3fa0")

        # Fade Out
        fo = int(item.params.get("fade_out", 0))
        fo_s = _make_param_slider(pf, "FADE OUT", "fade_out", 0, 100, fo, "%",
            "Audio sai gradualmente.\n0 = corte seco, 100 = fade na duracao total.", "#6b3fa0")

        # Reverb (eco/sala)
        reverb = int(item.params.get("reverb", 0))
        rev_s = _make_param_slider(pf, "REVERB", "reverb", 0, 100, reverb, "%",
            "Reverberacao (eco).\nSimula som em ambiente fechado.\n0 = seco, 100 = cathedral.", "#8855bb")

        # Room Size (distancia)
        room = int(item.params.get("room", 0))
        room_s = _make_param_slider(pf, "ROOM", "room", 0, 100, room, "%",
            "Tamanho da sala / distancia.\nSimula som distante ou proximo.\n0 = proximo, 100 = muito distante.", "#5588bb")

        # Low Pass (abafamento)
        lowpass = int(item.params.get("lowpass", 100))
        lp_s = _make_param_slider(pf, "TONE", "lowpass", 0, 100, lowpass, "%",
            "Filtro tonal (low-pass).\n100 = brilhante/original.\n0 = abafado/distante.", "#bb8844")

        # Speed
        speed = int(item.params.get("speed", 100))
        spd_f = ctk.CTkFrame(pf, fg_color="transparent")
        spd_f.pack(fill="x", padx=4, pady=2)
        spd_label = ctk.CTkLabel(spd_f, text="SPEED", font=("Segoe UI", 9, "bold"),
                                  text_color=C["text"], width=56)
        spd_label.pack(side="left")
        _ToolTip(spd_label, "Velocidade de reproducao.\n1.00x = normal.\n2.00x = rapido (agudo).\n0.50x = lento (grave).")
        spd_label.bind("<Enter>", lambda e: spd_label.configure(font=("Segoe UI", 10, "bold"), text_color=color))
        spd_label.bind("<Leave>", lambda e: spd_label.configure(font=("Segoe UI", 9, "bold"), text_color=C["text"]))
        spd_lbl = ctk.CTkLabel(spd_f, text=f"{speed/100:.2f}x", font=("Consolas", 9, "bold"),
                                text_color=C["text"], width=50)

        def _spd_change(delta, lbl=spd_lbl, itm=item):
            cur = int(itm.params.get("speed", 100))
            new = max(25, min(400, cur + delta))
            itm.params["speed"] = str(new)
            lbl.configure(text=f"{new/100:.2f}x")
            if self._layer_previews.get(itm.id, False):
                layer_info = self._layer_canvases.get(itm.id)
                if layer_info:
                    import sounddevice as sd
                    sd.stop()
                    self._layer_previews[itm.id] = False
                    layer_info["canvas"].delete("playhead")
                    self._start_single_item(itm, layer_info["btn"], layer_info["color"],
                                            layer_info["canvas"], layer_info["time_lbl"])

        ctk.CTkButton(spd_f, text="\u25c0", width=20, height=18, font=("Segoe UI", 9, "bold"),
                      fg_color="#1a1a2a", text_color=C["text"], hover_color=color,
                      command=lambda: _spd_change(-25)).pack(side="left", padx=2)
        spd_lbl.pack(side="left", padx=4)
        ctk.CTkButton(spd_f, text="\u25b6", width=20, height=18, font=("Segoe UI", 9, "bold"),
                      fg_color="#1a1a2a", text_color=C["text"], hover_color=color,
                      command=lambda: _spd_change(25)).pack(side="left", padx=2)

        # Guardar refs para salvar
        if not hasattr(self, '_layer_sliders'):
            self._layer_sliders = {}
        self._layer_sliders[item.id] = {
            "volume": vol_slider, "pan": pan_slider,
            "fade_in": fi_s, "fade_out": fo_s
        }

    def _draw_layer_waveform(self, canvas, item, color):
        """Desenha waveform no canvas do layer, usando tamanho real."""
        from pathlib import Path
        try:
            canvas.delete("waveform")
            canvas.delete("grid")
        except Exception:
            return
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            return
        mid = h // 2

        # Fundo
        canvas.create_rectangle(0, 0, w, h, fill="#040810", outline="", tags="grid")
        # Linha central
        canvas.create_line(0, mid, w, mid, fill="#1a2a3a", width=1, tags="grid")
        # Grid vertical
        step = max(20, w // 8)
        for gx in range(step, w, step):
            canvas.create_line(gx, 0, gx, h, fill="#0a1218", width=1, tags="grid")

        if not item.file_path or not Path(item.file_path).exists():
            canvas.create_text(w // 2, mid, text="(sem audio)", fill="#4a4a6a",
                               font=("Segoe UI", 8), tags="waveform")
            return
        try:
            from makevid.core.audio_utils import read_audio_mono
            import numpy as np
            audio, sr = read_audio_mono(item.file_path)
            if len(audio) < 10:
                return
            block_size = max(1, len(audio) // w)
            amp = mid - 3
            dark_color = self._darken_color(color, 0.4)
            for i in range(min(w, len(audio) // block_size)):
                start = i * block_size
                end = min(start + block_size, len(audio))
                block = audio[start:end]
                if len(block) > 0:
                    mn = float(block.min())
                    mx = float(block.max())
                    y1 = mid - int(mx * amp)
                    y2 = mid - int(mn * amp)
                    if y1 == y2:
                        y2 = y1 + 1
                    canvas.create_line(i, y1, i, y2, fill=dark_color, width=1, tags="waveform")
                    peak = max(abs(mx), abs(mn))
                    if peak > 0.3:
                        canvas.create_line(i, y1, i, y1 + 1, fill=color, width=1, tags="waveform")
                        canvas.create_line(i, y2 - 1, i, y2, fill=color, width=1, tags="waveform")
            # Bordas coloridas
            canvas.create_line(0, 0, w, 0, fill=color, width=1, tags="waveform")
            canvas.create_line(0, h - 1, w, h - 1, fill=color, width=1, tags="waveform")
        except Exception as e:
            canvas.create_text(w // 2, mid, text=f"Erro: {str(e)[:30]}",
                               fill="#ff4444", font=("Segoe UI", 7), tags="waveform")

    def _play_single_item(self, item, btn, color, canvas=None, time_lbl=None):
        """Play/Stop de um item individual com playhead animado."""
        item_id = item.id
        if self._layer_previews.get(item_id, False):
            self._stop_single_item(item_id, btn)
        else:
            # Parar qualquer outro que esteja tocando
            for other_id in list(self._layer_previews.keys()):
                if self._layer_previews.get(other_id, False):
                    info = self._layer_canvases.get(other_id)
                    if info:
                        self._layer_previews[other_id] = False
                        info["canvas"].delete("playhead")
                        info["btn"].configure(text="\u25b6 Play", fg_color=info["color"], text_color="#0a0a0f")
            self._start_single_item(item, btn, color, canvas, time_lbl)

    def _start_single_item(self, item, btn, color, canvas=None, time_lbl=None):
        """Inicia preview de um unico item com animacao de playhead."""
        from pathlib import Path
        if not item.file_path or not Path(item.file_path).exists():
            if time_lbl:
                time_lbl.configure(text="Arquivo nao encontrado", text_color="#ff4444")
            return
        try:
            import sounddevice as sd
            import numpy as np
            import soundfile as sf
            import time as _time

            data, sr = sf.read(item.file_path, dtype="float32")
            if len(data.shape) == 1:
                data = np.column_stack([data, data])

            # Aplicar volume
            vol = int(item.params.get("volume", 80)) / 100.0
            data *= vol

            # Aplicar pan
            pan = int(item.params.get("pan", 0)) / 100.0
            if pan != 0:
                data[:, 0] *= max(0, 1.0 - pan)
                data[:, 1] *= max(0, 1.0 + pan)

            # Fade in/out
            fade_in = int(item.params.get("fade_in", 0)) / 100.0
            if fade_in > 0:
                n = int(len(data) * fade_in)
                if n > 0:
                    data[:n] *= np.linspace(0, 1, n).reshape(-1, 1)
            fade_out = int(item.params.get("fade_out", 0)) / 100.0
            if fade_out > 0:
                n = int(len(data) * fade_out)
                if n > 0:
                    data[-n:] *= np.linspace(1, 0, n).reshape(-1, 1)

            # Reverb (eco)
            reverb = int(item.params.get("reverb", 0)) / 100.0
            if reverb > 0:
                reverb_len = int(0.4 * sr * (0.5 + reverb))
                impulse = np.exp(-np.linspace(0, 6, reverb_len))
                impulse = impulse / impulse.sum()
                wet_l = np.convolve(data[:, 0], impulse)[:len(data)]
                wet_r = np.convolve(data[:, 1], impulse)[:len(data)]
                data[:, 0] = data[:, 0] * (1 - reverb) + wet_l * reverb
                data[:, 1] = data[:, 1] * (1 - reverb) + wet_r * reverb

            # Room (distancia - atenuacao + pre-delay)
            room = int(item.params.get("room", 0)) / 100.0
            if room > 0:
                # Pre-delay (simula distancia)
                delay_samples = int(room * 0.05 * sr)
                if delay_samples > 0 and delay_samples < len(data):
                    delayed = np.zeros_like(data)
                    delayed[delay_samples:] = data[:-delay_samples]
                    data = data * (1 - room * 0.5) + delayed * room * 0.5
                # Atenuacao de altas frequencias com distancia
                data *= (1.0 - room * 0.3)

            # Lowpass / Tone
            lowpass = int(item.params.get("lowpass", 100)) / 100.0
            if lowpass < 0.95:
                # Filtro simples de media movel
                kernel_size = int((1.0 - lowpass) * 40) + 1
                kernel = np.ones(kernel_size) / kernel_size
                data[:, 0] = np.convolve(data[:, 0], kernel, mode='same')
                data[:, 1] = np.convolve(data[:, 1], kernel, mode='same')

            # Loop: repetir audio se habilitado
            loop_enabled = self._is_loop_enabled()
            # Speed via samplerate
            speed = int(item.params.get("speed", 100)) / 100.0
            play_sr = int(sr * speed) if speed > 0 else sr
            original_duration = len(data) / play_sr
            if loop_enabled:
                repeats = max(2, int(60.0 / max(0.1, original_duration)))
                data = np.tile(data, (repeats, 1))

            audio_data = np.ascontiguousarray(np.clip(data, -1, 1).astype(np.float32))

            # Guardar sr usado para o playhead sincronizar
            self._play_sr = play_sr
            self._play_base_sr = sr

            sd.stop()
            sd.play(audio_data, samplerate=play_sr)

            self._layer_previews[item.id] = True
            btn.configure(text="\u25a0 Stop", fg_color="#ff4444", text_color="#ffffff")

            # Iniciar animacao do playhead (usa duracao original pra loop fazer wrap)
            if canvas:
                self._start_playhead_animation(item.id, canvas, time_lbl,
                                               original_duration, _time.time(), color,
                                               loop=loop_enabled)

        except Exception as e:
            if time_lbl:
                time_lbl.configure(text=f"Erro: {str(e)[:40]}", text_color="#ff4444")
            import traceback
            traceback.print_exc()

    def _is_loop_enabled(self):
        """Verifica se loop esta habilitado no editor atual."""
        if self._voice_loop and self._voice_loop.get():
            return True
        if self._sfx_loop and self._sfx_loop.get():
            return True
        if self._music_loop and self._music_loop.get():
            return True
        if self._audio_loop and self._audio_loop.get():
            return True
        return False

    def _start_playhead_animation(self, item_id, canvas, time_lbl, duration, start_time, color, loop=False):
        """Anima playhead sincronizado com o audio (1:1 com tempo real)."""
        if not canvas or not self._layer_previews.get(item_id, False):
            return
        try:
            if not canvas.winfo_exists():
                return
        except Exception:
            return

        import time as _time
        elapsed = _time.time() - start_time

        if not loop and elapsed >= duration:
            self._layer_previews[item_id] = False
            canvas.delete("playhead")
            if time_lbl:
                time_lbl.configure(text=f"{duration:.1f}s / {duration:.1f}s")
            layer_info = self._layer_canvases.get(item_id)
            if layer_info:
                layer_info["btn"].configure(text="\u25b6 Play", fg_color=layer_info["color"], text_color="#0a0a0f")
            return

        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10:
            canvas.after(50, lambda: self._start_playhead_animation(
                item_id, canvas, time_lbl, duration, start_time, color, loop))
            return

        display_elapsed = elapsed % duration if loop else elapsed
        ratio = display_elapsed / duration
        px = int(w * ratio)

        canvas.delete("playhead")
        canvas.create_line(px - 1, 0, px - 1, h, fill="#550000", width=1, tags="playhead")
        canvas.create_line(px + 1, 0, px + 1, h, fill="#550000", width=1, tags="playhead")
        canvas.create_line(px, 0, px, h, fill="#ff2222", width=2, tags="playhead")
        canvas.create_polygon(px - 4, 0, px + 4, 0, px, 5,
                              fill="#ff2222", outline="", tags="playhead")

        if time_lbl:
            time_lbl.configure(text=f"{display_elapsed:.1f}s / {duration:.1f}s")

        canvas.after(33, lambda: self._start_playhead_animation(
            item_id, canvas, time_lbl, duration, start_time, color, loop))

    def _seek_layer(self, event, item, canvas, color, time_lbl):
        """Click na waveform para iniciar play a partir dessa posicao."""
        from pathlib import Path
        if not item.file_path or not Path(item.file_path).exists():
            return
        w = canvas.winfo_width() or 240
        ratio = max(0.0, min(1.0, event.x / w))

        try:
            import sounddevice as sd
            import numpy as np
            import soundfile as sf
            import time as _time

            data, sr = sf.read(item.file_path, dtype="float32")
            if len(data.shape) == 1:
                data = np.column_stack([data, data])

            vol = int(item.params.get("volume", 80)) / 100.0
            data *= vol

            duration = len(data) / sr
            start_sample = int(ratio * len(data))
            audio_chunk = np.ascontiguousarray(np.clip(data[start_sample:], -1, 1).astype(np.float32))

            # Parar outros
            for other_id in list(self._layer_previews.keys()):
                if self._layer_previews.get(other_id, False):
                    info = self._layer_canvases.get(other_id)
                    if info:
                        self._layer_previews[other_id] = False
                        info["canvas"].delete("playhead")
                        info["btn"].configure(text="\u25b6 Play", fg_color=info["color"], text_color="#0a0a0f")

            sd.stop()
            sd.play(audio_chunk, samplerate=sr)

            self._layer_previews[item.id] = True
            offset_time = ratio * duration
            fake_start = _time.time() - offset_time

            # Atualizar botao
            layer_info = self._layer_canvases.get(item.id)
            if layer_info:
                layer_info["btn"].configure(text="\u25a0 Stop", fg_color="#ff4444", text_color="#ffffff")

            self._start_playhead_animation(item.id, canvas, time_lbl, duration, fake_start, color, loop=False)
        except Exception as e:
            if time_lbl:
                time_lbl.configure(text=f"Erro: {str(e)[:40]}", text_color="#ff4444")
            import traceback
            traceback.print_exc()

    def _stop_single_item(self, item_id, btn):
        """Para preview de item e limpa playhead."""
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self._layer_previews[item_id] = False
        if btn:
            btn.configure(text="\u25b6 Play", fg_color=self._current_color, text_color="#0a0a0f")
        layer_info = getattr(self, '_layer_canvases', {}).get(item_id)
        if layer_info and layer_info["canvas"]:
            layer_info["canvas"].delete("playhead")

    def _stop_all_previews(self):
        """Para todos os previews e limpa playheads."""
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        for item_id, info in getattr(self, '_layer_canvases', {}).items():
            try:
                info["canvas"].delete("playhead")
            except Exception:
                pass
        self._layer_previews = {}
        self._layer_canvases = {}

    def _toggle_layer(self, content, btn, var):
        if var.get():
            content.pack_forget()
            btn.configure(text="\u25b6")
            var.set(False)
        else:
            content.pack(fill="x", padx=4, pady=(2, 4))
            btn.configure(text="\u25bc")
            var.set(True)

    def _close_editor(self):
        self._stop_all_previews()
        self.fx_panel.hide()

    def _inline_rename(self, item, lbl, header, color):
        """Substitui o label do nome por um entry inline para renomear."""
        lbl.pack_forget()
        entry = ctk.CTkEntry(header, width=100, height=20, font=("Segoe UI", 9, "bold"),
                             fg_color="#ffffff", text_color="#0a0a0f", border_width=1,
                             border_color=color)
        entry.pack(side="left", padx=4)
        entry.insert(0, item.name)
        entry.select_range(0, "end")

        def _focus():
            entry.focus_force()
        entry.after(50, _focus)

        def confirm(e=None):
            new_name = entry.get().strip()
            if new_name:
                item.name = new_name
                from makevid.config import PROJECTS_DIR
                self.fx_panel.timeline.project.save(PROJECTS_DIR)
                self.fx_panel.timeline.draw()
            entry.destroy()
            lbl.configure(text=f"\u266b {item.name[:20]}")
            lbl.pack(side="left", padx=4)

        entry.bind("<Return>", confirm)
        entry.bind("<FocusOut>", confirm)
        entry.bind("<Escape>", lambda e: (entry.destroy(), lbl.pack(side="left", padx=4)))

    def _duplicate_layer(self, item):
        """Duplica um layer com o mesmo audio."""
        from makevid.config import PROJECTS_DIR
        tl = self.fx_panel.timeline
        tl.project.add_track_item(
            name=item.name, track=item.track,
            start_time=item.start_time, duration=item.duration,
            file_path=item.file_path, params=dict(item.params),
            clip_index=item.clip_index)
        tl.project.save(PROJECTS_DIR)
        tl.draw()
        self.fx_panel.hide()
        self.fx_panel.show_track_editor(item)

    def _delete_layer(self, item):
        """Remove um layer (track_item) e recarrega o editor."""
        from makevid.config import PROJECTS_DIR
        import sounddevice as sd
        sd.stop()
        tl = self.fx_panel.timeline
        tl.project.remove_track_item(item.id)
        tl.project.save(PROJECTS_DIR)
        tl.draw()
        # Reabrir editor se ainda tem items na track
        remaining = tl.project.get_track_items(item.track)
        if remaining:
            self.fx_panel.hide()
            self.fx_panel.show_track_editor(remaining[0])
        else:
            self.fx_panel.hide()

    def _cut_item(self, item):
        """Ativa modo de recorte inline na waveform do layer."""
        layer_info = self._layer_canvases.get(item.id)
        if not layer_info:
            # Fallback: modo antigo na timeline
            tl = self.fx_panel.timeline
            tl.enter_audio_split_mode(item.track)
            self.fx_panel.hide()
            return

        canvas = layer_info["canvas"]
        color = layer_info["color"]
        self._cut_state = {"item": item, "canvas": canvas, "color": color,
                           "point_a": None, "point_b": None, "preview_x": None}
        canvas.configure(cursor="crosshair")
        canvas.bind("<Button-1>", self._cut_click)
        canvas.bind("<Motion>", self._cut_motion)
        # ESC cancela o recorte
        canvas.focus_set()
        canvas.bind("<Escape>", self._cut_cancel)

    def _cut_cancel(self, event=None):
        """Cancela o modo de recorte."""
        cs = self._cut_state
        if not cs:
            return
        canvas = cs["canvas"]
        item = cs["item"]
        canvas.delete("cut_preview")
        canvas.configure(cursor="hand2")
        # Restaurar binds originais
        layer_info = self._layer_canvases.get(item.id)
        if layer_info:
            def _make_seek_cmd(it, cv, cl, tl):
                return lambda e: self._seek_layer(e, it, cv, cl, tl)
            canvas.bind("<Button-1>", _make_seek_cmd(item, canvas, cs["color"], layer_info["time_lbl"]))
        else:
            canvas.bind("<Button-1>", lambda e: None)
        canvas.bind("<Motion>", lambda e: None)
        canvas.bind("<Escape>", lambda e: None)
        self._cut_state = None

    def _cut_click(self, event):
        """Click na waveform durante modo de corte."""
        cs = self._cut_state
        if not cs:
            return
        canvas = cs["canvas"]
        w = canvas.winfo_width() or 200
        ratio = max(0.0, min(1.0, event.x / w))
        # Snap nas bordas (5% de margem)
        if ratio < 0.03:
            ratio = 0.0
        elif ratio > 0.97:
            ratio = 1.0

        if cs["point_a"] is None:
            # Primeiro click
            cs["point_a"] = ratio
        else:
            # Segundo click - aplicar recorte
            cs["point_b"] = ratio
            self._cut_apply()

    def _cut_motion(self, event):
        """Preview da area de corte durante movimento do mouse."""
        cs = self._cut_state
        if not cs or cs["point_a"] is None:
            return
        canvas = cs["canvas"]
        w = canvas.winfo_width() or 200
        h = canvas.winfo_height() or 44
        ratio = max(0.0, min(1.0, event.x / w))
        # Snap nas bordas
        if ratio < 0.03:
            ratio = 0.0
        elif ratio > 0.97:
            ratio = 1.0
        cs["preview_x"] = ratio

        # Redesenhar preview
        canvas.delete("cut_preview")
        a = cs["point_a"]
        b = ratio
        x_a = int(a * w)
        x_b = int(b * w)
        if x_a > x_b:
            x_a, x_b = x_b, x_a

        # Area vermelha opaca (sera descartada)
        canvas.create_rectangle(x_a, 0, x_b, h, fill="#aa0000", outline="",
                                tags="cut_preview")
        # Linhas de corte nas bordas
        canvas.create_line(x_a, 0, x_a, h, fill="#ff4444", width=2, tags="cut_preview")
        canvas.create_line(x_b, 0, x_b, h, fill="#ff4444", width=2, tags="cut_preview")
        # Snap indicator nas bordas
        if ratio < 0.03 or ratio > 0.97:
            snap_x = 0 if ratio < 0.03 else w
            canvas.create_rectangle(snap_x - 3, 0, snap_x + 3, h, fill="#00ffee",
                                    outline="", tags="cut_preview")

    def _cut_apply(self):
        """Aplica o recorte: descarta a area selecionada, mantem o resto."""
        cs = self._cut_state
        if not cs:
            return
        item = cs["item"]
        a = cs["point_a"]
        b = cs["point_b"]
        canvas = cs["canvas"]

        # Limpar estado
        canvas.delete("cut_preview")
        canvas.configure(cursor="hand2")
        # Restaurar binds originais
        layer_info = self._layer_canvases.get(item.id)
        if layer_info:
            def _make_seek_cmd(it, cv, cl, tl):
                return lambda e: self._seek_layer(e, it, cv, cl, tl)
            canvas.bind("<Button-1>", _make_seek_cmd(item, canvas, cs["color"], layer_info["time_lbl"]))
        else:
            canvas.bind("<Button-1>", lambda e: None)
        canvas.bind("<Motion>", lambda e: None)
        self._cut_state = None

        if a is None or b is None:
            return
        if a > b:
            a, b = b, a
        if abs(b - a) < 0.02:
            return

        # Recortar o arquivo de audio - remover a selecao, manter o resto
        from pathlib import Path
        if not item.file_path or not Path(item.file_path).exists():
            return

        try:
            import soundfile as sf
            import numpy as np

            data, sr = sf.read(item.file_path, dtype="float32")
            total_samples = len(data)
            cut_start = int(a * total_samples)
            cut_end = int(b * total_samples)

            # Manter parte antes + parte depois da selecao
            if len(data.shape) == 1:
                kept = np.concatenate([data[:cut_start], data[cut_end:]])
            else:
                kept = np.concatenate([data[:cut_start], data[cut_end:]], axis=0)

            if len(kept) < 100:
                return

            # Salvar por cima
            sf.write(item.file_path, kept, sr)

            # Atualizar duration
            item.duration = len(kept) / sr

            from makevid.config import PROJECTS_DIR
            tl = self.fx_panel.timeline
            tl.project.save(PROJECTS_DIR)
            tl.draw()

            # Reabrir editor
            self.fx_panel.hide()
            self.fx_panel.show_track_editor(item)
        except Exception as e:
            print(f"[TrackEditor] Cut error: {e}")
            import traceback
            traceback.print_exc()

    def _rename_item(self, item, scroll, color):
        """Abre campo de texto para renomear o bloco, logo abaixo do botao."""
        from makevid.config import PROJECTS_DIR

        # Remover rename anterior se existir
        if hasattr(self, '_rename_frame') and self._rename_frame:
            try:
                self._rename_frame.destroy()
            except Exception:
                pass

        # Encontrar o botao RENOMEAR e inserir depois dele
        # Usar pack com after= referenciando o botao
        rename_f = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4)
        # Posicionar no indice correto: logo apos o botao renomear
        # Pack all children, find RENOMEAR button, insert after it
        children = scroll.winfo_children()
        rename_btn = None
        for child in children:
            if hasattr(child, 'cget'):
                try:
                    if 'RENOMEAR' in child.cget('text'):
                        rename_btn = child
                except Exception:
                    pass
        if rename_btn:
            rename_f.pack(fill="x", padx=4, pady=(2, 4), after=rename_btn)
        else:
            rename_f.pack(fill="x", padx=4, pady=(2, 4))

        self._rename_frame = rename_f

        # Nome que aparece na timeline (block_name ou nome do primeiro do grupo)
        group = self._get_overlapping_items(item, item.track)
        rep = sorted(group, key=lambda i: i.start_time)[0] if group else item
        rep_name = rep.params.get("block_name", rep.name)

        entry = ctk.CTkEntry(rename_f, placeholder_text=rep_name,
                             fg_color=C["input"], border_color=color,
                             border_width=1, text_color=C["text"],
                             font=("Segoe UI", 10), height=26)
        entry.pack(side="left", fill="x", expand=True, padx=(4, 2), pady=4)
        entry.insert(0, rep_name)
        entry.focus_set()
        entry.select_range(0, "end")

        def confirm(event=None):
            new_name = entry.get().strip()
            if new_name:
                tl = self.fx_panel.timeline
                # Salvar nome do bloco como param separado (nao altera nome dos layers)
                group = self._get_overlapping_items(item, item.track)
                if group:
                    sorted_group = sorted(group, key=lambda i: i.start_time)
                    sorted_group[0].params["block_name"] = new_name
                else:
                    item.params["block_name"] = new_name
                tl.project.save(PROJECTS_DIR)
                tl.draw()
                self.fx_panel.hide()
                self.fx_panel.show_track_editor(item)

        entry.bind("<Return>", confirm)
        ctk.CTkButton(rename_f, text="OK", width=30, height=24,
                      font=("Segoe UI", 9, "bold"), fg_color=color,
                      text_color="#0a0a0f", command=confirm).pack(side="right", padx=(2, 4), pady=4)

    # ============================================================
    # VOICE EDITOR - layers por item na track
    # ============================================================

    def _build_voice_editor(self, frame, item):
        color = "#ff9944"
        self._current_color = color
        self._build_header(frame, "\U0001f3a4 VOZ", color, item)

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent",
                                        scrollbar_button_color=color,
                                        scrollbar_button_hover_color="#ffbb66")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Info do item clicado
        ctk.CTkLabel(scroll, text=f"{item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w", padx=4, pady=(0, 4))

        # Listar apenas items que se sobrepoem ao bloco clicado
        self._layer_sliders = {}
        all_items = sorted(self._get_overlapping_items(item, "voice"),
                           key=lambda i: i.start_time)

        if all_items:
            ctk.CTkLabel(scroll, text=f"LAYERS ({len(all_items)})", font=("Segoe UI", 9, "bold"),
                         text_color=color).pack(anchor="w", padx=4, pady=(4, 2))
            for it in all_items:
                self._build_layer_item(scroll, it, color)
        else:
            ctk.CTkLabel(scroll, text="Nenhum item na track", text_color=C["text3"],
                         font=("Segoe UI", 9)).pack(anchor="w", padx=4, pady=4)

        # Separador + controles globais
        ctk.CTkFrame(scroll, height=1, fg_color=color).pack(fill="x", padx=4, pady=(8, 4))

        # Loop - DESLIGADO por padrao
        self._voice_loop = ctk.BooleanVar(value=False)
        loop_cb = ctk.CTkCheckBox(scroll, text="Loop", variable=self._voice_loop,
                        fg_color=color, text_color=C["text"], font=("Segoe UI", 9),
                        hover_color="#2a1a0a", height=20)
        loop_cb.pack(anchor="w", padx=4, pady=(2, 4))
        from makevid.ui.menus import _ToolTip
        _ToolTip(loop_cb, "Repete o audio em loop continuo.\nO playhead faz wrap-around na waveform.")

        # Play All (conjunto)
        self._play_all_btn = ctk.CTkButton(scroll, text="\u25b6 PLAY CONJUNTO", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=color, border_width=1,
                      text_color=color, hover_color="#2a1a0a",
                      command=lambda: self._toggle_play_all("voice", color))
        self._play_all_btn.pack(fill="x", padx=4, pady=(2, 2))

        # Recortar
        ctk.CTkButton(scroll, text="\u2702 RECORTAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._cut_item(item)).pack(fill="x", padx=4, pady=(2, 2))

        # Renomear
        ctk.CTkButton(scroll, text="\u270f RENOMEAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._rename_item(item, scroll, color)).pack(fill="x", padx=4, pady=(2, 2))

        # Salvar
        ctk.CTkButton(scroll, text="SALVAR", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=color, text_color="#0a0a0f", hover_color="#ffbb66",
                      command=lambda: self._save_all_params("voice")).pack(fill="x", padx=4, pady=(2, 4))

    # ============================================================
    # SFX EDITOR - layers por item na track
    # ============================================================

    def _build_sfx_editor(self, frame, item):
        color = "#44cc88"
        self._current_color = color
        self._build_header(frame, "\U0001f50a SFX", color, item)

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent",
                                        scrollbar_button_color=color,
                                        scrollbar_button_hover_color="#66eebb")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Info do item clicado
        ctk.CTkLabel(scroll, text=f"{item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w", padx=4, pady=(0, 4))

        # Listar apenas items que se sobrepoem ao bloco clicado
        self._layer_sliders = {}
        all_items = sorted(self._get_overlapping_items(item, "sfx"),
                           key=lambda i: i.start_time)

        if all_items:
            ctk.CTkLabel(scroll, text=f"LAYERS ({len(all_items)})", font=("Segoe UI", 9, "bold"),
                         text_color=color).pack(anchor="w", padx=4, pady=(4, 2))
            for it in all_items:
                self._build_layer_item(scroll, it, color)
        else:
            ctk.CTkLabel(scroll, text="Nenhum item na track", text_color=C["text3"],
                         font=("Segoe UI", 9)).pack(anchor="w", padx=4, pady=4)

        # Separador + controles globais
        ctk.CTkFrame(scroll, height=1, fg_color=C["gold"]).pack(fill="x", padx=4, pady=(8, 4))

        # Loop - DESLIGADO por padrao
        self._sfx_loop = ctk.BooleanVar(value=False)
        loop_cb = ctk.CTkCheckBox(scroll, text="Loop", variable=self._sfx_loop,
                        fg_color=color, text_color=C["text"], font=("Segoe UI", 9),
                        hover_color="#2a4a3a", height=20)
        loop_cb.pack(anchor="w", padx=4, pady=(2, 4))
        from makevid.ui.menus import _ToolTip
        _ToolTip(loop_cb, "Repete o audio em loop continuo.\nO playhead faz wrap-around na waveform.")

        # Play All (conjunto)
        self._play_all_btn = ctk.CTkButton(scroll, text="\u25b6 PLAY CONJUNTO", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=color, border_width=1,
                      text_color=color, hover_color="#0a2a1a",
                      command=lambda: self._toggle_play_all("sfx", color))
        self._play_all_btn.pack(fill="x", padx=4, pady=(2, 2))

        # Recortar
        ctk.CTkButton(scroll, text="\u2702 RECORTAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._cut_item(item)).pack(fill="x", padx=4, pady=(2, 2))

        # Renomear
        ctk.CTkButton(scroll, text="\u270f RENOMEAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._rename_item(item, scroll, color)).pack(fill="x", padx=4, pady=(2, 2))

        # Salvar
        ctk.CTkButton(scroll, text="SALVAR", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=color, text_color="#0a0a0f", hover_color="#66eebb",
                      command=lambda: self._save_all_params("sfx")).pack(fill="x", padx=4, pady=(2, 4))

    # ============================================================
    # MUSIC EDITOR - layers por item na track
    # ============================================================

    def _build_music_editor(self, frame, item):
        color = "#cc44aa"
        self._current_color = color
        self._build_header(frame, "\U0001f3b5 MUSICA", color, item)

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent",
                                        scrollbar_button_color=color,
                                        scrollbar_button_hover_color="#ee66cc")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Info do item clicado
        ctk.CTkLabel(scroll, text=f"{item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w", padx=4, pady=(0, 4))

        # Listar apenas items que se sobrepoem ao bloco clicado
        self._layer_sliders = {}
        all_items = sorted(self._get_overlapping_items(item, "music"),
                           key=lambda i: i.start_time)

        if all_items:
            ctk.CTkLabel(scroll, text=f"LAYERS ({len(all_items)})", font=("Segoe UI", 9, "bold"),
                         text_color=color).pack(anchor="w", padx=4, pady=(4, 2))
            for it in all_items:
                self._build_layer_item(scroll, it, color)
        else:
            ctk.CTkLabel(scroll, text="Nenhum item na track", text_color=C["text3"],
                         font=("Segoe UI", 9)).pack(anchor="w", padx=4, pady=4)

        # Separador + controles globais
        ctk.CTkFrame(scroll, height=1, fg_color=color).pack(fill="x", padx=4, pady=(8, 4))

        # Ducking global
        from makevid.ui.menus import _ToolTip
        self._music_ducking = self._compact_slider(scroll, "Ducking", 0, 100,
                                                    int(item.params.get("ducking", 75)), "%", "#8855bb",
                                                    tooltip="Reducao de volume da musica\nquando ha voz tocando.\n0% = sem reducao, 100% = mudo.")

        # Loop - DESLIGADO por padrao
        self._music_loop = ctk.BooleanVar(value=False)
        loop_cb = ctk.CTkCheckBox(scroll, text="Loop", variable=self._music_loop,
                        fg_color=color, text_color=C["text"], font=("Segoe UI", 9),
                        hover_color="#4a1a3a", height=20)
        loop_cb.pack(anchor="w", padx=4, pady=(4, 2))
        _ToolTip(loop_cb, "Repete o audio em loop continuo.\nO playhead faz wrap-around na waveform.")

        # Play All (conjunto)
        self._play_all_btn = ctk.CTkButton(scroll, text="\u25b6 PLAY CONJUNTO", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=color, border_width=1,
                      text_color=color, hover_color="#2a0a1a",
                      command=lambda: self._toggle_play_all("music", color))
        self._play_all_btn.pack(fill="x", padx=4, pady=(2, 2))

        # Recortar
        ctk.CTkButton(scroll, text="\u2702 RECORTAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._cut_item(item)).pack(fill="x", padx=4, pady=(2, 2))

        # Renomear
        ctk.CTkButton(scroll, text="\u270f RENOMEAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._rename_item(item, scroll, color)).pack(fill="x", padx=4, pady=(2, 2))

        # Salvar
        ctk.CTkButton(scroll, text="SALVAR", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=color, text_color="#0a0a0f", hover_color="#ee66cc",
                      command=lambda: self._save_all_params("music")).pack(fill="x", padx=4, pady=(2, 4))

    # ============================================================
    # AUDIO EDITOR - layers por item na track
    # ============================================================

    def _build_audio_editor(self, frame, item):
        color = "#0ac8b9"
        self._current_color = color
        self._build_header(frame, "\U0001f3a7 AUDIO", color, item)

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent",
                                        scrollbar_button_color=color,
                                        scrollbar_button_hover_color="#00ffee")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Info do item clicado
        ctk.CTkLabel(scroll, text=f"{item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w", padx=4, pady=(0, 4))

        # Listar apenas items que se sobrepoem ao bloco clicado
        self._layer_sliders = {}
        all_items = sorted(self._get_overlapping_items(item, "audio"),
                           key=lambda i: i.start_time)

        if all_items:
            ctk.CTkLabel(scroll, text=f"LAYERS ({len(all_items)})", font=("Segoe UI", 9, "bold"),
                         text_color=color).pack(anchor="w", padx=4, pady=(4, 2))
            for it in all_items:
                self._build_layer_item(scroll, it, color)
        else:
            ctk.CTkLabel(scroll, text="Nenhum item na track", text_color=C["text3"],
                         font=("Segoe UI", 9)).pack(anchor="w", padx=4, pady=4)

        # Separador + controles globais
        ctk.CTkFrame(scroll, height=1, fg_color=color).pack(fill="x", padx=4, pady=(8, 4))

        # Loop - DESLIGADO por padrao
        self._audio_loop = ctk.BooleanVar(value=False)
        loop_cb = ctk.CTkCheckBox(scroll, text="Loop", variable=self._audio_loop,
                        fg_color=color, text_color=C["text"], font=("Segoe UI", 9),
                        hover_color="#0a2a2a", height=20)
        loop_cb.pack(anchor="w", padx=4, pady=(2, 4))
        from makevid.ui.menus import _ToolTip
        _ToolTip(loop_cb, "Repete o audio em loop continuo.\nO playhead faz wrap-around na waveform.")

        # Play All (conjunto)
        self._play_all_btn = ctk.CTkButton(scroll, text="\u25b6 PLAY CONJUNTO", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=color, border_width=1,
                      text_color=color, hover_color="#0a2a2a",
                      command=lambda: self._toggle_play_all("audio", color))
        self._play_all_btn.pack(fill="x", padx=4, pady=(2, 2))

        # Recortar
        ctk.CTkButton(scroll, text="\u2702 RECORTAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._cut_item(item)).pack(fill="x", padx=4, pady=(2, 2))

        # Renomear
        ctk.CTkButton(scroll, text="\u270f RENOMEAR", height=24, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["text3"], border_width=1,
                      text_color=C["text2"], hover_color="#1a1a2a",
                      command=lambda: self._rename_item(item, scroll, color)).pack(fill="x", padx=4, pady=(2, 2))

        # Salvar
        ctk.CTkButton(scroll, text="SALVAR", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color=color, text_color="#0a0a0f", hover_color="#00ffee",
                      command=lambda: self._save_all_params("audio")).pack(fill="x", padx=4, pady=(2, 4))

    # ============================================================
    # ACTIONS
    # ============================================================

    def _toggle_play_all(self, track, color):
        """Toggle play/pause do conjunto."""
        if getattr(self, '_play_all_playing', False):
            # Parar
            import sounddevice as sd
            sd.stop()
            self._play_all_playing = False
            self._on_play_all_ended()
        else:
            # Tocar
            self._play_all_playing = True
            self._play_all_btn.configure(
                text="\u25a0 PAUSA", fg_color=color,
                text_color="#0a0a0f")
            self._play_all_items(track)

    def _play_all_items(self, track):
        """Reproduz todos os items da track mixados juntos com playheads individuais."""
        import threading
        import time as _time

        # Usar apenas items do grupo atual (bloco aberto no editor)
        items = sorted(self._get_overlapping_items(self._current_item, track),
                       key=lambda i: i.start_time)
        if not items:
            return

        # Calcular offset base (menor start_time do grupo)
        base_start = min(i.start_time for i in items)

        def run():
            try:
                import sounddevice as sd
                import numpy as np
                import soundfile as sf
                from pathlib import Path

                end_time = max(i.start_time + i.duration for i in items)
                total_dur = end_time - base_start
                sr = 44100
                total_samples = int(total_dur * sr)
                if total_samples <= 0:
                    return
                mix = np.zeros((total_samples, 2), dtype=np.float32)

                for item in items:
                    if not item.file_path or not Path(item.file_path).exists():
                        continue
                    data, item_sr = sf.read(item.file_path, dtype="float32")
                    if len(data.shape) == 1:
                        data = np.column_stack([data, data])
                    if item_sr != sr:
                        target_len = int(len(data) * sr / item_sr)
                        if target_len <= 0:
                            continue
                        data = np.column_stack([
                            np.interp(np.linspace(0, len(data)-1, target_len), np.arange(len(data)), data[:, 0]),
                            np.interp(np.linspace(0, len(data)-1, target_len), np.arange(len(data)), data[:, 1]),
                        ])
                    vol = int(item.params.get("volume", 80)) / 100.0
                    data *= vol
                    pan = int(item.params.get("pan", 0)) / 100.0
                    if pan != 0:
                        data[:, 0] *= max(0, 1.0 - pan)
                        data[:, 1] *= max(0, 1.0 + pan)
                    start_sample = int((item.start_time - base_start) * sr)
                    end_sample = min(start_sample + len(data), total_samples)
                    chunk_len = end_sample - start_sample
                    if chunk_len > 0:
                        mix[start_sample:start_sample + chunk_len] += data[:chunk_len]

                audio_out = np.ascontiguousarray(np.clip(mix, -1, 1).astype(np.float32))
                sd.stop()
                sd.play(audio_out, samplerate=sr)
            except Exception as e:
                print(f"[TrackEditor] Play all error: {e}")
                self._play_all_playing = False

        threading.Thread(target=run, daemon=True).start()

        # Iniciar playheads individuais com offset correto
        play_start = _time.time()
        for item in items:
            layer_info = self._layer_canvases.get(item.id)
            if not layer_info:
                continue
            delay_ms = int((item.start_time - base_start) * 1000)
            self._layer_previews[item.id] = True
            layer_info["btn"].configure(text="\u25a0 Stop", fg_color="#ff4444", text_color="#ffffff")
            # Agendar inicio do playhead com delay
            if delay_ms <= 0:
                self._start_playhead_animation(
                    item.id, layer_info["canvas"], layer_info["time_lbl"],
                    item.duration, play_start, layer_info["color"], loop=False)
            else:
                layer_info["canvas"].after(delay_ms, lambda iid=item.id, li=layer_info, d=item.duration, c=layer_info["color"]:
                    self._start_playhead_animation(
                        iid, li["canvas"], li["time_lbl"],
                        d, _time.time(), c, loop=False))

        # Agendar reset
        total_dur_ms = int((max(i.start_time + i.duration for i in items) - base_start) * 1000)
        try:
            self._play_all_btn.after(total_dur_ms, self._on_play_all_ended)
        except Exception:
            pass

    def _on_play_all_ended(self):
        """Reset do botao e playheads quando o audio termina."""
        self._play_all_playing = False
        # Parar todos os playheads
        for item_id in list(self._layer_previews.keys()):
            self._layer_previews[item_id] = False
            info = self._layer_canvases.get(item_id)
            if info:
                try:
                    info["canvas"].delete("playhead")
                    info["btn"].configure(text="\u25b6 Play", fg_color=info["color"], text_color="#0a0a0f")
                except Exception:
                    pass
        if hasattr(self, '_play_all_btn') and self._play_all_btn:
            color = self._current_color
            self._play_all_btn.configure(
                text="\u25b6 PLAY CONJUNTO", fg_color=C["card"],
                text_color=color)

    def _save_all_params(self, track):
        """Salva parametros de todos os layers da track."""
        from makevid.config import PROJECTS_DIR
        for item_id, sliders in self._layer_sliders.items():
            item = next((i for i in self.fx_panel.timeline.project.track_items if i.id == item_id), None)
            if item:
                item.params["volume"] = str(int(sliders["volume"].get()))
                item.params["pan"] = str(int(sliders["pan"].get()))
                item.params["fade_in"] = str(int(sliders["fade_in"].get()))
                item.params["fade_out"] = str(int(sliders["fade_out"].get()))
        # Loop state
        if self._voice_loop:
            for item in self.fx_panel.timeline.project.get_track_items(track):
                item.params["loop"] = "1" if self._voice_loop.get() else "0"
        if self._sfx_loop:
            for item in self.fx_panel.timeline.project.get_track_items(track):
                item.params["loop"] = "1" if self._sfx_loop.get() else "0"
        if self._music_loop:
            for item in self.fx_panel.timeline.project.get_track_items(track):
                item.params["loop"] = "1" if self._music_loop.get() else "0"
        if self._audio_loop:
            for item in self.fx_panel.timeline.project.get_track_items(track):
                item.params["loop"] = "1" if self._audio_loop.get() else "0"
        self.fx_panel.timeline.project.save(PROJECTS_DIR)


    # ============================================================
    # UTILS
    # ============================================================

    def _get_overlapping_items(self, item, track):
        """Retorna items do mesmo clip (mesmo clip_index)."""
        all_track = self.fx_panel.timeline.project.get_track_items(track)
        if item.clip_index >= 0:
            return [i for i in all_track if i.clip_index == item.clip_index]
        return [i for i in all_track if abs(i.start_time - item.start_time) < 0.05]

    def _compact_slider(self, parent, label, from_, to, default, unit, color, steps=100, tooltip=None):
        """Slider compacto em uma linha."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=4, pady=2)
        lbl_widget = ctk.CTkLabel(f, text=label, font=("Consolas", 8, "bold"), text_color=C["text3"],
                     width=50)
        lbl_widget.pack(side="left")
        if tooltip:
            from makevid.ui.menus import _ToolTip
            _ToolTip(lbl_widget, tooltip)
        lbl = ctk.CTkLabel(f, text=f"{default}{unit}", font=("Consolas", 8), text_color=C["text3"],
                           width=50)
        lbl.pack(side="right")
        slider = ctk.CTkSlider(f, from_=from_, to=to, number_of_steps=steps,
                                height=12, fg_color=C["border"], progress_color=color,
                                button_color=color, button_hover_color=color)
        slider.set(default)
        slider.pack(side="left", fill="x", expand=True, padx=(0, 4))
        slider.configure(command=lambda v, l=lbl, u=unit: l.configure(text=f"{int(v)}{u}"))
        return slider

    def _darken_color(self, hex_color, factor=0.5):
        """Escurece uma cor hex por um fator (0=preto, 1=original)."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
