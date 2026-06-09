"""Panel Properties - Painel lateral de propriedades do clip selecionado."""

import customtkinter as ctk
from pathlib import Path
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR


class ClipProperties:
    """Painel de propriedades que aparece sobre o preview quando um clip e selecionado."""

    def __init__(self, preview_panel):
        self.pp = preview_panel
        self.app = preview_panel.app
        self._panel = None

    def show(self, clip, total):
        """Mostra propriedades do clip."""
        self.close()
        self._current_clip = clip

        self._panel = ctk.CTkFrame(self.pp.preview_frame, width=230, fg_color=C["panel"],
                                    border_color=C["gold"], border_width=1, corner_radius=6)
        self._panel.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5, relheight=0.95)
        self._panel.lift()

        # Header
        header = ctk.CTkFrame(self._panel, fg_color="transparent", height=24)
        header.pack(fill="x", padx=6, pady=(6, 0))
        header.pack_propagate(False)
        self._header_label = ctk.CTkLabel(header, text=f"CLIP #{clip.position+1}", font=("Segoe UI", 11, "bold"),
                     text_color=C["gold"])
        self._header_label.pack(side="left", padx=4)
        ctk.CTkButton(header, text="X", width=20, height=18, fg_color=C["panel"],
                      text_color=C["text3"], hover_color=C["card_hover"], font=("", 9),
                      command=self.close).pack(side="right")

        ctk.CTkFrame(self._panel, height=2, fg_color=C["gold"]).pack(fill="x", padx=8, pady=(4, 0))

        scroll = ctk.CTkScrollableFrame(self._panel, fg_color="transparent",
                                        scrollbar_button_color=C["gold"],
                                        scrollbar_button_hover_color="#ffd700")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Descricao
        ctk.CTkLabel(scroll, text="DESCRICAO", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"]).pack(anchor="w", padx=6, pady=(4, 2))
        desc_text = clip.prompt if clip.prompt else "(sem descricao)"
        self._desc_label = ctk.CTkLabel(scroll, text=desc_text, font=("Segoe UI", 9),
                     text_color=C["text"], wraplength=190, anchor="w", justify="left")
        self._desc_label.pack(anchor="w", padx=6, pady=(0, 6))

        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=6, pady=2)

        # Props
        self._props_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._props_frame.pack(fill="x")
        self._build_props(clip)

        # Titulo editavel
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=6, pady=(8, 4))
        ctk.CTkLabel(scroll, text="TITULO", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"]).pack(anchor="w", padx=6, pady=(0, 2))

        self._title_var = ctk.StringVar(value=clip.prompt or "")
        title_entry = ctk.CTkEntry(scroll, textvariable=self._title_var, fg_color=C["input"],
                                   border_color=C["gold"], border_width=1, text_color=C["text"],
                                   font=("Segoe UI", 10, "bold"), width=190)
        title_entry.pack(padx=6, pady=(0, 6))

        def _save(*_):
            new = self._title_var.get().strip()
            if new and self._current_clip and new != self._current_clip.prompt:
                self._current_clip.prompt = new
                self.app.project.save(PROJECTS_DIR)
                self.app.timeline.draw()

        self._title_var.trace_add("write", _save)
        title_entry.bind("<Return>", lambda e: self.app.focus_set())
        self.app.bind("<Button-1>", lambda e: self._unfocus_entry(e, title_entry), add="+")

        # Acoes
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=6, pady=(2, 6))
        ctk.CTkLabel(scroll, text="ACOES", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"]).pack(anchor="w", padx=6, pady=(0, 4))

        grid = ctk.CTkFrame(scroll, fg_color="transparent")
        grid.pack(fill="x", padx=6, pady=(0, 10))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        btn_h = 28
        btn_font = ("Segoe UI", 9, "bold")

        ctk.CTkButton(grid, text="\u27f3 REGERAR", height=btn_h, font=btn_font,
                      fg_color=C["gold"], text_color="#0a0a0f", hover_color="#ffd700",
                      corner_radius=4,
                      command=lambda: self.app.regenerate_clip(self._current_clip)).grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=2)

        ctk.CTkButton(grid, text="\u29c9 DUPLICAR", height=btn_h, font=btn_font,
                      fg_color=C["card"], border_width=1, border_color=C["cyan"],
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      corner_radius=4,
                      command=lambda: self.app.duplicate_clip(self._current_clip)).grid(row=0, column=1, sticky="ew", padx=(2, 0), pady=2)

        ctk.CTkButton(grid, text="\u2702 DIVIDIR", height=btn_h, font=btn_font,
                      fg_color=C["card"], border_width=1, border_color=C["purple"],
                      text_color=C["purple"], hover_color="#1a0a2a",
                      corner_radius=4,
                      command=lambda: self.app.enter_split_mode()).grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=2)

        ctk.CTkButton(grid, text="\u2715 REMOVER", height=btn_h, font=btn_font,
                      fg_color="#2a0808", border_width=1, border_color="#ff4444",
                      text_color="#ff4444", hover_color="#3a1010",
                      corner_radius=4,
                      command=lambda: self.app.delete_clip(self._current_clip)).grid(row=1, column=1, sticky="ew", padx=(2, 0), pady=2)

    def update_info(self, clip, total):
        """Atualiza informacoes in-place sem reconstruir o painel."""
        self._current_clip = clip
        if self._panel and self._panel.winfo_exists():
            self._header_label.configure(text=f"CLIP #{clip.position+1}")
            self._desc_label.configure(text=clip.prompt if clip.prompt else "(sem descricao)")
            self._title_var.set(clip.prompt or "")
            # Rebuild props (leve)
            for w in self._props_frame.winfo_children():
                w.destroy()
            self._build_props(clip)
            self._panel.lift()

    def _build_props(self, clip):
        """Constroi linhas de propriedades."""
        def row(lbl, val, color=C["text"]):
            f = ctk.CTkFrame(self._props_frame, fg_color="transparent")
            f.pack(fill="x", padx=6, pady=1)
            ctk.CTkLabel(f, text=lbl, text_color=C["text3"], font=("Segoe UI", 9, "bold"), width=60).pack(side="left")
            ctk.CTkLabel(f, text=str(val), text_color=color, font=("Consolas", 10, "bold")).pack(side="left")

        row("Duracao", f"{clip.duration:.1f}s", C["cyan"])
        row("Status", clip.status.upper(), C["cyan"] if clip.status == "done" else C["gold"])
        row("Seed", clip.seed or "random")

        if clip.video_path:
            p = Path(clip.video_path)
            if p.exists():
                row("Tamanho", f"{p.stat().st_size / 1e6:.1f} MB")

    def close(self):
        if self._panel and self._panel.winfo_exists():
            self._panel.destroy()
            self._panel = None
        # Limpar bind global
        try:
            self.app.unbind("<Button-1>")
        except Exception:
            pass

    def _unfocus_entry(self, event, entry):
        """Remove foco do entry se click foi fora dele."""
        try:
            widget = event.widget
            if widget != entry and not str(widget).startswith(str(entry)):
                self.app.focus_set()
        except Exception:
            pass

    @property
    def is_visible(self):
        return self._panel is not None and self._panel.winfo_exists()
