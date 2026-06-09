"""Panel Estilo - Storyboard + Personagens ocupam o espaco do gerador+preview."""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from PIL import Image
import uuid
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR


class StylePanel:
    """Painel que substitui gerador+preview para editar Storyboard e Personagens."""

    def __init__(self, app):
        self.app = app
        self._frame = None
        self._visible = False
        self._img_refs = []
        self._current_tab = "storyboard"

    def show(self, tab="world"):
        if tab == "world":
            tab = "storyboard"
        if self._visible:
            self._switch_tab(tab)
            return
        self._current_tab = tab
        self.app.generator_panel.container.pack_forget()
        self.app.preview_panel.panel.pack_forget()
        self._frame = ctk.CTkFrame(self.app._main, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=6)
        self._frame.pack(fill="both", expand=True, padx=0, pady=4)
        self._build()
        self._visible = True

    def hide(self):
        if not self._visible:
            return
        if self._frame and self._frame.winfo_exists():
            self._frame.destroy()
            self._frame = None
        self.app.generator_panel.container.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self.app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self._visible = False

    def _build(self):
        f = self._frame
        header = ctk.CTkFrame(f, height=38, fg_color=C["card"], corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="ESTILO", font=("Segoe UI", 12, "bold"),
                     text_color=C["gold"]).pack(side="left", padx=12)

        self._tab_story_btn = ctk.CTkButton(
            header, text="STORYBOARD", height=28, width=120,
            font=("Segoe UI", 9, "bold"), corner_radius=0,
            fg_color=C["panel"] if self._current_tab == "storyboard" else C["card"],
            text_color=C["gold"] if self._current_tab == "storyboard" else C["text3"],
            hover_color=C["card_hover"],
            command=lambda: self._switch_tab("storyboard"))
        self._tab_story_btn.pack(side="left", padx=(10, 0))

        self._tab_chars_btn = ctk.CTkButton(
            header, text="PERSONAGENS", height=28, width=120,
            font=("Segoe UI", 9, "bold"), corner_radius=0,
            fg_color=C["panel"] if self._current_tab == "chars" else C["card"],
            text_color=C["cyan"] if self._current_tab == "chars" else C["text3"],
            hover_color=C["card_hover"],
            command=lambda: self._switch_tab("chars"))
        self._tab_chars_btn.pack(side="left")

        ctk.CTkButton(header, text="\u2715", width=30, height=26,
                      font=("Segoe UI", 14, "bold"), fg_color="transparent",
                      text_color="#ff4444", hover_color="#2a0808",
                      corner_radius=4,
                      command=self.hide).pack(side="right", padx=6)

        self._content = ctk.CTkFrame(f, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        if self._current_tab == "storyboard":
            self._build_storyboard()
        else:
            self._build_characters()

    def _switch_tab(self, tab):
        if tab == self._current_tab and self._visible:
            return
        self._current_tab = tab
        if self._visible:
            self._frame.destroy()
            self._frame = ctk.CTkFrame(self.app._main, fg_color=C["panel"],
                                       border_color=C["gold"], border_width=1, corner_radius=6)
            self._frame.pack(fill="both", expand=True, padx=0, pady=4)
            self._build()

    # ============================================================
    # STORYBOARD (estilo global + cenas como planilha)
    # ============================================================

    def _build_storyboard(self):
        from makevid.ui.menus import _ToolTip
        p = self._content

        self._resize_active = False
        self._resize_col = None

        # Top bar
        top = ctk.CTkFrame(p, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="\U0001f3ac STORYBOARD", font=("Segoe UI", 13, "bold"),
                     text_color=C["gold"]).pack(side="left")
        nova_btn = ctk.CTkButton(top, text="NOVA CENA", width=90, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color="#44cc88", border_width=1,
                      text_color="#44cc88", hover_color="#0a2a1a",
                      corner_radius=4,
                      command=self._add_scene)
        nova_btn.pack(side="right")
        _ToolTip(nova_btn, "Adiciona uma nova cena vazia ao storyboard.")
        import_btn = ctk.CTkButton(top, text="\u2913", width=28, height=26,
                      font=("Segoe UI", 12, "bold"), fg_color=C["card"],
                      border_color="#44cc88", border_width=1,
                      text_color="#44cc88", hover_color="#0a2a1a",
                      corner_radius=4,
                      command=self._import_txt)
        import_btn.pack(side="right", padx=(0, 4))
        _ToolTip(import_btn, "Importar cenas de arquivo .txt\n\nFormato aceito (tabela ou livre):\n| # | VISUAL | CAMERA | DIALOGUE | DURATION |\n|---|---|---|---|---|\n| 1 | cena descrita aqui | close-up | fala | 5 |\n\nOu texto livre (cada linha = 1 cena):\nUm guerreiro entra na caverna\nEle encontra o dragao dormindo")

        # Sheet container
        sheet = ctk.CTkFrame(p, fg_color="#0a0c18", border_color=C["border"],
                             border_width=1, corner_radius=4)
        sheet.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        # Horizontal scroll for wide tables
        self._table_scroll = ctk.CTkScrollableFrame(sheet, fg_color="#0a0c18",
                                                     corner_radius=0,
                                                     scrollbar_button_color=C["gold"],
                                                     scrollbar_button_hover_color="#ffd700")
        self._table_scroll.pack(fill="both", expand=True)

        # Build header + rows inside scroll
        self._build_table()

        # Bottom buttons
        btns = ctk.CTkFrame(p, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=(4, 10))
        ctk.CTkButton(btns, text="\u25b6 SALVAR E GERAR TIMELINE", height=30,
                      font=("Segoe UI", 10, "bold"), fg_color=C["cyan"],
                      text_color="#0a0a0f", hover_color="#00ffee",
                      corner_radius=4,
                      command=self._save_storyboard_to_timeline).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btns, text="\u2398 COPIAR CENAS", width=110, height=30,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["gold"], border_width=1,
                      text_color=C["gold"], hover_color="#2a2a0a",
                      corner_radius=4,
                      command=self._copy_scenes_to_clipboard).pack(side="left", padx=(4, 4))
        ctk.CTkButton(btns, text="LIMPAR TODOS", width=110, height=30,
                      font=("Segoe UI", 9, "bold"), fg_color="#2a0808",
                      border_color="#ff4444", border_width=1,
                      text_color="#ff4444", hover_color="#3a1010",
                      corner_radius=4,
                      command=self._clear_scenes).pack(side="right")

    def _build_table(self):
        """Build table using a SINGLE grid for perfect column alignment."""
        for w in self._table_scroll.winfo_children():
            w.destroy()
        self._scene_widgets = []
        self._resize_active = False
        self._resize_col = None

        container = self._table_scroll

        if not hasattr(self, '_col_weights') or not self._col_weights:
            self._col_weights = [1, 1, 1, 1, 1]

        # Single grid for entire table (use tk.Frame for zero internal padding)
        import tkinter as tk
        self._grid = tk.Frame(container, bg="#0a0c18", bd=0, highlightthickness=0)
        self._grid.pack(fill="both", expand=True)

        # Column layout: 0=#, 1=div, 2=VISUAL, 3=div, 4=CAMERA, 5=div, 6=SFX, 7=div, 8=DIALOGO, 9=div, 10=EMOCAO, 11=div, 12=TEMPO, 13=X
        # Fixed columns
        self._grid.columnconfigure(0, weight=0, minsize=32)   # #
        self._grid.columnconfigure(1, weight=0, minsize=2)    # div after #
        # Data columns (2,4,6,8,10)
        data_cols = [2, 4, 6, 8, 10]
        for i, gc in enumerate(data_cols):
            self._grid.columnconfigure(gc, weight=self._col_weights[i])
        # Divider columns between data (3,5,7,9)
        for dc in [3, 5, 7, 9]:
            self._grid.columnconfigure(dc, weight=0, minsize=3)
        # Right fixed
        self._grid.columnconfigure(11, weight=0, minsize=2)   # div before TEMPO
        self._grid.columnconfigure(12, weight=0, minsize=44)  # TEMPO
        self._grid.columnconfigure(13, weight=0, minsize=22)  # X

        # === ROW 0: HEADER ===
        r = 0
        self._grid.rowconfigure(r, weight=0)
        tk.Label(self._grid, text="#", font=("Consolas", 8, "bold"),
                 fg=C["gold"], bg="#111328", anchor="center").grid(row=r, column=0, sticky="nsew")
        tk.Frame(self._grid, width=2, bg="#2a2a4a").grid(row=r, column=1, sticky="ns")

        col_info = [
            ("VISUAL", "#0ac8b9"), ("CAMERA", "#3399ff"),
            ("SFX", "#44cc88"), ("DIALOGO", "#ff9944"), ("EMOCAO", "#cc44aa"),
        ]
        for i, (txt, clr) in enumerate(col_info):
            gc = data_cols[i]
            tk.Label(self._grid, text=txt, font=("Consolas", 8, "bold"),
                     fg=clr, bg="#111328", anchor="center").grid(row=r, column=gc, sticky="nsew", padx=4)

        # Draggable dividers in header
        div_cols = [3, 5, 7, 9]
        for di, dc in enumerate(div_cols):
            div = tk.Frame(self._grid, width=3, bg="#2a2a4a", cursor="sb_h_double_arrow")
            div.grid(row=r, column=dc, sticky="ns", rowspan=999)
            div.bind("<Enter>", lambda e, d=div: d.configure(bg=C["gold"]))
            div.bind("<Leave>", lambda e, d=div: d.configure(bg="#2a2a4a") if not self._resize_active else None)
            div.bind("<Button-1>", lambda e, idx=di: self._sash_start(e, idx))
            div.bind("<B1-Motion>", self._sash_drag)
            div.bind("<ButtonRelease-1>", self._sash_end)

        tk.Frame(self._grid, width=2, bg="#2a2a4a").grid(row=r, column=11, sticky="ns")
        tk.Label(self._grid, text="TEMPO", font=("Consolas", 7, "bold"),
                 fg=C["cyan"], bg="#111328", anchor="center").grid(row=r, column=12, sticky="nsew")
        tk.Label(self._grid, text="", bg="#111328").grid(row=r, column=13, sticky="nsew")

        # Separator row
        r += 1
        self._grid.rowconfigure(r, weight=0, minsize=1)
        tk.Frame(self._grid, height=1, bg=C["gold"]).grid(
            row=r, column=0, columnspan=14, sticky="ew")

        # === DATA ROWS ===
        scenes = self.app.project.world.scenes
        if not scenes:
            r += 1
            tk.Label(self._grid, text="Clique NOVA CENA para adicionar.",
                     fg=C["text3"], bg="#0a0c18", font=("Segoe UI", 10)).grid(
                row=r, column=0, columnspan=14, pady=30)
            return

        field_keys = ["visual", "camera", "audio", "dialogue", "emotion"]
        field_colors = ["#0ac8b9", "#3399ff", "#44cc88", "#ff9944", "#cc44aa"]

        for idx, scene in enumerate(scenes):
            r += 1
            self._grid.rowconfigure(r, weight=0)
            bg = "#0d0f1a" if idx % 2 == 0 else "#0b0d16"

            # # column
            tk.Label(self._grid, text=f"{idx+1}", font=("Consolas", 9, "bold"),
                     fg=C["gold"], bg=bg, anchor="center").grid(row=r, column=0, sticky="nsew")
            # div
            tk.Frame(self._grid, width=2, bg="#2a2a4a").grid(row=r, column=1, sticky="ns")

            # Data cells
            vars_dict = {}
            field_borders = ["#1a3a3a", "#1a3a3a", "#1a3a2a", "#3a2a1a", "#3a1a3a"]
            field_borders_hover = ["#0ac8b9", "#0ac8b9", "#44cc88", "#ff9944", "#cc44aa"]
            for i, key in enumerate(field_keys):
                gc = data_cols[i]
                val = scene.get(key, "")
                cell_frame = ctk.CTkFrame(self._grid, fg_color="#080a14",
                                          border_color=field_borders[i], border_width=2,
                                          corner_radius=8)
                cell_frame.grid(row=r, column=gc, sticky="nsew", padx=5, pady=4)
                txt = tk.Text(cell_frame, height=2, width=1,
                              bg="#080a14", fg=field_colors[i],
                              font=("Consolas", 11, "bold"),
                              bd=0, highlightthickness=0,
                              insertbackground=field_colors[i],
                              selectbackground="#1a3a5a",
                              selectforeground=field_colors[i],
                              wrap="word", undo=True,
                              padx=8, pady=6)
                txt.pack(fill="both", expand=True, padx=6, pady=6)
                if val:
                    txt.insert("1.0", val)
                # Hover effect - border glows
                border_clr = field_borders[i]
                hover_clr = field_borders_hover[i]
                def _enter(e, f=cell_frame, c=hover_clr):
                    f.configure(border_color=c, border_width=3)
                def _leave(e, f=cell_frame, c=border_clr):
                    f.configure(border_color=c, border_width=2)
                cell_frame.bind("<Enter>", _enter)
                cell_frame.bind("<Leave>", _leave)
                txt.bind("<Enter>", _enter)
                txt.bind("<Leave>", _leave)
                # Auto-resize height on content change
                def _auto_height(event=None, w=txt):
                    try:
                        content = w.get("1.0", "end-1c")
                        if not content:
                            w.configure(height=2)
                            return
                        w_width = w.winfo_width()
                        if w_width < 10:
                            w_width = 200
                        char_width = 8
                        chars_per_line = max(5, (w_width - 10) // char_width)
                        total_lines = 0
                        for line in content.split("\n"):
                            line_len = len(line) if line else 1
                            total_lines += max(1, -(-line_len // chars_per_line))
                        w.configure(height=max(2, total_lines))
                    except Exception:
                        pass
                txt.bind("<KeyRelease>", _auto_height)
                txt.bind("<Configure>", _auto_height)
                txt.bind("<Button-1>", lambda e, w=txt: w.after(10, lambda: w.focus_force()), add="+")
                if val:
                    _auto_height(w=txt)
                vars_dict[key] = txt

            # div before TEMPO
            tk.Frame(self._grid, width=2, bg="#2a2a4a").grid(row=r, column=11, sticky="ns")

            # TEMPO
            dur_var = ctk.StringVar(value=scene.get("duration", "5"))
            ctk.CTkEntry(self._grid, textvariable=dur_var, width=40, height=20,
                         fg_color="#080a14", border_color=C["border"], border_width=1,
                         text_color=C["cyan"], font=("Consolas", 9, "bold"),
                         justify="center").grid(row=r, column=12, sticky="", pady=2)

            # X button
            ctk.CTkButton(self._grid, text="\u2715", width=16, height=16,
                          font=("Segoe UI", 7), fg_color="transparent",
                          text_color="#ff4444", hover_color="#2a0808",
                          command=lambda i=idx: self._remove_scene(i)
                          ).grid(row=r, column=13, sticky="", pady=2)

            vars_dict["dur"] = dur_var
            self._scene_widgets.append(vars_dict)

    def _sash_start(self, event, div_idx):
        """div_idx: 0-3 for dividers between columns."""
        self._resize_active = True
        self._resize_col = div_idx
        self._resize_start_x = event.x_root
        self._left_col = div_idx
        self._right_col = div_idx + 1
        # Capture current widths from grid_bbox
        data_cols = [2, 4, 6, 8, 10]
        self._grid.update_idletasks()
        widths = []
        for gc in data_cols:
            bbox = self._grid.grid_bbox(column=gc)
            widths.append(bbox[2] if bbox and bbox[2] else 80)
        self._col_weights = widths
        self._start_left_w = self._col_weights[self._left_col]
        self._start_right_w = self._col_weights[self._right_col]
        # Lock all columns to current pixel proportions
        for i, gc in enumerate(data_cols):
            self._grid.columnconfigure(gc, weight=self._col_weights[i])

    def _sash_drag(self, event):
        if not self._resize_active or self._resize_col is None:
            return
        dx = event.x_root - self._resize_start_x
        new_left = max(40, self._start_left_w + dx)
        new_right = max(40, self._start_right_w - dx)
        self._col_weights[self._left_col] = new_left
        self._col_weights[self._right_col] = new_right
        data_cols = [2, 4, 6, 8, 10]
        self._grid.columnconfigure(data_cols[self._left_col], weight=new_left)
        self._grid.columnconfigure(data_cols[self._right_col], weight=new_right)

    def _sash_end(self, event):
        self._resize_active = False
        self._resize_col = None

    def _refresh_scenes(self):
        self._build_table()

    def _collect_scenes(self):
        scenes = []
        for w in self._scene_widgets:
            scenes.append({
                "visual": w["visual"].get("1.0", "end").strip(),
                "camera": w["camera"].get("1.0", "end").strip(),
                "audio": w["audio"].get("1.0", "end").strip(),
                "dialogue": w["dialogue"].get("1.0", "end").strip(),
                "emotion": w["emotion"].get("1.0", "end").strip(),
                "duration": w["dur"].get().strip() or "5",
            })
        self.app.project.world.scenes = scenes

    def _add_scene(self):
        self._collect_scenes()
        self.app.project.world.scenes.append({"visual":"","camera":"","audio":"","dialogue":"","emotion":"","duration":"5"})
        self.app.project.save(PROJECTS_DIR)
        self._refresh_scenes()
        # Scroll to bottom to show new scene
        self._table_scroll.after(50, lambda: self._table_scroll._parent_canvas.yview_moveto(1.0))

    def _remove_scene(self, idx):
        self._collect_scenes()
        if idx < len(self.app.project.world.scenes):
            self.app.project.world.scenes.pop(idx)
            self.app.project.save(PROJECTS_DIR)
            self._refresh_scenes()

    def _copy_scenes_to_clipboard(self):
        """Copia cenas formatadas como tabela para o clipboard."""
        self._collect_scenes()
        scenes = self.app.project.world.scenes
        if not scenes:
            return

        # Campos do storyboard
        fields = ["visual", "camera", "dialogue", "emotion", "ambience", "sfx", "music_mood", "duration"]
        # Header
        lines = []
        lines.append("| # | " + " | ".join(f.upper() for f in fields) + " |")
        lines.append("|---| " + " | ".join("---" for _ in fields) + " |")
        # Rows
        for i, scene in enumerate(scenes):
            row = [str(i + 1)]
            for f in fields:
                val = scene.get(f, "").replace("|", "/").replace("\n", " ")
                row.append(val[:40] if val else "-")
            lines.append("| " + " | ".join(row) + " |")

        text = "\n".join(lines)
        self.app.clipboard_clear()
        self.app.clipboard_append(text)

    def _import_txt(self):
        """Importa cenas de um arquivo de texto (.txt)."""
        from tkinter import filedialog
        from makevid.config import PROJECTS_DIR

        path = filedialog.askopenfilename(
            title="Importar Storyboard",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

        fields = ["visual", "camera", "dialogue", "emotion", "ambience", "sfx", "music_mood", "duration"]
        scenes = []

        lines = [l.strip() for l in content.strip().split("\n") if l.strip()]

        # Tentar parsear como tabela markdown (formato do COPIAR CENAS)
        table_lines = [l for l in lines if l.startswith("|")]
        if len(table_lines) >= 3:
            # Pular header e separador
            for row in table_lines[2:]:
                cells = [c.strip() for c in row.split("|")]
                cells = [c for c in cells if c]  # remover vazios
                if len(cells) >= 2:
                    scene = {}
                    # Primeiro campo eh o numero, pular
                    for i, field in enumerate(fields):
                        idx = i + 1  # +1 pq primeiro eh o #
                        if idx < len(cells):
                            val = cells[idx].strip()
                            if val and val != "-":
                                scene[field] = val
                    if scene:
                        if "duration" not in scene:
                            scene["duration"] = "5"
                        scenes.append(scene)
        else:
            # Formato livre: cada linha ou bloco vira uma cena
            # Separar por linhas vazias ou numeros
            import re
            blocks = re.split(r'\n\s*\n|\n(?=\d+[.\)\-]\s)', content.strip())
            if len(blocks) <= 1:
                # Tentar separar por linhas simples
                blocks = [l for l in lines if l and not l.startswith("#")]

            for block in blocks:
                block = block.strip()
                if not block:
                    continue
                # Remover numeracao inicial
                block = re.sub(r'^\d+[.\)\-]\s*', '', block)
                scene = {"visual": block[:200], "duration": "5"}
                scenes.append(scene)

        if not scenes:
            return

        # Substituir cenas atuais
        self.app.project.world.scenes = scenes
        self.app.project.save(PROJECTS_DIR)
        self._refresh_scenes()

    def _clear_scenes(self):
        self.app.project.world.scenes = []
        self.app.project._storyboard_applied = False
        self.app.project.save(PROJECTS_DIR)
        self._refresh_scenes()
        self.app.timeline.draw()

    def _save_all(self):
        """Salva cenas sem gerar timeline."""
        self._collect_scenes()
        self.app.project.save(PROJECTS_DIR)

    def _save_storyboard_to_timeline(self):
        """Salva e atualiza/cria clips baseado no storyboard. Usa params do gerador."""
        self._collect_scenes()
        self.app.project._storyboard_applied = True

        scenes = self.app.project.world.scenes
        clips = sorted(self.app.project.clips, key=lambda c: c.position)

        # Pegar parametros do painel gerador
        gen = self.app.generator_panel
        steps = int(gen.steps_var.get())
        guidance = float(gen.guidance_var.get())
        width, height = gen._get_resolution()
        negative = gen.neg_box.get("0.0", "end").strip()

        for i, scene in enumerate(scenes):
            prompt = scene.get("visual", "")
            camera = scene.get("camera", "")
            full_prompt = f"{prompt}, {camera}" if camera else prompt
            dur = float(scene.get("duration", 5))

            if i < len(clips):
                clips[i].prompt = full_prompt
                clips[i].duration = dur
            else:
                clip = self.app.project.add_clip(prompt=full_prompt, position=i)
                clip.duration = dur

        # Salvar params de geracao no projeto para uso posterior
        self.app.project.output_width = width
        self.app.project.output_height = height

        self.app.project.save(PROJECTS_DIR)
        self.app.timeline.draw()
        self.hide()

        # Gerar clips que ainda nao tem video
        clips = sorted(self.app.project.clips, key=lambda c: c.position)
        for clip in clips:
            if clip.status == "empty" and clip.prompt:
                self.app.request_generation(
                    prompt=clip.prompt,
                    duration=clip.duration,
                    steps=steps,
                    guidance=guidance,
                    seed=None,
                    width=width,
                    height=height,
                    negative=negative,
                    ref_images=None,
                )
                break  # Gera um por vez (o callback gera o proximo)



    def _build_characters(self):
        p = self._content
        self._img_refs = []
        self._editor_char_id = None  # Reset cache para forcar rebuild

        cols = ctk.CTkFrame(p, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=10, pady=10)

        # Lista esquerda
        left = ctk.CTkFrame(cols, width=260, fg_color=C["card"], corner_radius=6,
                             border_color=C["border"], border_width=1)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)
        left.configure(width=260)

        left_header = ctk.CTkFrame(left, fg_color="transparent", height=36)
        left_header.pack(fill="x", padx=10, pady=(10, 0))
        left_header.pack_propagate(False)
        ctk.CTkLabel(left_header, text="PERSONAGENS", font=("Segoe UI", 11, "bold"),
                     text_color=C["cyan"]).pack(side="left")
        from makevid.ui.menus import _ToolTip as _TT2
        add_btn = ctk.CTkButton(left_header, text="+", width=28, height=24,
                      font=("Segoe UI", 12, "bold"), fg_color=C["card"],
                      border_color=C["gold"], border_width=1,
                      text_color=C["gold"], hover_color=C["card_hover"],
                      command=self._add_character)
        add_btn.pack(side="right")
        _TT2(add_btn, "Criar novo personagem vazio.")
        imp_btn = ctk.CTkButton(left_header, text="\u2913", width=28, height=24,
                      font=("Segoe UI", 12, "bold"), fg_color=C["card"],
                      border_color="#44cc88", border_width=1,
                      text_color="#44cc88", hover_color="#0a2a1a",
                      command=self._import_char_txt)
        imp_btn.pack(side="right", padx=(0, 4))
        _TT2(imp_btn, "Importar personagem de arquivo .txt\n\nFormato aceito:\nNOME: Guerreira\nTIPO: humano\nRESUMO: Pirata com martelo\nIDADE: 25\nALTURA E CONSTITUICAO: 1.75m | atletica\nROSTO E CABECA: olhos verdes\nCABELO / CABECA: verde brilhante\nTRAJE / ARMADURA: top preto\nESTILO VISUAL: UE5 MetaHuman")

        ctk.CTkFrame(left, height=1, fg_color=C["cyan"]).pack(fill="x", padx=10, pady=(6, 4))

        self._char_list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                                        scrollbar_button_color=C["cyan"],
                                                        scrollbar_button_hover_color="#00ffee")
        self._char_list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._char_editor = ctk.CTkScrollableFrame(cols, fg_color=C["card"], corner_radius=6,
                                                    border_color=C["border"], border_width=1,
                                                    scrollbar_button_color=C["gold"],
                                                    scrollbar_button_hover_color="#ffd700")
        self._char_editor.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self._selected_char_id = None
        self._refresh_char_list()

    def _refresh_char_list(self):
        for w in self._char_list_frame.winfo_children():
            w.destroy()
        self._img_refs = []

        chars = self.app.project.characters
        if not chars:
            ctk.CTkLabel(self._char_list_frame, text="Nenhum personagem.\nClique + para criar.",
                         text_color=C["text3"], font=("Segoe UI", 9)).pack(pady=20)
            self._show_empty_editor()
            return

        for char in chars:
            selected = char.id == self._selected_char_id
            card = ctk.CTkFrame(self._char_list_frame,
                                fg_color=C["panel"] if selected else "transparent",
                                border_color=C["cyan"] if selected else C["border"],
                                border_width=2 if selected else 1, corner_radius=5)
            card._char_id = char.id
            card.pack(fill="x", pady=2)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=6)

            if char.reference_image and Path(char.reference_image).exists():
                try:
                    # Cache de thumbnails
                    cache = getattr(self, '_thumb_cache', {})
                    cache_key = char.reference_image
                    if cache_key in cache:
                        ctk_img = cache[cache_key]
                    else:
                        img = Image.open(char.reference_image).convert("RGB")
                        img.thumbnail((36, 36))
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
                        cache[cache_key] = ctk_img
                        self._thumb_cache = cache
                    self._img_refs.append(ctk_img)
                    ctk.CTkLabel(row, image=ctk_img, text="").pack(side="left", padx=(0, 6))
                except Exception:
                    ctk.CTkLabel(row, text="\U0001f464", font=("Segoe UI", 14),
                                 text_color=C["text3"]).pack(side="left", padx=(0, 6))
            else:
                ctk.CTkLabel(row, text="\U0001f464", font=("Segoe UI", 14),
                             text_color=C["text3"]).pack(side="left", padx=(0, 6))

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(info, text=char.name or "(sem nome)",
                         font=("Segoe UI", 10, "bold"), text_color=C["text"]).pack(anchor="w")
            summary = char.summary or char.description
            ctk.CTkLabel(info, text=(summary[:30] + "...") if len(summary) > 30 else summary,
                         font=("Segoe UI", 8), text_color=C["text3"]).pack(anchor="w")

            for widget in [card, row, info] + info.winfo_children():
                widget.bind("<Button-1>", lambda e, c=char: self._select_char(c))

        if not self._selected_char_id and chars:
            self._select_char(chars[0])
        elif self._selected_char_id:
            char = next((c for c in chars if c.id == self._selected_char_id), None)
            if char:
                self._build_char_editor(char)
            else:
                self._show_empty_editor()

    def _select_char(self, char):
        self._selected_char_id = char.id
        # Atualizar visual dos cards sem recriar tudo
        for card in self._char_list_frame.winfo_children():
            if hasattr(card, '_char_id'):
                is_sel = card._char_id == char.id
                card.configure(
                    fg_color=C["panel"] if is_sel else "transparent",
                    border_color=C["cyan"] if is_sel else C["border"],
                    border_width=2 if is_sel else 1)
        self._build_char_editor(char)

    def _show_empty_editor(self):
        for w in self._char_editor.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._char_editor, text="Selecione ou crie um personagem",
                     text_color=C["text3"], font=("Segoe UI", 11)).pack(pady=40)

    def _build_char_editor(self, char):
        # Evitar recriar se mesmo personagem
        if getattr(self, '_editor_char_id', None) == char.id:
            return
        self._editor_char_id = char.id
        for w in self._char_editor.winfo_children():
            w.destroy()
        ed = self._char_editor
        from makevid.ui.menus import _ToolTip

        ctk.CTkLabel(ed, text="FICHA DE PERSONAGEM", font=("Segoe UI", 12, "bold"),
                     text_color=C["gold"]).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkFrame(ed, height=1, fg_color=C["gold"]).pack(fill="x", padx=12, pady=(0, 8))

        # === GRID DE IMAGENS NO TOPO ===
        img_section = ctk.CTkFrame(ed, fg_color=C["panel"], corner_radius=4,
                                    border_color=C["cyan"], border_width=1)
        img_section.pack(fill="x", padx=12, pady=(0, 8))

        img_header = ctk.CTkFrame(img_section, fg_color="transparent")
        img_header.pack(fill="x", padx=8, pady=(6, 4))
        img_lbl = ctk.CTkLabel(img_header, text="IMAGENS DE REFERENCIA", text_color=C["cyan"],
                     font=("Segoe UI", 9, "bold"))
        img_lbl.pack(side="left")
        _ToolTip(img_lbl, "Imagens de referencia visual do personagem.\nUsadas pela engine VACE para consistencia.\nAdicione varias poses/angulos.")

        add_img_btn = ctk.CTkButton(img_header, text="+ IMG", width=55, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color=C["card"],
                      border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      command=lambda: self._add_ref_image(char))
        add_img_btn.pack(side="right")
        _ToolTip(add_img_btn, "Adicionar imagem (PNG, JPG, WEBP).\nVarias imagens = melhor consistencia.")

        self._ref_grid_frame = ctk.CTkFrame(img_section, fg_color="transparent")
        self._ref_grid_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._render_ref_grid(char)

        # === CAMPOS ===
        fields = [
            ("NOME", "name", "entry", "Nome do personagem",
             "Nome unico do personagem.\nQuando voce digitar esse nome no prompt,\no sistema injeta automaticamente as caracteristicas dele."),
            ("TIPO", "char_type", "entry", "humano / humanoide / criatura / robo / alienigena",
             "Tipo de personagem.\nEx: humano, humanoide, criatura de fantasia,\nrobo, alienigena, estilizado"),
            ("RESUMO", "summary", "text", "Descricao curta",
             "Descricao curta e direta do personagem.\nEx: Guerreira pirata com martelo gigante,\ncabelo verde, estetica dark fantasy"),
            ("PERFIL DEMOGRAFICO", "demographic", "entry", "Perfil demografico",
             "Perfil fisico base do personagem em pe.\nEx: mulher caucasiana, corpo atletico,\n1.75m, pele clara com sardas"),
            ("IDADE", "age", "entry", "Idade ou idade aparente",
             "Idade real ou aparente.\nEx: 25, aparenta 30, adolescente, anciã"),
            ("ALTURA E CONSTITUICAO", "height_build", "entry", "1.80m | atletico",
             "Altura e tipo fisico.\nEx: 1.65m | atletica, 2.0m | musculoso pesado,\n1.50m | magra e agil"),
            ("PROPORCAO", "proportion_style", "entry", "realista 7-7.5 cabecas / heroico",
             "Estilo de proporcao corporal.\nEx: realista 7.5 cabecas, heroico 8 cabecas,\nchibi 3 cabecas, estilizado anime"),
            ("ROSTO E CABECA", "face_design", "text", "Formato, olhos, nariz, mandibula",
             "Design detalhado do rosto.\nEx: rosto oval, olhos grandes amarelo-verde,\nnariz pequeno, mandibula afilada,\nexpressao base: sorriso confiante"),
            ("CABELO / CABECA", "hair_head", "entry", "Cor, comprimento, textura",
             "Cabelo e detalhes da cabeca.\nEx: verde brilhante, franja lateral,\nrabo de cavalo alto preso com anel metalico,\noculos de aviador empurrados na testa"),
            ("PELE / SUPERFICIE", "skin_surface", "text", "Tonalidade, cicatrizes, tatuagens",
             "Detalhes da pele/superficie.\nEx: pele clara, marcas de batalha azuis\nsob o olho esquerdo, cicatriz no braco direito,\ntextura realista com poros visiveis"),
            ("TRAJE / ARMADURA", "costume", "text", "Descricao completa do traje",
             "Roupa/armadura detalhada.\nEx: top preto estilo marinheiro com laco,\nfivelas de latao, shorts rasgados pretos,\nmeia listrada preta/cinza na perna esquerda,\nperna direita nua com meia curta"),
            ("DETALHES ASSIMETRICOS", "asymmetric_details", "text", "Lado exato de cada detalhe",
             "IMPORTANTE: sempre do ponto de vista DO PERSONAGEM.\nEx: bracelete com corrente no braco ESQUERDO,\nbracelete com espinhos no braco DIREITO,\nmarcas azuis apenas sob olho ESQUERDO\nNunca espelhe entre as views!"),
            ("ACESSORIOS", "accessories", "entry", "Joias, armas, asas, cauda",
             "Objetos e aderecos.\nEx: martelo gigante com cranio de touro,\n3 cranios pendurados no cinto\n(esquerdo vermelho, centro natural, direito verde),\noculos de aviador na testa"),
            ("CONTINUIDADE", "continuity_locks", "text", "Recursos inegociaveis",
             "Detalhes que NUNCA podem mudar entre cenas.\nEx: oculos SEMPRE na testa (nunca nos olhos),\ncabelo SEMPRE verde vibrante sem tons amarelados,\nmarcas azuis APENAS no olho esquerdo,\nassimetria das pernas e obrigatoria"),
            ("ESTILO VISUAL", "visual_style", "entry", "UE5 MetaHuman / anime / fantasia",
             "Estilo de renderizacao do personagem.\nEx: UE5 MetaHuman fotorrealista,\nanime estilizado, fantasia sombria,\nsci-fi superficie dura"),
        ]

        self._char_vars = {}
        self._char_textboxes = {}

        for label, attr, wtype, ph, tooltip in fields:
            lbl = ctk.CTkLabel(ed, text=label, text_color=C["text2"],
                         font=("Segoe UI", 9, "bold"))
            lbl.pack(anchor="w", padx=12, pady=(5, 1))
            _ToolTip(lbl, tooltip)

            val = str(getattr(char, attr, "") or "")
            if wtype == "text":
                box = ctk.CTkTextbox(ed, height=45, fg_color=C["input"],
                                     border_color=C["border"], border_width=2,
                                     text_color=C["cyan"], font=("Consolas", 11, "bold"),
                                     corner_radius=8)
                box.pack(fill="x", padx=12, pady=(0, 2))
                box.insert("0.0", val)
                box.bind("<Enter>", lambda e, b=box: b.configure(border_color=C["gold"], border_width=3))
                box.bind("<Leave>", lambda e, b=box: b.configure(border_color=C["border"], border_width=2))
                box.bind("<Button-1>", lambda e, b=box: b.after(10, lambda: b.focus_force()), add="+")
                self._char_textboxes[attr] = box
            else:
                var = ctk.StringVar(value=val)
                entry = ctk.CTkEntry(ed, textvariable=var, fg_color=C["input"],
                             border_color=C["border"], border_width=2, text_color=C["cyan"],
                             font=("Consolas", 11, "bold"), height=28,
                             corner_radius=8,
                             placeholder_text=ph)
                entry.pack(fill="x", padx=12, pady=(0, 2))
                entry.bind("<Enter>", lambda e, en=entry: en.configure(border_color=C["gold"], border_width=3))
                entry.bind("<Leave>", lambda e, en=entry: en.configure(border_color=C["border"], border_width=2))
                entry.bind("<Button-1>", lambda e, en=entry: en.after(10, lambda: en.focus_force()), add="+")
                self._char_vars[attr] = var

        # === VOZ DO PERSONAGEM ===
        self._build_voice_section(ed, char)

        # Botoes
        btn_frame = ctk.CTkFrame(ed, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkButton(btn_frame, text="SALVAR", height=34,
                      font=("Segoe UI", 11, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700",
                      command=lambda: self._save_char_full(char)).pack(side="left", fill="x", expand=True, padx=(0, 4))
        copy_btn = ctk.CTkButton(btn_frame, text="COPIAR FICHA", height=34, width=100,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      command=lambda: self._copy_sheet_prompt(char))
        copy_btn.pack(side="left", padx=(0, 4))
        _ToolTip(copy_btn, "Copia um prompt completo de ficha de producao\npara o clipboard. Cole num gerador de imagem\n(Midjourney, DALL-E, Flux) para criar\na imagem de referencia do personagem.")
        ctk.CTkButton(btn_frame, text="REMOVER", height=34, width=80,
                      font=("Segoe UI", 9, "bold"), fg_color="#2a0808",
                      text_color="#ff4444", hover_color="#3a1010",
                      border_color="#ff4444", border_width=1,
                      command=lambda: self._remove_char(char)).pack(side="right")

    def _save_char_full(self, char):
        for attr, var in self._char_vars.items():
            setattr(char, attr, var.get().strip())
        for attr, box in self._char_textboxes.items():
            setattr(char, attr, box.get("0.0", "end").strip())
        # Salvar voz
        if hasattr(self, '_voice_id_var'):
            char.voice_id = self._voice_id_var.get()
        if hasattr(self, '_voice_sample_path'):
            char.voice_sample = self._voice_sample_path or ""
        self.app.project.save(PROJECTS_DIR)
        self._editor_char_id = None
        self._refresh_char_list()

    def _copy_sheet_prompt(self, char):
        self._save_char_full(char)
        sheet = char.to_sheet_prompt()
        self.app.clipboard_clear()
        self.app.clipboard_append(sheet)

    def _build_voice_section(self, ed, char):
        """Constroi secao de voz do personagem com seletor + gravacao."""
        from makevid.ui.menus import _ToolTip
        from makevid.core.tts_provider import get_available_voices

        ctk.CTkFrame(ed, height=1, fg_color=C["cyan"]).pack(fill="x", padx=12, pady=(10, 4))
        voice_lbl = ctk.CTkLabel(ed, text="\U0001f3a4 VOZ DO PERSONAGEM", font=("Segoe UI", 11, "bold"),
                     text_color=C["cyan"])
        voice_lbl.pack(anchor="w", padx=12, pady=(0, 4))
        _ToolTip(voice_lbl, "Selecione uma voz TTS para este personagem.\nUsada automaticamente ao gerar audio das cenas.\nOu importe/grave uma amostra de voz real.")

        voice_frame = ctk.CTkFrame(ed, fg_color=C["panel"], corner_radius=4,
                                    border_color=C["cyan"], border_width=1)
        voice_frame.pack(fill="x", padx=12, pady=(0, 8))

        # Seletor de voz TTS
        ctk.CTkLabel(voice_frame, text="Voz TTS", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

        voices = get_available_voices("pt-BR") + get_available_voices("en-US")
        voice_names = [v["ShortName"] for v in voices] if voices else ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"]

        self._voice_id_var = ctk.StringVar(value=char.voice_id or voice_names[0])
        ctk.CTkOptionMenu(voice_frame, variable=self._voice_id_var,
                          values=voice_names,
                          fg_color=C["card"], button_color=C["cyan"],
                          button_hover_color="#00ffee",
                          text_color=C["text"], font=("Segoe UI", 9),
                          dropdown_fg_color=C["card"],
                          dropdown_hover_color=C["card_hover"],
                          dropdown_text_color=C["text"],
                          width=220, height=26).pack(anchor="w", padx=8, pady=(0, 6))

        # Botao testar voz
        test_row = ctk.CTkFrame(voice_frame, fg_color="transparent")
        test_row.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkButton(test_row, text="\u25b6 Testar", width=70, height=24,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      command=lambda: self._test_voice(char)).pack(side="left", padx=(0, 4))

        # Amostra de voz (importar/gravar)
        ctk.CTkFrame(voice_frame, height=1, fg_color=C["border"]).pack(fill="x", padx=8, pady=(4, 4))
        ctk.CTkLabel(voice_frame, text="Amostra de voz (opcional)", text_color=C["text3"],
                     font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(0, 2))

        self._voice_sample_path = char.voice_sample or ""
        sample_row = ctk.CTkFrame(voice_frame, fg_color="transparent")
        sample_row.pack(fill="x", padx=8, pady=(0, 6))

        self._voice_sample_lbl = ctk.CTkLabel(sample_row,
            text=Path(self._voice_sample_path).name if self._voice_sample_path else "Nenhuma",
            text_color=C["text3"], font=("Segoe UI", 8))
        self._voice_sample_lbl.pack(side="left", padx=(0, 6))

        ctk.CTkButton(sample_row, text="Importar", width=60, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color=C["card"],
                      border_color=C["border"], border_width=1,
                      text_color=C["text2"], hover_color=C["card_hover"],
                      command=lambda: self._import_voice_sample(char)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(sample_row, text="\u25cf Gravar", width=60, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color="#2a0808",
                      border_color="#ff4444", border_width=1,
                      text_color="#ff4444", hover_color="#3a1010",
                      command=lambda: self._record_voice_sample(char)).pack(side="left")

    def _test_voice(self, char):
        """Gera e toca preview da voz selecionada."""
        import threading
        voice_id = self._voice_id_var.get()
        name = char.name or "personagem"
        text = f"Ola, eu sou {name}."

        def run():
            from makevid.core.tts_provider import generate_voice
            from makevid.config import AUDIO_DIR
            path = AUDIO_DIR / "_voice_test.wav"
            result = generate_voice(text, path, voice_id=voice_id)
            if result:
                try:
                    import sounddevice as sd
                    import numpy as np
                    import wave
                    with wave.open(str(path), "r") as wf:
                        frames = wf.readframes(wf.getnframes())
                        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                        sd.play(audio, samplerate=wf.getframerate())
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def _import_voice_sample(self, char):
        """Importa amostra de voz WAV/MP3."""
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.mp3 *.ogg")])
        if path:
            self._voice_sample_path = path
            self._voice_sample_lbl.configure(text=Path(path).name)
            char.voice_sample = path
            self.app.project.save(PROJECTS_DIR)

    def _record_voice_sample(self, char):
        """Grava amostra de voz via microfone."""
        from makevid.ui.timeline.recorder import AudioRecorder
        from makevid.config import AUDIO_DIR
        import sounddevice as sd
        import numpy as np
        import wave
        import time as _time

        win = ctk.CTkToplevel(self.app)
        win.title(f"Gravar Voz - {char.name or 'Personagem'}")
        win.geometry("320x180")
        win.configure(fg_color=C["panel"])
        win.transient(self.app)
        win.grab_set()
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="GRAVAR AMOSTRA DE VOZ", font=("Segoe UI", 12, "bold"),
                     text_color=C["cyan"]).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(win, text="Fale algo para o personagem usar como referencia",
                     text_color=C["text3"], font=("Segoe UI", 9)).pack(anchor="w", padx=15)

        time_lbl = ctk.CTkLabel(win, text="00:00.0", font=("Consolas", 18, "bold"), text_color=C["text"])
        time_lbl.pack(pady=(8, 6))

        state = {"recording": False, "frames": [], "start": 0}
        SR = 44100

        def update_time():
            if state["recording"]:
                elapsed = _time.time() - state["start"]
                time_lbl.configure(text=f"{int(elapsed)//60:02d}:{elapsed%60:04.1f}")
                win.after(100, update_time)

        def start():
            state["recording"] = True
            state["frames"] = []
            state["start"] = _time.time()
            btn.configure(text="PARAR", command=stop)
            update_time()
            state["stream"] = sd.InputStream(samplerate=SR, channels=1, dtype="int16",
                                              callback=lambda d, f, t, s: state["frames"].append(d.copy()))
            state["stream"].start()

        def stop():
            state["recording"] = False
            state["stream"].stop()
            state["stream"].close()
            if not state["frames"]:
                win.destroy()
                return
            audio = np.concatenate(state["frames"], axis=0)
            out_dir = AUDIO_DIR / self.app.project.id
            out_dir.mkdir(parents=True, exist_ok=True)
            filepath = out_dir / f"voice_sample_{char.id}.wav"
            with wave.open(str(filepath), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SR)
                wf.writeframes(audio.tobytes())
            char.voice_sample = str(filepath)
            self._voice_sample_path = str(filepath)
            self._voice_sample_lbl.configure(text=filepath.name)
            self.app.project.save(PROJECTS_DIR)
            win.destroy()

        btn = ctk.CTkButton(win, text="\u25cf REC", command=start, height=36,
                            font=("Segoe UI", 13, "bold"), fg_color="#2a0808",
                            border_color="#ff4444", border_width=2,
                            text_color="#ff4444", hover_color="#3a1010")
        btn.pack(fill="x", padx=15, pady=(8, 10))

    def _render_ref_grid(self, char):
        """Renderiza grid de thumbnails das imagens de referencia."""
        for w in self._ref_grid_frame.winfo_children():
            w.destroy()

        ref_path = char.reference_image
        paths = [p.strip() for p in ref_path.split("|") if p.strip()] if ref_path else []

        if not paths:
            ctk.CTkLabel(self._ref_grid_frame, text="Nenhuma imagem. Clique + IMG.",
                         text_color=C["text3"], font=("Segoe UI", 8)).pack(pady=4)
            return

        cols = 4
        row_frame = None
        for i, p in enumerate(paths):
            if i % cols == 0:
                row_frame = ctk.CTkFrame(self._ref_grid_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=2)

            cell = ctk.CTkFrame(row_frame, fg_color=C["card"], corner_radius=4,
                                border_color=C["border"], border_width=1,
                                width=70, height=70)
            cell.pack(side="left", padx=2)
            cell.pack_propagate(False)

            if Path(p).exists():
                try:
                    img = Image.open(p).convert("RGB")
                    img.thumbnail((64, 64))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 64))
                    self._img_refs.append(ctk_img)
                    ctk.CTkLabel(cell, image=ctk_img, text="").pack(expand=True)
                except Exception:
                    ctk.CTkLabel(cell, text="ERR", text_color="#ff4444",
                                 font=("Segoe UI", 8)).pack(expand=True)
            else:
                ctk.CTkLabel(cell, text="?", text_color=C["text3"],
                             font=("Segoe UI", 12)).pack(expand=True)

            ctk.CTkButton(cell, text="\u2715", width=14, height=14, corner_radius=7,
                          fg_color="#ff4444", hover_color="#ff6666",
                          text_color="#ffffff", font=("", 7),
                          command=lambda idx=i, ch=char: self._remove_ref_image(ch, idx)
                          ).place(relx=1.0, rely=0, anchor="ne", x=-2, y=2)

    def _add_ref_image(self, char):
        """Adiciona imagem de referencia ao personagem."""
        path = filedialog.askopenfilename(
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")])
        if not path:
            return
        existing = char.reference_image.strip()
        if existing:
            char.reference_image = f"{existing}|{path}"
        else:
            char.reference_image = path
        self.app.project.save(PROJECTS_DIR)
        self._render_ref_grid(char)

    def _remove_ref_image(self, char, idx):
        """Remove uma imagem de referencia pelo indice."""
        paths = [p.strip() for p in char.reference_image.split("|") if p.strip()]
        if idx < len(paths):
            paths.pop(idx)
        char.reference_image = "|".join(paths)
        self.app.project.save(PROJECTS_DIR)
        self._render_ref_grid(char)

    def _import_char_txt(self):
        """Importa personagem de um arquivo de texto (.txt)."""
        from tkinter import filedialog
        from makevid.core.project import Character
        import uuid

        path = filedialog.askopenfilename(
            title="Importar Personagem",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

        # Mapear labels para atributos
        field_map = {
            "NOME": "name", "TIPO": "char_type", "RESUMO": "summary",
            "PERFIL DEMOGRAFICO": "demographic", "IDADE": "age",
            "ALTURA E CONSTITUICAO": "height_build", "PROPORCAO": "proportion_style",
            "ROSTO E CABECA": "face_design", "CABELO / CABECA": "hair_head",
            "CABELO": "hair_head", "PELE / SUPERFICIE": "skin_surface",
            "PELE": "skin_surface", "TRAJE / ARMADURA": "costume",
            "TRAJE": "costume", "DETALHES ASSIMETRICOS": "asymmetric_details",
            "ACESSORIOS": "accessories", "CONTINUIDADE": "continuity_locks",
            "ESTILO VISUAL": "visual_style",
        }

        char = Character(id=str(uuid.uuid4())[:8], name="")

        # Parsear linhas no formato "LABEL: valor"
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":", 1)
            label = parts[0].strip().upper()
            val = parts[1].strip() if len(parts) > 1 else ""
            attr = field_map.get(label)
            if attr and val:
                setattr(char, attr, val)

        # Se nao tem nome, usar nome do arquivo
        if not char.name:
            from pathlib import Path
            char.name = Path(path).stem[:20]

        self.app.project.characters.append(char)
        self.app.project.save(PROJECTS_DIR)
        self._selected_char_id = char.id
        self._editor_char_id = None
        self._refresh_char_list()

    def _add_character(self):
        from makevid.core.project import Character
        char = Character(id=str(uuid.uuid4())[:8], name="")
        self.app.project.characters.append(char)
        self.app.project.save(PROJECTS_DIR)
        self._selected_char_id = char.id
        self._refresh_char_list()

    def _remove_char(self, char):
        self.app.project.characters = [c for c in self.app.project.characters if c.id != char.id]
        self._selected_char_id = None
        self.app.project.save(PROJECTS_DIR)
        self._refresh_char_list()
