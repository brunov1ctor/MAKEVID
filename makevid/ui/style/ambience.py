"""Ambience - Imagens de referencia visual."""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from PIL import Image
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR


class AmbienceMixin:
    """Metodos de ambientacao do StylePanel."""

    def _build_ambience(self):
        from makevid.ui.menus import _ToolTip
        from makevid.config import AMBIENCE_REFS_DIR
        p = self._content

        # === HEADER ===
        top = ctk.CTkFrame(p, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 2))

        title_lbl = ctk.CTkLabel(top, text="\U0001f5bc AMBIENTACAO", font=("Segoe UI", 13, "bold"),
                     text_color="#44cc88")
        title_lbl.pack(side="left")
        _ToolTip(title_lbl,
            "COMO FUNCIONA\n"
            "\n"
            "1. Jogue imagens de referencia nesta pasta\n"
            "   (vilas, castelos, florestas, interiores, etc.)\n"
            "\n"
            "2. Quando voce gerar qualquer video (pelo Storyboard\n"
            "   ou pelo gerador direto), o sistema AUTOMATICAMENTE\n"
            "   seleciona a imagem que mais combina com o prompt\n"
            "   da cena e usa como referencia visual.\n"
            "\n"
            "3. Resultado: todos os videos saem com a mesma\n"
            "   estetica visual das suas imagens de referencia.\n"
            "\n"
            "EXEMPLO:\n"
            "- Voce joga 30 imagens realistas de um mundo medieval\n"
            "- No storyboard: 'rei sentado no trono' -> sistema pega\n"
            "  automaticamente uma imagem de castelo da pasta\n"
            "- 'fuga pela floresta escura' -> pega imagem de floresta\n"
            "- 'vila ao amanhecer' -> pega imagem de vila\n"
            "\n"
            "Tudo sai coerente sem voce selecionar nada manualmente!")

        # Botoes
        btn_row = ctk.CTkFrame(top, fg_color="transparent")
        btn_row.pack(side="right")

        open_dir_btn = ctk.CTkButton(btn_row, text="\U0001f4c2", width=28, height=26,
                      font=("Segoe UI", 12), fg_color=C["card"],
                      border_color=C["border"], border_width=1,
                      text_color=C["text2"], hover_color=C["card_hover"],
                      corner_radius=4, command=self._amb_open_folder)
        open_dir_btn.pack(side="left", padx=(0, 4))
        _ToolTip(open_dir_btn, "Abrir pasta no Explorer.\nVoce pode arrastar imagens direto para la.\n\nCaminho: " + str(AMBIENCE_REFS_DIR))

        add_folder_btn = ctk.CTkButton(btn_row, text="+ PASTA", width=70, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color="#44cc88", border_width=1,
                      text_color="#44cc88", hover_color="#0a2a1a",
                      corner_radius=4, command=self._amb_add_folder)
        add_folder_btn.pack(side="left", padx=(0, 4))
        _ToolTip(add_folder_btn, "Importar TODAS as imagens de uma pasta de uma vez.\n\nEx: selecione uma pasta com 30 fotos e todas\nserao copiadas para o diretorio de ambientacao.")

        add_imgs_btn = ctk.CTkButton(btn_row, text="+ IMAGENS", width=90, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color="#44cc88",
                      text_color="#0a0a0f", hover_color="#66ffaa",
                      corner_radius=4, command=self._amb_add_images)
        add_imgs_btn.pack(side="left")
        _ToolTip(add_imgs_btn, "Selecionar imagens individuais (PNG, JPG, WEBP).\n\nDica: misture cenarios variados do mesmo universo.\nVilas, castelos, florestas, interiores - tudo junto.\nO sistema escolhe a melhor para cada cena.")

        # === INFO BOX ===
        info = ctk.CTkFrame(p, fg_color=C["card"], corner_radius=4,
                            border_color="#44cc88", border_width=1)
        info.pack(fill="x", padx=10, pady=(6, 6))

        info_text = (
            "\u2713 AUTOMATICO: ao gerar video, o sistema analisa o prompt de cada cena "
            "e seleciona a imagem mais parecida como referencia visual.\n"
            "\u2713 Quanto mais imagens variadas, melhor a cobertura de cenarios.\n"
            "\u2713 Funciona com Storyboard (todas as cenas) e gerador individual."
        )
        ctk.CTkLabel(info, text=info_text,
                     text_color=C["text2"], font=("Segoe UI", 9),
                     wraplength=700, justify="left").pack(padx=10, pady=8)

        # === CONTAGEM + STATUS ===
        images = self._amb_get_images()
        status_row = ctk.CTkFrame(p, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=(0, 4))

        self._amb_count_label = ctk.CTkLabel(status_row, text=f"{len(images)} imagens",
                     text_color="#44cc88", font=("Segoe UI", 10, "bold"))
        self._amb_count_label.pack(side="left")
        _ToolTip(self._amb_count_label,
            "Total de imagens na pasta.\n"
            "\n"
            "Recomendacoes:\n"
            "  3-10  imagens: funciona, mas cobertura limitada\n"
            "  10-30 imagens: bom para um universo\n"
            "  30-50 imagens: ideal, cobre muitos cenarios\n"
            "  50+   imagens: excelente variedade")

        # Indicador de estado
        if images:
            ctk.CTkLabel(status_row, text=" | \u26a1 Ativo (auto-match ligado)",
                         text_color=C["cyan"], font=("Segoe UI", 9)).pack(side="left")
        else:
            ctk.CTkLabel(status_row, text=" | Inativo (adicione imagens para ativar)",
                         text_color=C["text3"], font=("Segoe UI", 9)).pack(side="left")

        # === GRID DE IMAGENS ===
        grid_container = ctk.CTkFrame(p, fg_color="#0a0c18", border_color=C["border"],
                                       border_width=1, corner_radius=4)
        grid_container.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self._amb_grid_scroll = ctk.CTkScrollableFrame(grid_container, fg_color="#0a0c18",
                                                        corner_radius=0,
                                                        scrollbar_button_color="#44cc88",
                                                        scrollbar_button_hover_color="#66ffaa")
        self._amb_grid_scroll.pack(fill="both", expand=True)
        self._amb_render_grid(images)

        # === BOTTOM BAR ===
        btns = ctk.CTkFrame(p, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=(4, 10))

        use_btn = ctk.CTkButton(btns, text="\u25b6 USAR SELECIONADA NO GERADOR", height=30,
                      font=("Segoe UI", 10, "bold"), fg_color="#44cc88",
                      text_color="#0a0a0f", hover_color="#66ffaa",
                      corner_radius=4, command=self._amb_use_selected)
        use_btn.pack(side="left", padx=(0, 4))
        _ToolTip(use_btn,
            "Forca uma imagem especifica como referencia\n"
            "(ignora o auto-match para a proxima geracao).\n"
            "\n"
            "1. Clique numa imagem (borda verde)\n"
            "2. Clique neste botao\n"
            "3. A imagem vai para o gerador como referencia\n"
            "\n"
            "Util quando voce quer garantir uma imagem especifica.")

        ctk.CTkButton(btns, text="LIMPAR TUDO", width=100, height=30,
                      font=("Segoe UI", 9, "bold"), fg_color="#2a0808",
                      border_color="#ff4444", border_width=1,
                      text_color="#ff4444", hover_color="#3a1010",
                      corner_radius=4,
                      command=self._amb_clear_all).pack(side="right")

    def _amb_get_images(self):
        """Retorna lista de paths de imagens na pasta de ambientação."""
        from makevid.config import AMBIENCE_REFS_DIR
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        imgs = []
        if AMBIENCE_REFS_DIR.exists():
            for f in sorted(AMBIENCE_REFS_DIR.iterdir()):
                if f.suffix.lower() in exts:
                    imgs.append(f)
        return imgs

    def _amb_render_grid(self, images):
        """Renderiza grid de thumbnails."""
        for w in self._amb_grid_scroll.winfo_children():
            w.destroy()
        self._amb_img_refs = []
        self._amb_selected = None

        if not images:
            ctk.CTkLabel(self._amb_grid_scroll,
                         text="Nenhuma imagem.\nClique + IMAGENS ou + PASTA para adicionar.",
                         text_color=C["text3"], font=("Segoe UI", 10)).pack(pady=30)
            return

        cols = 5
        row_frame = None
        for i, img_path in enumerate(images):
            if i % cols == 0:
                row_frame = ctk.CTkFrame(self._amb_grid_scroll, fg_color="transparent")
                row_frame.pack(fill="x", pady=3)

            cell = ctk.CTkFrame(row_frame, fg_color=C["card"], corner_radius=4,
                                border_color=C["border"], border_width=1,
                                width=110, height=110)
            cell.pack(side="left", padx=3)
            cell.pack_propagate(False)

            try:
                img = Image.open(img_path).convert("RGB")
                img.thumbnail((100, 100))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                self._amb_img_refs.append(ctk_img)
                lbl = ctk.CTkLabel(cell, image=ctk_img, text="")
                lbl.pack(expand=True)
                # Click para selecionar
                for widget in [cell, lbl]:
                    widget.bind("<Button-1>", lambda e, p=img_path, c=cell: self._amb_select(p, c))
                    widget.bind("<Double-Button-1>", lambda e, p=img_path: self._amb_preview(p))
            except Exception:
                ctk.CTkLabel(cell, text="ERR", text_color="#ff4444",
                             font=("Segoe UI", 9)).pack(expand=True)

            # Nome curto
            name = img_path.stem[:12]
            ctk.CTkLabel(cell, text=name, text_color=C["text3"],
                         font=("Segoe UI", 7)).place(relx=0.5, rely=1.0, anchor="s", y=-2)

            # X button
            ctk.CTkButton(cell, text="\u2715", width=14, height=14, corner_radius=7,
                          fg_color="#ff4444", hover_color="#ff6666",
                          text_color="#ffffff", font=("", 7),
                          command=lambda p=img_path: self._amb_remove(p)
                          ).place(relx=1.0, rely=0, anchor="ne", x=-2, y=2)

    def _amb_select(self, path, cell):
        """Seleciona imagem."""
        # Reset borda anterior
        if hasattr(self, '_amb_sel_cell') and self._amb_sel_cell:
            try:
                self._amb_sel_cell.configure(border_color=C["border"], border_width=1)
            except Exception:
                pass
        self._amb_selected = path
        self._amb_sel_cell = cell
        cell.configure(border_color="#44cc88", border_width=2)

    def _amb_preview(self, path):
        """Mostra preview maior da imagem no painel."""
        try:
            img = Image.open(path).convert("RGB")
            pp = self.app.preview_panel
            display_img, w, h = pp._fit_image(img)
            pp._preview_img_ref = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(w, h))
            pp.preview_label.configure(image=pp._preview_img_ref, text="", compound="center")
            pp.clip_info.configure(text=f"Ambientação | {img.size[0]}x{img.size[1]} | {path.name}")
        except Exception:
            pass

    def _amb_add_images(self):
        """Importa imagens selecionadas para a pasta de ambientação."""
        import shutil
        from makevid.config import AMBIENCE_REFS_DIR
        paths = filedialog.askopenfilenames(
            title="Importar Imagens de Ambientação",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if not paths:
            return
        for p in paths:
            src = Path(p)
            dst = AMBIENCE_REFS_DIR / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
        self._amb_refresh()

    def _amb_add_folder(self):
        """Importa todas as imagens de uma pasta."""
        import shutil
        from makevid.config import AMBIENCE_REFS_DIR
        folder = filedialog.askdirectory(title="Selecionar Pasta com Imagens")
        if not folder:
            return
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        src_folder = Path(folder)
        for f in src_folder.iterdir():
            if f.suffix.lower() in exts:
                dst = AMBIENCE_REFS_DIR / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
        self._amb_refresh()

    def _amb_remove(self, path):
        """Remove imagem da pasta de ambientação."""
        try:
            Path(path).unlink()
        except Exception:
            pass
        self._amb_refresh()

    def _amb_clear_all(self):
        """Remove todas as imagens."""
        from makevid.config import AMBIENCE_REFS_DIR
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        for f in AMBIENCE_REFS_DIR.iterdir():
            if f.suffix.lower() in exts:
                try:
                    f.unlink()
                except Exception:
                    pass
        self._amb_refresh()

    def _amb_open_folder(self):
        """Abre pasta no explorador de arquivos."""
        import subprocess
        from makevid.config import AMBIENCE_REFS_DIR
        subprocess.Popen(f'explorer "{AMBIENCE_REFS_DIR}"')

    def _amb_use_selected(self):
        """Envia imagem selecionada como referência para o gerador (Wan TI2V)."""
        if not hasattr(self, '_amb_selected') or not self._amb_selected:
            return
        path = str(self._amb_selected)
        gen = self.app.generator_panel
        # Adicionar como ref image e mudar para mode image
        if path not in gen._ref_images:
            gen._ref_images.append(path)
        gen.mode_var.set("image")
        gen._on_mode()
        gen._refresh_thumbs()
        # Mudar engine para Wan TI2V se não estiver
        if "Wan" not in self.app.engine_var.get() and "VACE" not in self.app.engine_var.get():
            self.app.engine_var.set("Wan 2.2 TI2V")
        self.hide()

    def _amb_refresh(self):
        """Atualiza grid de ambientação."""
        images = self._amb_get_images()
        self._amb_count_label.configure(text=f"{len(images)} imagens")
        self._amb_render_grid(images)

    # ============================================================
    # VOICE PROFILE (inline no editor de personagem)
    # ============================================================

