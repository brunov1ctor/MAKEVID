"""Storyboard - Planilha de cenas do projeto."""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR


class StoryboardMixin:
    """Metodos de storyboard do StylePanel."""

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



