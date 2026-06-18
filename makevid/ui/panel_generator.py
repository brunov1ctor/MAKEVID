"""Panel Generator - Painel esquerdo para gerar clips (scrollable)."""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from pathlib import Path
from makevid.ui.theme import C
from makevid.ui.menus import _ToolTip


class GeneratorPanel:
    def __init__(self, parent, app):
        self.app = app
        self._ref_images = []
        self._img_thumb_refs = []

        import tkinter as tk

        # Container principal
        self.container = ctk.CTkFrame(parent, width=300, fg_color=C["panel"],
                                 border_width=0, corner_radius=0)
        self.container.pack(fill="both", expand=True, pady=4)
        self.container.pack_propagate(False)

        # Canvas para desenhar abas com borda integrada
        self._tab_canvas = tk.Canvas(self.container, height=28, bg=C["panel"],
                                     highlightthickness=0)
        self._tab_canvas.pack(fill="x")
        self._tab_canvas.bind("<Button-1>", self._on_tab_click)
        self._tab_canvas.bind("<Configure>", lambda e: self._draw_tabs())

        self._tab_var = "clip"
        self._tab_width = 148

        # Corpo (sem borda top - a borda top é desenhada pelo canvas)
        self._body_frame = tk.Frame(self.container, bg=C["panel"])
        self._body_frame.pack(fill="both", expand=True)

        # Bordas laterais e inferior com frames de 1px
        self._border_left = tk.Frame(self._body_frame, bg=C["gold"], width=1)
        self._border_left.pack(side="left", fill="y")
        self._border_right = tk.Frame(self._body_frame, bg=C["gold"], width=1)
        self._border_right.pack(side="right", fill="y")
        self._border_bottom = tk.Frame(self._body_frame, bg=C["gold"], height=1)
        self._border_bottom.pack(side="bottom", fill="x")

        # Conteudo interno
        self._body = ctk.CTkFrame(self._body_frame, fg_color=C["panel"],
                                  border_width=0, corner_radius=0)
        self._body.pack(fill="both", expand=True)

        # Scroll do clip
        self.scroll = ctk.CTkScrollableFrame(self._body, fg_color=C["panel"], corner_radius=0,
                                             scrollbar_button_color=C["gold"],
                                             scrollbar_button_hover_color="#dbb042")
        self.scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # Scroll da imagem (hidden)
        self._img_scroll = ctk.CTkScrollableFrame(self._body, fg_color=C["panel"], corner_radius=0,
                                                   scrollbar_button_color=C["cyan"],
                                                   scrollbar_button_hover_color="#00ffee")

        self._build(self.scroll)
        self._build_image_tab(self._img_scroll)

    def _build(self, p):
        # Mode
        ctk.CTkLabel(p, text="MODO", font=("Segoe UI", 10, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=10, pady=(10, 4))
        mf = ctk.CTkFrame(p, fg_color=C["card"], corner_radius=5, border_color=C["border"], border_width=1)
        mf.pack(fill="x", padx=10, pady=(0, 8))
        self.mode_var = ctk.StringVar(value="text")
        ctk.CTkRadioButton(mf, text="Texto", variable=self.mode_var, value="text",
                           command=self._on_mode, fg_color=C["gold"],
                           text_color=C["text"], font=("Segoe UI", 11)).pack(side="left", padx=10, pady=8)
        ctk.CTkRadioButton(mf, text="Img+Texto", variable=self.mode_var, value="image",
                           command=self._on_mode, fg_color=C["gold"],
                           text_color=C["text"], font=("Segoe UI", 11)).pack(side="left", padx=10, pady=8)
        ctk.CTkRadioButton(mf, text="Motion", variable=self.mode_var, value="motion",
                           command=self._on_mode, fg_color="#44cc88",
                           text_color=C["text"], font=("Segoe UI", 11)).pack(side="left", padx=10, pady=8)

        # Image frame (hidden)
        self.img_frame = ctk.CTkFrame(p, fg_color="transparent")
        row = ctk.CTkFrame(self.img_frame, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="+ Imagem", command=self._add_image, height=28,
                      fg_color=C["card"], border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], font=("Segoe UI", 10, "bold")).pack(side="left")
        ctk.CTkButton(row, text="Limpar", width=55, height=28, command=self._clear_images,
                      fg_color=C["card"], border_color=C["border"], border_width=1,
                      text_color=C["text3"], font=("Segoe UI", 9)).pack(side="left", padx=6)
        self.thumbs_frame = ctk.CTkFrame(self.img_frame, fg_color="transparent")
        self.thumbs_frame.pack(fill="x", pady=(6, 0))

        # ControlNet frame (hidden)
        self._controlnet_frame = ctk.CTkFrame(p, fg_color="transparent")
        cn_row = ctk.CTkFrame(self._controlnet_frame, fg_color="transparent")
        cn_row.pack(fill="x")
        ctk.CTkButton(cn_row, text="\U0001f3ac + Video Ref", command=self._add_motion_ref, height=28,
                      fg_color=C["card"], border_color="#44cc88", border_width=1,
                      text_color="#44cc88", font=("Segoe UI", 9, "bold")).pack(side="left")
        ctk.CTkButton(cn_row, text="Limpar", width=55, height=28, command=self._clear_motion_ref,
                      fg_color=C["card"], border_color=C["border"], border_width=1,
                      text_color=C["text3"], font=("Segoe UI", 9)).pack(side="left", padx=6)
        self._cn_mode_var = ctk.StringVar(value="pose")
        ctk.CTkRadioButton(cn_row, text="Pose", variable=self._cn_mode_var, value="pose",
                           fg_color="#44cc88", text_color=C["text"],
                           font=("Segoe UI", 9)).pack(side="left", padx=(10, 4))
        ctk.CTkRadioButton(cn_row, text="Depth", variable=self._cn_mode_var, value="depth",
                           fg_color="#44cc88", text_color=C["text"],
                           font=("Segoe UI", 9)).pack(side="left")
        self._cn_status = ctk.CTkLabel(self._controlnet_frame, text="",
                                        text_color=C["text3"], font=("Segoe UI", 8))
        self._cn_status.pack(anchor="w", pady=(4, 0))
        self._motion_ref_path = None

        # Prompt
        self._prompt_label = ctk.CTkLabel(p, text="PROMPT", font=("Segoe UI", 11, "bold"),
                                          text_color=C["text"])
        self._prompt_label.pack(anchor="w", padx=10, pady=(4, 4))
        self.prompt_box = ctk.CTkTextbox(p, height=100, fg_color=C["input"], border_color=C["gold"],
                                         border_width=2, text_color=C["cyan"], font=("Consolas", 11, "bold"),
                                         corner_radius=8)
        self.prompt_box.pack(fill="x", padx=10)

        # Continuidade
        self.continuity_var = ctk.BooleanVar(value=True)
        cont_frame = ctk.CTkFrame(p, fg_color="transparent")
        cont_frame.pack(fill="x", padx=10, pady=(8, 0))
        cont_cb = ctk.CTkCheckBox(cont_frame, text="Continuar do anterior",
                                  variable=self.continuity_var, fg_color=C["gold"],
                                  text_color=C["text"], font=("Segoe UI", 10),
                                  hover_color="#dbb042", checkmark_color="#0a0a0f")
        cont_cb.pack(side="left")
        _ToolTip(cont_cb, "Usa o ultimo frame do clip anterior como referencia.\nGarante continuidade visual entre cenas (mesma cabana, mesma iluminacao, etc)")

        # Negative
        neg_lbl = ctk.CTkLabel(p, text="NEGATIVE PROMPT", font=("Segoe UI", 9, "bold"),
                     text_color=C["text3"])
        neg_lbl.pack(anchor="w", padx=10, pady=(10, 3))
        _ToolTip(neg_lbl, "Descreva o que voce NAO quer no video.\nO modelo tenta evitar esses elementos")
        self.neg_box = ctk.CTkTextbox(p, height=40, fg_color=C["input"], border_color=C["border"],
                                      border_width=2, text_color=C["text3"], font=("Consolas", 11, "bold"),
                                      corner_radius=8)
        self.neg_box.pack(fill="x", padx=10)
        self.neg_box.insert("0.0", "blurry, low quality, distorted, watermark, static")

        # Params
        ctk.CTkLabel(p, text="PARAMETROS", font=("Segoe UI", 10, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=10, pady=(12, 4))
        pf = ctk.CTkFrame(p, fg_color=C["card"], corner_radius=5, border_color=C["border"], border_width=1)
        pf.pack(fill="x", padx=10)

        r1 = ctk.CTkFrame(pf, fg_color="transparent")
        r1.pack(fill="x", padx=8, pady=(8, 3))
        self.dur_var = self._entry(r1, "Duracao", "5", 45,
                                   tooltip="Duracao do video em segundos")
        self.steps_var = self._entry(r1, "Steps", "30", 45,
                                    tooltip="Numero de passos de inferencia. Mais steps = mais qualidade, mais lento")

        r1b = ctk.CTkFrame(pf, fg_color="transparent")
        r1b.pack(fill="x", padx=8, pady=(0, 3))
        self.guidance_var = self._entry(r1b, "CFG", "5.0", 55,
                                       tooltip="Classifier-Free Guidance. Controla o quanto o modelo segue o prompt.\nBaixo (1-3): mais criativo/aleatorio\nMedio (4-7): equilibrado\nAlto (8+): segue rigidamente o texto")

        r2 = ctk.CTkFrame(pf, fg_color="transparent")
        r2.pack(fill="x", padx=8, pady=(0, 4))
        self.seed_var = self._entry(r2, "Seed", "", 65, ph="random",
                                   tooltip="Semente para reproducibilidade. Mesma seed + mesmo prompt = mesmo resultado")

        # Resolucao
        r3 = ctk.CTkFrame(pf, fg_color="transparent")
        r3.pack(fill="x", padx=8, pady=(0, 8))
        res_lbl = ctk.CTkLabel(r3, text="Resolucao", text_color=C["text2"], font=("Segoe UI", 9, "bold"))
        res_lbl.pack(side="left", padx=(0, 5))
        _ToolTip(res_lbl, "Resolucao do video gerado.\nMaior resolucao = mais VRAM e mais tempo")
        self.res_var = ctk.StringVar(value="480p")
        self._res_options = {
            "480p (832x480)": (832, 480),
            "720p (1280x720)": (1280, 720),
            "1080p (1920x1080)": (1920, 1080),
            "4K (3840x2160)": (3840, 2160),
        }
        ctk.CTkOptionMenu(r3, variable=self.res_var,
                          values=list(self._res_options.keys()),
                          fg_color=C["card"], button_color=C["gold"],
                          button_hover_color="#ffd700",
                          text_color=C["text"], font=("Segoe UI", 9),
                          dropdown_fg_color=C["card"],
                          dropdown_hover_color=C["card_hover"],
                          dropdown_text_color=C["text"],
                          width=160, height=24,
                          command=self._on_res_change).pack(side="left")
        self.res_var.set("480p (832x480)")

        self._vram_label = ctk.CTkLabel(pf, text="~12 GB VRAM", text_color=C["text3"],
                                         font=("Consolas", 8))
        self._vram_label.pack(anchor="w", padx=8, pady=(0, 6))

        # Atualizar label quando engine mudar
        self.app.engine_var.trace_add("write", lambda *_: self._on_res_change(self.res_var.get()))

        # Generate button - neon glow
        self.gen_btn = ctk.CTkButton(p, text="GERAR CLIP", command=self._generate, height=44,
                                     font=("Segoe UI", 14, "bold"), fg_color=C["gold"],
                                     hover_color="#ffd700", text_color="#0a0a0f",
                                     border_color="#ffd700", border_width=2, corner_radius=6)
        self.gen_btn.pack(fill="x", padx=10, pady=(14, 2))

        # Engine label abaixo do botao
        self._engine_info = ctk.CTkLabel(p, text="", text_color=C["text3"], font=("Consolas", 9))
        self._engine_info.pack(anchor="w", padx=12, pady=(0, 4))
        self._update_engine_info()
        self.app.engine_var.trace_add("write", lambda *_: self._update_engine_info())

        # Progress
        self.progress = ctk.CTkProgressBar(p, progress_color=C["cyan"], fg_color=C["card"], height=6, corner_radius=3)
        self.progress.pack(fill="x", padx=10, pady=(0, 4))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(p, text="Pronto", text_color=C["text3"], font=("Segoe UI", 11))
        self.status_label.pack(anchor="w", padx=10, pady=(0, 10))

    def _entry(self, parent, label, default, width, ph=None, tooltip=None):
        lbl = ctk.CTkLabel(parent, text=label, text_color=C["text2"], font=("Segoe UI", 9, "bold"))
        lbl.pack(side="left", padx=(0, 3))
        if tooltip:
            _ToolTip(lbl, tooltip)
        var = ctk.StringVar(value=default)
        e = ctk.CTkEntry(parent, textvariable=var, width=width, fg_color=C["input"],
                         border_color=C["border"], border_width=2, text_color=C["cyan"],
                         font=("Consolas", 11, "bold"), corner_radius=8)
        if ph:
            e.configure(placeholder_text=ph)
        e.pack(side="left", padx=(0, 10))
        return var

    # --- Image ---

    def _on_mode(self):
        mode = self.mode_var.get()
        if mode == "image":
            self.img_frame.pack(fill="x", padx=10, pady=(0, 6), before=self._prompt_label)
            self._controlnet_frame.pack_forget()
        elif mode == "motion":
            self.img_frame.pack_forget()
            self._controlnet_frame.pack(fill="x", padx=10, pady=(0, 6), before=self._prompt_label)
        else:
            self.img_frame.pack_forget()
            self._controlnet_frame.pack_forget()

    def _update_engine_info(self):
        engine = self.app.engine_var.get()
        self._engine_info.configure(text=f"⚡ {engine}")

    def _on_res_change(self, value):
        """Atualiza label de VRAM/tempo estimado."""
        engine = self.app.engine_var.get() if hasattr(self.app, 'engine_var') else ""
        if engine == "Local (CPU)":
            self._vram_label.configure(text="CPU: 320x192 fixo, ~5-20min")
        else:
            vram_map = {
                "480p (832x480)": "~12 GB VRAM",
                "720p (1280x720)": "~24 GB VRAM",
                "1080p (1920x1080)": "~32 GB VRAM (lento)",
                "4K (3840x2160)": "~64+ GB VRAM (muito lento)",
            }
            self._vram_label.configure(text=vram_map.get(value, ""))

    def _get_resolution(self):
        """Retorna (width, height) baseado no preset selecionado."""
        return self._res_options.get(self.res_var.get(), (832, 480))

    def _add_image(self):
        paths = filedialog.askopenfilenames(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")])
        for p in paths:
            if p not in self._ref_images:
                self._ref_images.append(p)
        self._refresh_thumbs()

    def _clear_images(self):
        self._ref_images.clear()
        self._img_thumb_refs.clear()
        self._refresh_thumbs()

    def _refresh_thumbs(self):
        for w in self.thumbs_frame.winfo_children():
            w.destroy()
        self._img_thumb_refs.clear()

        if not self._ref_images:
            ctk.CTkLabel(self.thumbs_frame, text="Nenhuma imagem", text_color=C["text3"],
                         font=("Segoe UI", 9)).pack(side="left")
            return

        for path in self._ref_images:
            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((44, 44))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(44, 44))
                self._img_thumb_refs.append(ctk_img)
                item = ctk.CTkFrame(self.thumbs_frame, fg_color=C["card"],
                                    border_color=C["cyan"], border_width=1, corner_radius=4)
                item.pack(side="left", padx=2)
                lbl = ctk.CTkLabel(item, image=ctk_img, text="")
                lbl.pack(padx=2, pady=2)
                ctk.CTkButton(item, text="x", width=14, height=14, corner_radius=7,
                              fg_color="#ff4444", hover_color="#ff6666",
                              text_color="#ffffff", font=("", 8),
                              command=lambda p=path: self._remove_img(p)).place(relx=1.0, rely=0, anchor="ne")
            except Exception:
                pass

        ctk.CTkLabel(self.thumbs_frame, text=f" {len(self._ref_images)}",
                     text_color=C["cyan"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)

    def _remove_img(self, path):
        if path in self._ref_images:
            self._ref_images.remove(path)
            self._refresh_thumbs()

    # --- ControlNet (Motion Reference) ---

    def _add_motion_ref(self):
        """Importa video de referencia de movimento."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.webm")])
        if path:
            self._motion_ref_path = path
            from pathlib import Path
            name = Path(path).stem[:25]
            self._cn_status.configure(text=f"\u2713 {name}", text_color="#44cc88")

    def _clear_motion_ref(self):
        self._motion_ref_path = None
        self._cn_status.configure(text="", text_color=C["text3"])

    # --- Generation ---

    def _generate(self):
        prompt = self.prompt_box.get("0.0", "end").strip()
        duration = float(self.dur_var.get())

        # Prompt vazio: cria clip vazio na timeline
        if not prompt:
            clip = self.app.project.add_clip(prompt="", position=len(self.app.project.clips))
            clip.duration = duration
            from makevid.config import PROJECTS_DIR
            self.app.project.save(PROJECTS_DIR)
            self.app.timeline.draw()
            return

        self.gen_btn.configure(state="disabled")
        self.status_label.configure(text="Gerando...", text_color=C["gold"])
        self.progress.set(0.15)

        # Capturar ref_images ANTES de limpar
        ref = list(self._ref_images) if self.mode_var.get() == "image" and self._ref_images else None
        w, h = self._get_resolution()

        # Continuidade: pegar ultimo frame do clip anterior
        if self.continuity_var.get() and not ref:
            last_frame_path = self._get_last_frame()
            if last_frame_path:
                ref = [last_frame_path]

        # Limpar prompt e imagens imediatamente ao iniciar
        self.prompt_box.delete("0.0", "end")
        self.seed_var.set("")
        self._ref_images.clear()
        self._refresh_thumbs()

        self.app.request_generation(
            prompt=prompt,
            duration=float(self.dur_var.get()),
            steps=int(self.steps_var.get()),
            guidance=float(self.guidance_var.get()),
            seed=int(self.seed_var.get()) if self.seed_var.get().strip() else None,
            width=w,
            height=h,
            negative=self.neg_box.get("0.0", "end").strip(),
            ref_images=ref,
            motion_ref_path=self._motion_ref_path if self.mode_var.get() == "motion" else None,
            motion_mode=self._cn_mode_var.get() if self.mode_var.get() == "motion" else "pose",
        )

    def _get_last_frame(self) -> str:
        """Extrai ultimo frame do ultimo clip done na timeline como imagem temp."""
        from pathlib import Path
        import tempfile

        clips = sorted(self.app.project.clips, key=lambda c: c.position)
        # Pegar ultimo clip com video pronto
        last_done = None
        for c in reversed(clips):
            if c.status == "done" and c.video_path and Path(c.video_path).exists():
                last_done = c
                break

        if not last_done:
            return None

        try:
            import cv2
            cap = cv2.VideoCapture(str(last_done.video_path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total - 1)
            ret, frame = cap.read()
            cap.release()

            if ret:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                cv2.imwrite(tmp.name, frame)
                return tmp.name
        except Exception:
            pass
        return None

    def on_gen_progress(self, msg):
        self.status_label.configure(text=msg, text_color=C["gold"])
        # Extrair progresso do step se disponivel ("Step 3/8")
        if "Step " in msg and "/" in msg:
            try:
                parts = msg.split("Step ")[1].split("/")
                current = int(parts[0])
                total = int(parts[1].split(" ")[0])
                self.progress.set(current / total)
            except Exception:
                self.progress.set(0.5)
        elif "Salvando" in msg:
            self.progress.set(0.9)
        else:
            self.progress.set(0.15)

    def on_gen_done(self, clip):
        self.gen_btn.configure(state="normal")
        self.progress.set(0)
        self.status_label.configure(text=f"Pronto! {clip.duration:.1f}s", text_color=C["cyan"])

    def _reset_fields(self):
        """Limpa campos para proximo clip."""
        self.prompt_box.delete("0.0", "end")
        self.seed_var.set("")
        self.progress.set(0)
        self.status_label.configure(text="Pronto", text_color=C["text3"])

    def on_gen_error(self, error):
        self.gen_btn.configure(state="normal")
        self.progress.set(0)
        self.status_label.configure(text=f"Erro: {error[:60]}", text_color=C["red"])

    def set_clip_data(self, clip):
        self.prompt_box.delete("0.0", "end")
        self.prompt_box.insert("0.0", clip.prompt)
        self.dur_var.set(str(clip.duration))
        self.seed_var.set(str(clip.seed) if clip.seed else "")

        # Restaurar imagem de referencia se existir
        self._ref_images.clear()
        if clip.image_ref_path and Path(clip.image_ref_path).exists():
            self._ref_images.append(clip.image_ref_path)
            self.mode_var.set("image")
            self._on_mode()
        else:
            self.mode_var.set("text")
            self._on_mode()
        self._refresh_thumbs()

    # --- TABS ---

    def _switch_tab(self, tab):
        """Alterna entre aba Clip e Imagem."""
        if tab == self._tab_var:
            return
        self._tab_var = tab
        if tab == "clip":
            self._img_scroll.pack_forget()
            self.scroll.pack(fill="both", expand=True, padx=2, pady=2)
        else:
            self.scroll.pack_forget()
            self._img_scroll.pack(in_=self._body, fill="both", expand=True, padx=2, pady=2)
        self._draw_tabs()

    def _on_tab_click(self, event):
        """Detecta click na area das abas."""
        x = event.x
        if x < self._tab_width:
            self._switch_tab("clip")
        elif x < self._tab_width * 2:
            self._switch_tab("image")

    def _draw_tabs(self, event=None):
        """Desenha abas estilo Excel com borda integrada."""
        c = self._tab_canvas
        c.delete("all")
        w = c.winfo_width() or 300
        h = 28
        tw = self._tab_width
        gold = C["gold"]
        panel = C["panel"]
        card = C["card"]
        bw = 2  # espessura da borda

        if self._tab_var == "clip":
            # Fundo aba ativa (CLIP)
            c.create_rectangle(bw, bw, tw - 1, h, fill=panel, outline="")
            # Fundo aba inativa (IMAGEM)
            c.create_rectangle(tw + 1, h - 1 - bw, tw * 2 - 1, h, fill=card, outline="")
            c.create_rectangle(tw + 1, bw + 4, tw * 2 - 1, h - bw, fill=card, outline="")

            # Borda aba ativa: esquerda, topo, direita
            c.create_line(0, h, 0, 0, fill=gold, width=bw)
            c.create_line(0, 1, tw, 1, fill=gold, width=bw)
            c.create_line(tw, 0, tw, h, fill=gold, width=bw)

            # Linha base: passa embaixo da aba inativa ate o fim
            c.create_line(tw, h - 1, w, h - 1, fill=gold, width=bw)

            # Borda direita do painel
            c.create_line(w - 1, h, w - 1, h - 1, fill=gold, width=bw)

            # Texto
            c.create_text(tw // 2, h // 2, text="GERAR CLIP",
                          fill=gold, font=("Segoe UI", 9, "bold"))
            c.create_text(tw + tw // 2, h // 2, text="GERAR IMAGEM",
                          fill=C["text3"], font=("Segoe UI", 9, "bold"))
        else:
            # Fundo aba inativa (CLIP)
            c.create_rectangle(1, bw + 4, tw - 1, h - bw, fill=card, outline="")
            # Fundo aba ativa (IMAGEM)
            c.create_rectangle(tw + bw, bw, tw * 2 - bw, h, fill=panel, outline="")

            # Linha base: passa embaixo da aba inativa
            c.create_line(0, h - 1, tw, h - 1, fill=gold, width=bw)

            # Borda esquerda do painel (so ate a linha base)
            c.create_line(0, h, 0, h - 1, fill=gold, width=bw)

            # Borda aba ativa: esquerda, topo, direita
            c.create_line(tw, h, tw, 0, fill=gold, width=bw)
            c.create_line(tw, 1, tw * 2, 1, fill=gold, width=bw)
            c.create_line(tw * 2, 0, tw * 2, h, fill=gold, width=bw)

            # Linha base apos aba ativa ate o fim
            if tw * 2 < w:
                c.create_line(tw * 2, h - 1, w, h - 1, fill=gold, width=bw)

            # Borda direita do painel (so ate a linha base)
            c.create_line(w - 1, h, w - 1, h - 1, fill=gold, width=bw)

            # Texto
            c.create_text(tw // 2, h // 2, text="GERAR CLIP",
                          fill=C["text3"], font=("Segoe UI", 9, "bold"))
            c.create_text(tw + tw // 2, h // 2, text="GERAR IMAGEM",
                          fill=C["cyan"], font=("Segoe UI", 9, "bold"))

    # --- IMAGE GENERATION TAB ---

    def _build_image_tab(self, p):
        """Constroi aba de geracao de imagem - configs no painel, resultado no display."""
        # Modo
        # Modo fixo texto (FLUX nao suporta img2img)
        self._img_mode_var = ctk.StringVar(value="text")
        self._img_ref_path = None

        self._img_prompt_label = ctk.CTkLabel(p, text="PROMPT", font=("Segoe UI", 11, "bold"),
                                              text_color=C["text"])
        self._img_prompt_label.pack(anchor="w", padx=10, pady=(4, 4))
        self._img_prompt_box = ctk.CTkTextbox(p, height=80, fg_color=C["input"], border_color=C["cyan"],
                                              border_width=2, text_color=C["cyan"], font=("Consolas", 11, "bold"),
                                              corner_radius=8)
        self._img_prompt_box.pack(fill="x", padx=10)

        # Negative
        ctk.CTkLabel(p, text="NEGATIVE", font=("Segoe UI", 9, "bold"),
                     text_color=C["text3"]).pack(anchor="w", padx=10, pady=(8, 3))
        self._img_neg_box = ctk.CTkTextbox(p, height=30, fg_color=C["input"], border_color=C["border"],
                                            border_width=2, text_color=C["text3"], font=("Consolas", 11, "bold"),
                                            corner_radius=8)
        self._img_neg_box.pack(fill="x", padx=10)
        self._img_neg_box.insert("0.0", "blurry, low quality, ugly, deformed")

        # Modelo

        # Duracao
        dur_frame = ctk.CTkFrame(p, fg_color="transparent")
        dur_frame.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(dur_frame, text="Duracao(s)", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(side="left")
        self._img_dur_var = ctk.StringVar(value="5")
        ctk.CTkEntry(dur_frame, textvariable=self._img_dur_var, width=45, fg_color=C["input"],
                     border_color=C["border"], border_width=2, text_color=C["cyan"],
                     font=("Consolas", 11, "bold"), corner_radius=8).pack(side="left", padx=(6, 0))

        # Botao gerar
        self._img_gen_btn = ctk.CTkButton(p, text="GERAR IMAGEM", command=self._generate_image, height=40,
                                          font=("Segoe UI", 13, "bold"), fg_color=C["cyan"],
                                          hover_color="#00ffee", text_color="#0a0a0f",
                                          border_color="#00ffee", border_width=2, corner_radius=6)
        self._img_gen_btn.pack(fill="x", padx=10, pady=(14, 4))

        # Progress bar
        self._img_progress = ctk.CTkProgressBar(p, progress_color=C["cyan"], fg_color=C["card"], height=6, corner_radius=3)
        self._img_progress.pack(fill="x", padx=10, pady=(0, 4))
        self._img_progress.set(0)

        # Status
        self._img_status = ctk.CTkLabel(p, text="Pronto", text_color=C["text3"], font=("Segoe UI", 10))
        self._img_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _generate_image(self):
        """Gera imagem - mostra no display + salva em Minhas Imagens + adiciona na timeline."""
        import threading
        prompt = self._img_prompt_box.get("0.0", "end").strip()
        if not prompt:
            return

        self._img_gen_btn.configure(state="disabled")
        self._img_status.configure(text="Gerando imagem...", text_color=C["gold"])
        self._img_progress.set(0.15)

        # Animacao de progress
        self._img_progress_job = None
        def _animate_progress():
            try:
                cur = self._img_progress.get()
                if cur < 0.85:
                    self._img_progress.set(cur + 0.02)
                self._img_progress_job = self.app.after(200, _animate_progress)
            except Exception:
                pass
        _animate_progress()

        engine = self.app.engine_var.get()
        duration = float(self._img_dur_var.get())

        def run():
            try:
                if engine == "HuggingFace API":
                    img = self._gen_img_hf(prompt, False)
                else:
                    img = self._gen_img_local(prompt, False, engine)

                if img:
                    self._generated_img = img
                    def on_done():
                        if self._img_progress_job:
                            self.app.after_cancel(self._img_progress_job)
                        self._img_progress.set(1.0)
                        # Mostrar no display
                        try:
                            pp = self.app.preview_panel
                            display_img, w, h = pp._fit_image(img)
                            pp._preview_img_ref = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(w, h))
                            pp.preview_label.configure(image=pp._preview_img_ref, text="", compound="center")
                            pp.clip_info.configure(text=f"Imagem gerada | {img.size[0]}x{img.size[1]} | {engine}")
                        except Exception:
                            pass
                        # Salvar + timeline
                        self._save_and_add_to_timeline(img, prompt, duration)
                        self._img_status.configure(text=f"Pronto! {duration:.0f}s na timeline", text_color=C["cyan"])
                        self._img_gen_btn.configure(state="normal")
                        self._img_prompt_box.delete("0.0", "end")
                        self.app.after(1500, lambda: self._img_progress.set(0))
                        # Habilitar play no preview
                        clips = sorted(self.app.project.clips, key=lambda c: c.position)
                        if clips:
                            last_clip = clips[-1]
                            self.app.timeline.selected_clip_id = last_clip.id
                            self.app.preview_panel.show_clip(last_clip, len(clips))
                    self.app.after(0, on_done)
                else:
                    self.app.after(0, lambda: [
                        self._img_progress_job and self.app.after_cancel(self._img_progress_job),
                        self._img_progress.set(0),
                        self._img_status.configure(text="Falha", text_color="#ff4444"),
                        self._img_gen_btn.configure(state="normal"),
                    ])
            except Exception as e:
                err = str(e)
                def on_error():
                    if self._img_progress_job:
                        try:
                            self.app.after_cancel(self._img_progress_job)
                        except Exception:
                            pass
                        self._img_progress_job = None
                    try:
                        self._img_progress.set(0)
                    except Exception:
                        pass
                    self._show_token_prompt(auto_generate=True)
                    try:
                        self._img_status.configure(text=f"Erro: {err[:50]}", text_color="#ff4444")
                        self._img_gen_btn.configure(state="normal")
                    except Exception:
                        pass
                self.app.after(0, on_error)

        threading.Thread(target=run, daemon=True).start()

    def _save_and_add_to_timeline(self, img, prompt, duration):
        """Salva imagem e adiciona como clip estatico na timeline."""
        from makevid.core.video import frames_to_mp4
        from makevid.config import OUTPUTS_DIR, PROJECTS_DIR
        import time as _time

        filename = f"img_{int(_time.time())}"
        out_dir = OUTPUTS_DIR / self.app.project.id
        out_dir.mkdir(parents=True, exist_ok=True)
        img_path = out_dir / f"{filename}.png"
        img.save(str(img_path))

        img_resized = img.resize(
            (self.app.project.output_width, self.app.project.output_height), Image.LANCZOS)
        fps = self.app.project.output_fps or 16
        frames = [img_resized] * int(duration * fps)
        out_path = out_dir / f"{filename}.mp4"
        frames_to_mp4(frames, out_path, fps=fps)

        clip = self.app.project.add_clip(prompt=f"[IMG] {prompt}",
                                         position=len(self.app.project.clips))
        clip.video_path = str(out_path)
        clip.duration = duration
        clip.status = "done"
        clip.image_ref_path = str(img_path)
        self.app.project.save(PROJECTS_DIR)
        self.app.timeline.invalidate_thumbnail(clip.id)
        self.app.timeline.draw()

    def _show_token_prompt(self, auto_generate=False):
        """Mostra campo inline no painel para inserir HuggingFace token."""
        import os
        from makevid.core.hf_api import _get_token

        # Remover prompt anterior se existir
        if hasattr(self, '_token_frame') and self._token_frame:
            try:
                self._token_frame.destroy()
            except Exception:
                pass

        # Garantir que o painel gerador esta visivel
        if not self.container.winfo_ismapped():
            # Fechar fx_panel se aberto e restaurar o gerador
            if self.app.timeline.fx_panel._visible:
                self.app.timeline.fx_panel.hide()

        # Inserir inline no scroll correto (depende da aba ativa)
        parent_scroll = self._img_scroll if self._tab_var == "image" else self.scroll
        self._token_frame = ctk.CTkFrame(parent_scroll, fg_color=C["card"], corner_radius=6,
                                          border_color=C["gold"], border_width=1)
        self._token_frame.pack(fill="x", padx=6, pady=(4, 8))

        ctk.CTkLabel(self._token_frame, text="TOKEN HUGGINGFACE", font=("Segoe UI", 10, "bold"),
                     text_color=C["gold"]).pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(self._token_frame, text="Crie em: huggingface.co/settings/tokens",
                     text_color=C["text3"], font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 4))

        token_var = ctk.StringVar(value=os.environ.get("HF_TOKEN") or "")
        entry = ctk.CTkEntry(self._token_frame, textvariable=token_var, fg_color=C["input"],
                     border_color=C["gold"], border_width=1, text_color=C["text"],
                     font=("Consolas", 10), placeholder_text="hf_...")
        entry.pack(fill="x", padx=10, pady=(0, 6))
        entry.after(10, entry.focus_force)

        btn_frame = ctk.CTkFrame(self._token_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        def save_token():
            t = token_var.get().strip()
            if t:
                os.environ["HF_TOKEN"] = t
                self._img_status.configure(text="Token salvo!", text_color=C["cyan"])
            self._token_frame.destroy()
            self._token_frame = None
            if auto_generate:
                self._generate_image()

        def cancel():
            self._token_frame.destroy()
            self._token_frame = None

        ctk.CTkButton(btn_frame, text="SALVAR", command=save_token, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700", width=80).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_frame, text="X", command=cancel, height=26, width=28,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010").pack(side="left")
        entry.bind("<Return>", lambda e: save_token())

        # Scroll para mostrar o campo
        try:
            parent_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _show_freesound_prompt(self, on_saved=None):
        """Mostra campo inline para inserir Freesound API key (mesmo padrao do HF token)."""
        import os

        if hasattr(self, '_fs_token_frame') and self._fs_token_frame:
            try:
                self._fs_token_frame.destroy()
            except Exception:
                pass

        # Garantir que o painel gerador esta visivel
        if not self.container.winfo_ismapped():
            if self.app.timeline.fx_panel._visible:
                self.app.timeline.fx_panel.hide()
            else:
                self.container.pack(side="left", fill="y", padx=(0, 4), pady=4)

        # Garantir aba clip
        if self._tab_var != "clip":
            self._switch_tab("clip")

        self._fs_token_frame = ctk.CTkFrame(self.scroll, fg_color=C["card"], corner_radius=6,
                                             border_color=C["gold"], border_width=1)
        self._fs_token_frame.pack(fill="x", padx=6, pady=(4, 8))

        ctk.CTkLabel(self._fs_token_frame, text="FREESOUND API KEY", font=("Segoe UI", 10, "bold"),
                     text_color=C["gold"]).pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(self._fs_token_frame, text="Crie em: freesound.org/apiv2/apply",
                     text_color=C["text3"], font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 4))

        key_var = ctk.StringVar(value=os.environ.get("FREESOUND_API_KEY", ""))
        entry = ctk.CTkEntry(self._fs_token_frame, textvariable=key_var, fg_color=C["input"],
                     border_color=C["gold"], border_width=1, text_color=C["text"],
                     font=("Consolas", 10), placeholder_text="sua_api_key_aqui")
        entry.pack(fill="x", padx=10, pady=(0, 6))
        entry.bind("<Button-1>", lambda e: entry.after(1, entry.focus_force))
        entry.after(100, entry.focus_force)

        btn_frame = ctk.CTkFrame(self._fs_token_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        def save_key():
            k = key_var.get().strip()
            if k:
                os.environ["FREESOUND_API_KEY"] = k
                from makevid.core import freesound_provider
                freesound_provider.FREESOUND_API_KEY = k
                self.status_label.configure(text="Key salva!", text_color=C["cyan"])
            self._fs_token_frame.destroy()
            self._fs_token_frame = None
            if on_saved and k:
                on_saved()

        def cancel():
            self._fs_token_frame.destroy()
            self._fs_token_frame = None

        ctk.CTkButton(btn_frame, text="SALVAR", command=save_key, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700", width=80).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_frame, text="X", command=cancel, height=26, width=28,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010").pack(side="left")
        entry.bind("<Return>", lambda e: save_key())

        try:
            self.scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _gen_img_hf(self, prompt, use_img_ref):
        """Gera imagem via HuggingFace API."""
        import requests
        import os
        import io
        import base64

        model_id = "black-forest-labs/FLUX.1-schnell"
        from makevid.core.hf_api import _get_token
        token = os.environ.get("HF_TOKEN") or _get_token()
        url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
        headers = {"Authorization": f"Bearer {token}"}

        if use_img_ref:
            img_ref = Image.open(self._img_ref_path).convert("RGB")
            img_ref.thumbnail((768, 768))
            buf = io.BytesIO()
            img_ref.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            payload = {"inputs": prompt, "parameters": {"image": img_b64, "seed": __import__('random').randint(0, 2**32)}}
        else:
            payload = {"inputs": prompt, "parameters": {"seed": __import__('random').randint(0, 2**32)}}

        import logging
        logging.getLogger("gen").info(f"[HF IMG] {model_id} | {prompt[:50]}")
        r = requests.post(url, headers=headers, json=payload, timeout=120)

        if r.status_code != 200:
            logging.getLogger("gen").error(f"[HF IMG] {r.status_code} | {r.text[:80]}")
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            from io import BytesIO
            return Image.open(BytesIO(r.content))
        else:
            error = r.text[:80] if r.text else f"Status {r.status_code}"
            raise Exception(error)

    def _gen_img_local(self, prompt, use_img_ref, engine):
        """Gera imagem localmente via diffusers (GPU/CPU)."""
        import torch
        from diffusers import StableDiffusionPipeline
        from makevid.config import MODELS_DIR

        if not torch.cuda.is_available() and "GPU" in engine:
            raise Exception("GPU nao disponivel")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        pipe = StableDiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=dtype,
            cache_dir=str(MODELS_DIR),
        )
        if device == "cuda":
            pipe.enable_model_cpu_offload()
        else:
            pipe.to(device)

        neg = self._img_neg_box.get("0.0", "end").strip()
        result = pipe(prompt=prompt, negative_prompt=neg, num_inference_steps=20)
        return result.images[0]
