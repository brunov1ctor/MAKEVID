"""Characters - Fichas de personagens."""

import customtkinter as ctk
import uuid
from tkinter import filedialog
from pathlib import Path
from PIL import Image
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR


class CharactersMixin:
    """Metodos de personagens do StylePanel."""

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
        self.app.project.save(PROJECTS_DIR)
        self._editor_char_id = None
        self._refresh_char_list()

    def _copy_sheet_prompt(self, char):
        self._save_char_full(char)
        sheet = char.to_sheet_prompt()
        self.app.clipboard_clear()
        self.app.clipboard_append(sheet)

