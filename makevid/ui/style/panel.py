"""Panel Estilo - Shell principal que delega para mixins."""

import customtkinter as ctk
from pathlib import Path
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR
from makevid.ui.style.storyboard import StoryboardMixin
from makevid.ui.style.characters import CharactersMixin
from makevid.ui.style.voice_profile import VoiceProfileMixin
from makevid.ui.style.ambience import AmbienceMixin


class StylePanel(StoryboardMixin, CharactersMixin, VoiceProfileMixin, AmbienceMixin):
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
        if tab not in ("storyboard", "chars", "ambience"):
            tab = "storyboard"
        if self._visible:
            self._switch_tab(tab)
            return
        self._current_tab = tab
        self.app._h_paned.pack_forget()
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
        self.app._h_paned.pack(fill="both", expand=True)
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

        self._tab_amb_btn = ctk.CTkButton(
            header, text="AMBIENTA\u00c7\u00c3O", height=28, width=120,
            font=("Segoe UI", 9, "bold"), corner_radius=0,
            fg_color=C["panel"] if self._current_tab == "ambience" else C["card"],
            text_color="#44cc88" if self._current_tab == "ambience" else C["text3"],
            hover_color=C["card_hover"],
            command=lambda: self._switch_tab("ambience"))
        self._tab_amb_btn.pack(side="left")

        ctk.CTkButton(header, text="\u2715", width=30, height=26,
                      font=("Segoe UI", 14, "bold"), fg_color="transparent",
                      text_color="#ff4444", hover_color="#2a0808",
                      corner_radius=4,
                      command=self.hide).pack(side="right", padx=6)

        self._content = ctk.CTkFrame(f, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        if self._current_tab == "storyboard":
            self._build_storyboard()
        elif self._current_tab == "chars":
            self._build_characters()
        else:
            self._build_ambience()

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
