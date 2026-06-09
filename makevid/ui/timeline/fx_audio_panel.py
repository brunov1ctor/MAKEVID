"""FX/Audio Panel - Orquestrador. Delega para fx_editor, audio_mixer, export_panel, recorder."""

import customtkinter as ctk
from makevid.ui.theme import C
from makevid.ui.timeline.fx_editor import FxEditor
from makevid.ui.timeline.audio_mixer import AudioMixer
from makevid.ui.timeline.export_panel import ExportPanel
from makevid.ui.timeline.recorder import AudioRecorder
from makevid.ui.timeline.track_editor import TrackEditor


FX_ITEMS = [
    ("Fade In", "Escuro para imagem"),
    ("Fade Out", "Imagem para escuro"),
    ("Cross Dissolve", "Mistura entre clips"),
    ("Wipe Left", "Cortina da direita"),
    ("Wipe Right", "Cortina da esquerda"),
    ("Flash", "Flash branco"),
    ("Glitch", "Distorcao digital"),
    ("Vignette", "Bordas escuras"),
    ("Blur", "Desfoque gaussiano"),
    ("Shake", "Tremor de camera"),
    ("Color Shift", "Deslocamento de cor RGB"),
    ("Sepia", "Tom sepia vintage"),
    ("Invert", "Cores invertidas"),
    ("Pixelate", "Efeito pixelado"),
    ("Film Grain", "Granulacao de filme"),
    ("Letterbox", "Barras cinematicas"),
]

VOICE_ITEMS = [
    ("Importar Voz", "WAV, MP3"),
    ("Gravar", "Gravar microfone"),
    ("Gerar TTS", "Texto para fala (edge-tts)"),
]

SFX_ITEMS = [
    ("Importar SFX", "WAV, MP3, OGG"),
    ("Gravar", "Gravar microfone"),
]

MUSIC_ITEMS = [
    ("Importar Musica", "WAV, MP3, OGG"),
]

AUDIO_ITEMS = [
    ("Importar Audio", "MP3, WAV, OGG"),
    ("Gravar", "Gravar microfone"),
]


class FxAudioPanel:
    """Painel que ocupa o lado esquerdo inteiro da interface."""

    def __init__(self, parent, timeline):
        self.timeline = timeline
        self._visible = False
        self._frame = None
        # Sub-components
        self._fx_editor = FxEditor(self)
        self._audio_mixer = AudioMixer(self)
        self._export_panel = ExportPanel(self)
        self._recorder = AudioRecorder(self)
        self._track_editor = TrackEditor(self)

    @property
    def _mixer_item(self):
        return self._audio_mixer.item

    def show(self, track_type: str):
        """Mostra painel de FX ou Audio no lugar do painel gerador."""
        if self._visible:
            self.hide()

        app = self.timeline.app
        app.generator_panel.container.pack_forget()

        if not app.preview_panel.panel.winfo_ismapped():
            app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self._frame = ctk.CTkFrame(app._main, width=320, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=6)
        self._frame.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self._frame.pack_propagate(False)

        self._build_list(track_type)
        self._visible = True

    def show_export(self):
        if self._visible:
            self.hide()
        app = self.timeline.app
        app.generator_panel.container.pack_forget()
        # Garantir preview visivel
        if not app.preview_panel.panel.winfo_ismapped():
            app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self._frame = ctk.CTkFrame(app._main, width=280, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=6)
        self._frame.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self._export_panel.build(self._frame)
        self._visible = True

    def show_audio_mixer(self, item):
        if self._visible:
            self.hide()
        app = self.timeline.app
        app.generator_panel.container.pack_forget()
        if not app.preview_panel.panel.winfo_ismapped():
            app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self._frame = ctk.CTkFrame(app._main, width=320, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=6)
        self._frame.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self._frame.pack_propagate(False)
        self._audio_mixer.build(self._frame, item)
        self._visible = True

    def show_fx_editor(self, item):
        if self._visible:
            self.hide()
        app = self.timeline.app
        app.generator_panel.container.pack_forget()
        if not app.preview_panel.panel.winfo_ismapped():
            app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self._frame = ctk.CTkFrame(app._main, width=320, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=6)
        self._frame.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self._frame.pack_propagate(False)
        self._fx_editor.build(self._frame, item)
        self._visible = True

    def show_track_editor(self, item):
        """Abre editor especifico para VOICE, SFX ou MUSIC."""
        if self._visible:
            self.hide()
        app = self.timeline.app
        app.generator_panel.container.pack_forget()
        if not app.preview_panel.panel.winfo_ismapped():
            app.preview_panel.panel.pack(side="right", fill="both", expand=True, pady=4)
        self._frame = ctk.CTkFrame(app._main, width=320, fg_color=C["panel"],
                                   border_color=C["gold"], border_width=1, corner_radius=6)
        self._frame.pack(side="left", fill="y", padx=(0, 4), pady=4)
        self._frame.pack_propagate(False)
        self._track_editor.build(self._frame, item)
        self._visible = True

    def hide(self):
        if self._visible and self._frame and self._frame.winfo_exists():
            self._frame.destroy()
            self._frame = None
            app = self.timeline.app
            app.generator_panel.container.pack(side="left", fill="y", padx=(0, 4), pady=4)
            self._visible = False
            self.timeline.draw()

    def _start_player_at_time(self, player, start_time):
        """Inicia player e faz seek para o tempo especificado."""
        player.play()
        total_dur = player.app.project.total_duration()
        if total_dur > 0 and player._timeline_total_frames > 0:
            ratio = start_time / total_dur
            target_frame = int(ratio * player._timeline_total_frames)
            player._seek_to_frame(target_frame)

    # --- Build FX/Audio list ---

    def _build_list(self, track_type):
        p = self._frame
        config = {
            "fx": (C["purple"], "EFEITOS", FX_ITEMS),
            "voice": ("#ff9944", "\U0001f3a4 VOZ", VOICE_ITEMS),
            "sfx": ("#44cc88", "\U0001f50a SFX", SFX_ITEMS),
            "music": ("#cc44aa", "\U0001f3b5 MUSICA", MUSIC_ITEMS),
            "audio": (C["cyan"], "AUDIO", AUDIO_ITEMS),
        }
        color, title, items = config.get(track_type, (C["cyan"], "AUDIO", AUDIO_ITEMS))

        header = ctk.CTkFrame(p, fg_color="transparent", height=32)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 13, "bold"), text_color=color).pack(side="left")
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=self.hide).pack(side="right")

        ctk.CTkFrame(p, height=2, fg_color=color).pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkButton(p, text="Limpar Track", height=26, font=("Segoe UI", 9, "bold"),
                      fg_color="transparent", text_color="#ff4444", hover_color="#2a0808",
                      border_width=1, border_color="#ff4444",
                      command=lambda: self._clear_track(track_type)).pack(fill="x", padx=10, pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                        scrollbar_button_color=color,
                                        scrollbar_button_hover_color=color)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkLabel(scroll, text="Clique para adicionar na track",
                     text_color=C["text3"], font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))

        for name, desc in items:
            item = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=5,
                                border_color=C["border"], border_width=1)
            item.pack(fill="x", pady=3)
            ctk.CTkLabel(item, text=name, font=("Segoe UI", 10, "bold"),
                         text_color=C["text"]).pack(anchor="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(item, text=desc, font=("Segoe UI", 8),
                         text_color=C["text3"]).pack(anchor="w", padx=10, pady=(0, 6))
            item.bind("<Enter>", lambda e, i=item, cl=color: i.configure(border_color=cl))
            item.bind("<Leave>", lambda e, i=item: i.configure(border_color=C["border"]))

            if "Gravar" in name:
                for widget in item.winfo_children():
                    widget.bind("<Button-1>", lambda e, t=track_type: self._recorder.open(track=t))
                item.bind("<Button-1>", lambda e, t=track_type: self._recorder.open(track=t))
            elif "Importar" in name:
                for widget in item.winfo_children():
                    widget.bind("<Button-1>", lambda e, t=track_type: self._import_audio(t))
                item.bind("<Button-1>", lambda e, t=track_type: self._import_audio(t))
            elif "TTS" in name:
                for widget in item.winfo_children():
                    widget.bind("<Button-1>", lambda e: self._generate_tts())
                item.bind("<Button-1>", lambda e: self._generate_tts())
            else:
                for widget in item.winfo_children():
                    widget.bind("<Button-1>", lambda e, n=name, t=track_type: self._add_item(n, t))
                item.bind("<Button-1>", lambda e, n=name, t=track_type: self._add_item(n, t))

    def _add_item(self, name, track_type):
        tl = self.timeline
        existing = tl.project.get_track_items(track_type)
        if existing:
            last = max(existing, key=lambda i: i.start_time + i.duration)
            start = last.start_time + last.duration
        else:
            start = tl.playhead_pos
        tl.project.add_track_item(name=name, track=track_type, start_time=start, duration=2.0)
        from makevid.config import PROJECTS_DIR
        tl.project.save(PROJECTS_DIR)
        tl.draw()

    def _import_audio(self, track_type):
        """Importa arquivo de audio e adiciona na track."""
        from tkinter import filedialog
        from pathlib import Path
        from makevid.config import AUDIO_DIR, PROJECTS_DIR
        import shutil

        paths = filedialog.askopenfilenames(
            filetypes=[("Audio", "*.wav *.mp3 *.ogg *.flac")])
        if not paths:
            return

        tl = self.timeline
        for p in paths:
            src = Path(p)
            dest_dir = AUDIO_DIR / tl.project.id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            if not dest.exists():
                shutil.copy2(str(src), str(dest))

            # Pegar duracao
            dur = 5.0
            try:
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(str(dest)) or 5.0
            except Exception:
                pass

            existing = tl.project.get_track_items(track_type)
            if existing:
                last = max(existing, key=lambda i: i.start_time + i.duration)
                start = last.start_time + last.duration
            else:
                start = tl.playhead_pos

            tl.project.add_track_item(
                name=src.stem[:20], track=track_type,
                start_time=start, duration=dur, file_path=str(dest))

        tl.project.save(PROJECTS_DIR)
        tl.draw()

    def _generate_tts(self):
        """Abre dialog para gerar TTS e adicionar na track voice."""
        import threading

        app = self.timeline.app
        win = ctk.CTkToplevel(app)
        win.title("Gerar Voz TTS")
        win.geometry("380x200")
        win.configure(fg_color=C["panel"])
        win.transient(app)
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="GERAR VOZ", font=("Segoe UI", 12, "bold"),
                     text_color="#ff9944").pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(win, text="Texto:", text_color=C["text2"],
                     font=("Segoe UI", 9)).pack(anchor="w", padx=15, pady=(5, 2))
        text_box = ctk.CTkTextbox(win, height=60, fg_color=C["input"],
                                   border_color="#ff9944", border_width=1,
                                   text_color=C["text"], font=("Segoe UI", 10))
        text_box.pack(fill="x", padx=15)

        status = ctk.CTkLabel(win, text="", text_color=C["text3"], font=("Segoe UI", 9))
        status.pack(anchor="w", padx=15, pady=(4, 0))

        def generate():
            text = text_box.get("0.0", "end").strip()
            if not text:
                return
            status.configure(text="Gerando...", text_color="#ff9944")
            win.update()

            def run():
                from makevid.core.tts_provider import generate_voice
                from makevid.config import AUDIO_DIR, PROJECTS_DIR
                import time as _time

                out_dir = AUDIO_DIR / app.project.id
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f"tts_{int(_time.time())}.wav"
                result = generate_voice(text, path)
                if result:
                    import wave
                    with wave.open(str(path), "r") as wf:
                        dur = wf.getnframes() / wf.getframerate()

                    tl = self.timeline
                    existing = tl.project.get_track_items("voice")
                    if existing:
                        last = max(existing, key=lambda i: i.start_time + i.duration)
                        start = last.start_time + last.duration
                    else:
                        start = tl.playhead_pos

                    tl.project.add_track_item(
                        name=text[:20], track="voice",
                        start_time=start, duration=dur, file_path=str(path),
                        params={"text": text})
                    tl.project.save(PROJECTS_DIR)

                    app.after(0, lambda: [
                        status.configure(text="\u2714 Pronto!", text_color="#0ac8b9"),
                        tl.draw(),
                        win.after(1000, win.destroy)
                    ])
                else:
                    app.after(0, lambda: status.configure(text="Erro na geracao", text_color="#ff4444"))

            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(win, text="GERAR", height=32, font=("Segoe UI", 11, "bold"),
                      fg_color="#ff9944", text_color="#0a0a0f", hover_color="#ffbb66",
                      command=generate).pack(fill="x", padx=15, pady=(10, 10))

    def _clear_track(self, track_type):
        items = self.timeline.project.get_track_items(track_type)
        for item in items:
            self.timeline.project.remove_track_item(item.id)
        from makevid.config import PROJECTS_DIR
        self.timeline.project.save(PROJECTS_DIR)
        self.hide()
