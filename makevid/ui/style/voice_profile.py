"""Voice Profile - Configuracao de voz dos personagens."""

import customtkinter as ctk
import threading
from tkinter import filedialog
from pathlib import Path
from makevid.ui.theme import C
from makevid.config import PROJECTS_DIR


class VoiceProfileMixin:
    """Metodos de voice profile do StylePanel."""

    def _build_voice_section(self, ed, char):
        """Constroi secao compacta de voz com botao para popup completo."""
        from makevid.ui.menus import _ToolTip
        from makevid.core.voice_engine import VoiceProfile, VOICE_PRESETS

        ctk.CTkFrame(ed, height=1, fg_color=C["cyan"]).pack(fill="x", padx=12, pady=(10, 4))
        voice_lbl = ctk.CTkLabel(ed, text="\U0001f3a4 VOZ DO PERSONAGEM", font=("Segoe UI", 11, "bold"),
                     text_color=C["cyan"])
        voice_lbl.pack(anchor="w", padx=12, pady=(0, 4))
        _ToolTip(voice_lbl, "Voice Profile: identidade vocal do personagem.\n"
                 "Define timbre, tom, velocidade e como cada\n"
                 "emocao modifica a voz nas cenas do storyboard.\n\n"
                 "A emocao vem automaticamente do campo EMOCAO\n"
                 "de cada cena — voce so configura o perfil base.")

        voice_frame = ctk.CTkFrame(ed, fg_color=C["panel"], corner_radius=4,
                                    border_color=C["cyan"], border_width=1)
        voice_frame.pack(fill="x", padx=12, pady=(0, 8))

        # Carregar profile atual
        profile = VoiceProfile.from_dict(char.voice_profile) if char.voice_profile else VoiceProfile()
        if char.voice_id and not char.voice_profile:
            profile.voice_id = char.voice_id

        # Resumo compacto
        info_row = ctk.CTkFrame(voice_frame, fg_color="transparent")
        info_row.pack(fill="x", padx=8, pady=(8, 4))

        engine_text = profile.engine.upper()
        voice_text = profile.voice_id.split("-")[-1].replace("Neural", "") if "Neural" in profile.voice_id else profile.voice_id[:20]
        pitch_text = f"{profile.pitch_base:+d}Hz" if profile.pitch_base else "0Hz"
        rate_text = f"{profile.rate_base:+d}%" if profile.rate_base else "0%"

        ctk.CTkLabel(info_row, text=f"Engine: ", text_color=C["text3"],
                     font=("Segoe UI", 9)).pack(side="left")
        ctk.CTkLabel(info_row, text=engine_text, text_color=C["cyan"],
                     font=("Segoe UI", 9, "bold")).pack(side="left")
        ctk.CTkLabel(info_row, text=f"  Voz: ", text_color=C["text3"],
                     font=("Segoe UI", 9)).pack(side="left")
        ctk.CTkLabel(info_row, text=voice_text, text_color=C["gold"],
                     font=("Segoe UI", 9, "bold")).pack(side="left")

        params_row = ctk.CTkFrame(voice_frame, fg_color="transparent")
        params_row.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(params_row, text=f"Tom: {pitch_text}  |  Vel: {rate_text}  |  Aspereza: {profile.roughness}%  |  Resp: {profile.breathiness}%",
                     text_color=C["text3"], font=("Segoe UI", 8)).pack(side="left")

        # Botões
        btn_row = ctk.CTkFrame(voice_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(4, 8))

        test_btn = ctk.CTkButton(btn_row, text="\u25b6 Testar", width=65, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      command=lambda: self._test_voice(char))
        test_btn.pack(side="left", padx=(0, 4))
        _ToolTip(test_btn, "Gera preview rapido da voz com edge-tts.")

        config_btn = ctk.CTkButton(btn_row, text="\u2699 CONFIGURAR VOZ", width=140, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700",
                      corner_radius=4,
                      command=lambda: self._open_voice_profile_popup(char))
        config_btn.pack(side="left", padx=(0, 4))
        _ToolTip(config_btn, "Abre painel completo de Voice Profile:\n"
                 "- Selecao de engine (edge-tts/bark/xtts/parler)\n"
                 "- Sliders de tom, velocidade, respiracao, aspereza\n"
                 "- Configuracao de emocoes por cena\n"
                 "- Presets rapidos (heroi grave, vilao sombrio...)\n"
                 "- Teste comparativo de emocoes")



        # Indicador de amostra
        sample_path = profile.voice_sample_path or char.voice_sample or ""
        if sample_path and Path(sample_path).exists():
            ctk.CTkLabel(btn_row, text=f"  \u2713 {Path(sample_path).name}",
                         text_color="#44cc88", font=("Segoe UI", 8)).pack(side="left", padx=(6, 0))

    def _test_voice(self, char):
        """Gera e toca preview da voz usando VoiceProfile."""
        import threading
        from makevid.core.voice_engine import VoiceProfile, build_speech_params

        profile = VoiceProfile.from_dict(char.voice_profile) if char.voice_profile else VoiceProfile()
        if char.voice_id and not char.voice_profile:
            profile.voice_id = char.voice_id

        name = char.name or "personagem"
        text = f"Ola, eu sou {name}. Esta e a minha voz."
        params = build_speech_params(profile, text, "neutral")

        def run():
            from makevid.core.tts_provider import generate_voice, play_audio
            from makevid.config import AUDIO_DIR
            path = AUDIO_DIR / "_voice_test.wav"
            result = generate_voice(text, path, voice_profile=params)
            if result:
                play_audio(path)

        threading.Thread(target=run, daemon=True).start()

    def _import_voice_sample(self, char):
        """Importa amostra de voz WAV/MP3."""
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.mp3 *.ogg")])
        if path:
            self._voice_sample_path = path
            char.voice_sample = path
            self.app.project.save(PROJECTS_DIR)

    def _record_voice_sample(self, char):
        """Grava amostra de voz no painel esquerdo (lista de personagens) com waveform."""
        import sounddevice as sd
        import numpy as np
        import wave
        import time as _time
        import tkinter as tk
        from makevid.config import AUDIO_DIR

        color = "#ff9944"
        SR = 44100
        state = {"recording": False, "frames": [], "start": 0,
                 "stream": None, "wave_job": None}

        # Substituir conteudo do painel esquerdo (lista de personagens)
        p = self._char_list_frame
        for w in p.winfo_children():
            w.destroy()

        # Header
        ctk.CTkLabel(p, text="\u25cf GRAVAR VOZ", font=("Segoe UI", 11, "bold"),
                     text_color=color).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(p, text=char.name or "(sem nome)",
                     text_color=C["text2"], font=("Segoe UI", 9)).pack(anchor="w", padx=8)
        ctk.CTkFrame(p, height=2, fg_color=color).pack(fill="x", padx=8, pady=(4, 6))

        # Timer
        time_lbl = ctk.CTkLabel(p, text="00:00.0", font=("Consolas", 20, "bold"),
                                text_color=C["text"])
        time_lbl.pack(pady=(6, 4))

        # Waveform canvas
        wave_canvas = tk.Canvas(p, height=50, bg="#080a14", highlightthickness=1,
                                highlightbackground=color)
        wave_canvas.pack(fill="x", padx=8, pady=(0, 6))

        # Status
        status_lbl = ctk.CTkLabel(p, text="Fale 5-15s para referencia",
                                  text_color=C["text3"], font=("Segoe UI", 8))
        status_lbl.pack(anchor="w", padx=8)

        def update_time():
            if state["recording"]:
                elapsed = _time.time() - state["start"]
                time_lbl.configure(text=f"{int(elapsed)//60:02d}:{elapsed%60:04.1f}")
                p.after(100, update_time)

        def draw_waveform():
            if not state["recording"]:
                return
            wave_canvas.delete("all")
            w = wave_canvas.winfo_width() or 220
            h = 50
            mid = h // 2
            if state["frames"]:
                last = state["frames"][-1]
                samples = last.flatten().astype(float) / 32768.0
                peak = max(abs(samples.max()), abs(samples.min()), 0.001)
                samples = samples / peak
                block_size = max(1, len(samples) // w)
                for i in range(min(w, len(samples) // block_size)):
                    start_s = i * block_size
                    end_s = min(start_s + block_size, len(samples))
                    block = samples[start_s:end_s]
                    if len(block) > 0:
                        y1 = mid - int(block.max() * (mid - 2))
                        y2 = mid - int(block.min() * (mid - 2))
                        wave_canvas.create_line(i, y1, i, y2, fill=color, width=1)
            else:
                wave_canvas.create_line(0, mid, w, mid, fill="#1a2a3a", width=1, dash=(2, 4))
            state["wave_job"] = p.after(50, draw_waveform)

        def start_rec():
            state["recording"] = True
            state["frames"] = []
            state["start"] = _time.time()
            status_lbl.configure(text="\u25cf GRAVANDO...", text_color="#ff4444")
            rec_btn.configure(text="\u25a0 PARAR", fg_color="#2a0808",
                              border_color="#ff4444", text_color="#ff4444",
                              command=stop_rec)
            cancel_btn.configure(state="disabled")
            update_time()
            draw_waveform()

            def callback(indata, frames, t, status):
                if state["recording"]:
                    state["frames"].append(indata.copy())

            state["stream"] = sd.InputStream(
                samplerate=SR, channels=1, dtype="int16", callback=callback)
            state["stream"].start()

        def stop_rec():
            state["recording"] = False
            if state["wave_job"]:
                p.after_cancel(state["wave_job"])
                state["wave_job"] = None
            if state["stream"]:
                state["stream"].stop()
                state["stream"].close()

            if not state["frames"]:
                status_lbl.configure(text="Nenhum audio capturado", text_color="#ff4444")
                rec_btn.configure(text="\u25cf REC", fg_color=color,
                                  border_color=color, text_color="#0a0a0f",
                                  command=start_rec)
                cancel_btn.configure(state="normal")
                return

            audio = np.concatenate(state["frames"], axis=0)
            duration = len(audio) / SR
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
            self.app.project.save(PROJECTS_DIR)

            # Waveform final
            wave_canvas.delete("all")
            w = wave_canvas.winfo_width() or 220
            h = 50
            mid = h // 2
            samples = audio.flatten().astype(float) / 32768.0
            peak = max(abs(samples.max()), abs(samples.min()), 0.001)
            samples = samples / peak
            block_size = max(1, len(samples) // w)
            for i in range(w):
                start_s = i * block_size
                end_s = min(start_s + block_size, len(samples))
                block = samples[start_s:end_s]
                if len(block) > 0:
                    y1 = mid - int(block.max() * (mid - 2))
                    y2 = mid - int(block.min() * (mid - 2))
                    wave_canvas.create_line(i, y1, i, y2, fill=color, width=1)

            status_lbl.configure(text=f"\u2714 Salvo! {duration:.1f}s", text_color="#44cc88")
            time_lbl.configure(text=f"{int(duration)//60:02d}:{duration%60:04.1f}")
            rec_btn.configure(text="\u25cf GRAVAR NOVO", fg_color=color,
                              border_color=color, text_color="#0a0a0f",
                              command=start_rec)
            cancel_btn.configure(state="normal", text="VOLTAR")

        def cancel():
            if state["recording"]:
                state["recording"] = False
                if state["wave_job"]:
                    p.after_cancel(state["wave_job"])
                if state["stream"]:
                    state["stream"].stop()
                    state["stream"].close()
            self._editor_char_id = None
            self._refresh_char_list()

        rec_btn = ctk.CTkButton(p, text="\u25cf REC", command=start_rec, height=36,
                                font=("Segoe UI", 12, "bold"), fg_color=color,
                                border_color=color, border_width=2,
                                text_color="#0a0a0f", hover_color="#ffd700")
        rec_btn.pack(fill="x", padx=8, pady=(8, 4))

        cancel_btn = ctk.CTkButton(p, text="CANCELAR", command=cancel, height=28,
                                   font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                                   border_color=C["border"], border_width=1,
                                   text_color=C["text3"], hover_color=C["card_hover"])
        cancel_btn.pack(fill="x", padx=8, pady=(0, 8))

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

    # ============================================================
    # AMBIENTAÇÃO (pasta de imagens de referência para Wan TI2V)
    # ============================================================


    def _open_voice_profile_popup(self, char):
        """Abre Voice Profile inline no editor de personagem."""
        from makevid.ui.menus import _ToolTip
        from makevid.core.voice_engine import VoiceProfile, VOICE_PRESETS, DEFAULT_EMOTIONS, EmotionModifier
        from makevid.core.tts_provider import get_available_voices

        # Carregar profile
        profile = VoiceProfile.from_dict(char.voice_profile) if char.voice_profile else VoiceProfile()
        if char.voice_id and not char.voice_profile:
            profile.voice_id = char.voice_id

        # Limpar editor e construir Voice Profile inline
        ed = self._char_editor
        for w in ed.winfo_children():
            w.destroy()
        self._editor_char_id = None

        # Header com botao voltar
        hdr = ctk.CTkFrame(ed, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkButton(hdr, text="\u2190 VOLTAR", width=80, height=26,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["border"], border_width=1,
                      text_color=C["text2"], hover_color=C["card_hover"],
                      command=lambda: self._select_char(char)).pack(side="left")
        ctk.CTkLabel(hdr, text="\U0001f3a4 VOICE PROFILE", font=("Segoe UI", 12, "bold"),
                     text_color=C["gold"]).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(hdr, text=char.name or "", font=("Segoe UI", 10),
                     text_color=C["cyan"]).pack(side="left", padx=(8, 0))

        ctk.CTkFrame(ed, height=1, fg_color=C["gold"]).pack(fill="x", padx=12, pady=(4, 8))

        # O editor ja e scrollable, usar ele como container
        scroll = ed

        # === ENGINE SELECTOR ===
        eng_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        eng_frame.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(eng_frame, text="ENGINE", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))

        engine_var = ctk.StringVar(value=profile.engine)
        engines = ["edge-tts", "bark", "xtts", "parler", "elevenlabs"]
        for eng in engines:
            is_sel = eng == profile.engine
            btn = ctk.CTkButton(eng_frame, text=eng.upper(), width=80, height=24,
                      font=("Segoe UI", 8, "bold"),
                      fg_color=C["cyan"] if is_sel else C["card"],
                      text_color="#0a0a0f" if is_sel else C["text3"],
                      border_color=C["cyan"], border_width=1,
                      hover_color="#0a3a3a",
                      command=lambda e=eng: engine_var.set(e))
            btn.pack(side="left", padx=2)

        # === TIMBRE ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["gold"]).pack(fill="x", padx=12, pady=(8, 4))
        timbre_header = ctk.CTkFrame(scroll, fg_color="transparent")
        timbre_header.pack(fill="x", padx=12)
        ctk.CTkLabel(timbre_header, text="TIMBRE (voz base)", text_color=C["gold"],
                     font=("Segoe UI", 10, "bold")).pack(side="left")

        timbre_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                     border_color=C["border"], border_width=1)
        timbre_frame.pack(fill="x", padx=12, pady=(4, 6))

        # Voice ID selector
        voice_row = ctk.CTkFrame(timbre_frame, fg_color="transparent")
        voice_row.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(voice_row, text="Voz:", text_color=C["text2"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))

        voices_pt = get_available_voices("pt-BR")
        voices_en = get_available_voices("en-US")
        all_voices = [v["ShortName"] for v in voices_pt + voices_en] if (voices_pt or voices_en) else [
            "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural",
            "en-US-ChristopherNeural", "en-US-RogerNeural", "en-US-GuyNeural",
            "en-US-EricNeural", "en-US-BrianNeural", "en-US-SteffanNeural",
            "en-US-AndrewNeural", "en-US-JennyNeural", "en-US-AriaNeural",
            "en-US-AvaNeural", "en-US-EmmaNeural", "en-US-MichelleNeural", "en-US-AnaNeural",
        ]
        voice_id_var = ctk.StringVar(value=profile.voice_id)
        ctk.CTkOptionMenu(voice_row, variable=voice_id_var, values=all_voices,
                          fg_color=C["input"], button_color=C["cyan"],
                          text_color=C["text"], font=("Segoe UI", 9),
                          dropdown_fg_color=C["card"], dropdown_text_color=C["text"],
                          width=280, height=26).pack(side="left", padx=(0, 8))

        # Preview button
        def _preview_voice():
            import threading
            from makevid.core.tts_provider import generate_voice, play_audio, stop_audio
            from makevid.config import AUDIO_DIR
            stop_audio()
            name = char.name or "personagem"
            text = f"Ola, eu sou {name}. Esta e a minha voz."
            path = AUDIO_DIR / "_voice_preview.wav"

            def run():
                generate_voice(text, path, voice_id=voice_id_var.get())
                play_audio(path)
            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(voice_row, text="\u25b6", width=30, height=24,
                      font=("Segoe UI", 10), fg_color=C["card"],
                      border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      command=_preview_voice).pack(side="left")

        # Language / Gender
        lang_row = ctk.CTkFrame(timbre_frame, fg_color="transparent")
        lang_row.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkLabel(lang_row, text="Idioma:", text_color=C["text3"],
                     font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        lang_var = ctk.StringVar(value=profile.language)
        ctk.CTkOptionMenu(lang_row, variable=lang_var,
                          values=["pt-BR", "en-US", "es-ES", "fr-FR"],
                          fg_color=C["input"], button_color=C["border"],
                          text_color=C["text"], font=("Segoe UI", 8),
                          width=80, height=22).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(lang_row, text="Genero:", text_color=C["text3"],
                     font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        gender_var = ctk.StringVar(value=profile.gender)
        ctk.CTkOptionMenu(lang_row, variable=gender_var,
                          values=["male", "female"],
                          fg_color=C["input"], button_color=C["border"],
                          text_color=C["text"], font=("Segoe UI", 8),
                          width=80, height=22).pack(side="left")

        # === PARAMETROS DE VOZ (sliders) ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(scroll, text="PARAMETROS DE VOZ", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12)

        sliders_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                      border_color=C["border"], border_width=1)
        sliders_frame.pack(fill="x", padx=12, pady=(4, 6))

        slider_vars = {}

        def _make_slider(parent, label, hint, var_name, from_val, to_val, default, unit=""):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            lbl = ctk.CTkLabel(row, text=label, text_color=C["text2"],
                         font=("Segoe UI", 9), width=100, anchor="w")
            lbl.pack(side="left")
            _ToolTip(lbl, hint)

            var = ctk.DoubleVar(value=default)
            slider = ctk.CTkSlider(row, from_=from_val, to=to_val, variable=var,
                                    width=280, height=16,
                                    fg_color=C["input"], progress_color=C["cyan"],
                                    button_color=C["gold"], button_hover_color="#ffd700")
            slider.pack(side="left", padx=(4, 8))

            val_lbl = ctk.CTkLabel(row, text=f"{int(default)}{unit}", text_color=C["cyan"],
                         font=("Consolas", 9, "bold"), width=50)
            val_lbl.pack(side="left")
            var.trace_add("write", lambda *_: val_lbl.configure(text=f"{int(var.get())}{unit}"))

            slider_vars[var_name] = var
            return var

        _make_slider(sliders_frame, "TOM (pitch)", "Grave (-20) a Agudo (+20)\nAltera a frequencia base da voz.",
                     "pitch_base", -20, 20, profile.pitch_base, "Hz")
        _make_slider(sliders_frame, "VELOCIDADE", "Lento (-50%) a Rapido (+50%)\nQuao rapido o personagem fala normalmente.",
                     "rate_base", -50, 50, profile.rate_base, "%")
        _make_slider(sliders_frame, "VOLUME", "Volume base da voz (50-150%).",
                     "volume_base", 50, 150, profile.volume_base, "%")

        # === POST-PROCESSING ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(6, 4))
        pp_lbl = ctk.CTkLabel(scroll, text="POST-PROCESSING (simulacao de timbre)", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold"))
        pp_lbl.pack(anchor="w", padx=12)
        _ToolTip(pp_lbl, "Efeitos aplicados no audio APOS a geracao.\\n"
                 "Funciona com qualquer engine.\\n"
                 "Simula caracteristicas vocais via processamento de sinal.")

        pp_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                 border_color=C["border"], border_width=1)
        pp_frame.pack(fill="x", padx=12, pady=(4, 6))

        _make_slider(pp_frame, "RESPIRACAO", "Limpa (0) a Ofegante (100)\nAdiciona ruido de ar na voz.\nBom para: personagens cansados, sensuais.",
                     "breathiness", 0, 100, profile.breathiness, "%")
        _make_slider(pp_frame, "ASPEREZA", "Suave (0) a Rouca (100)\nAdiciona distorcao/saturacao leve.\nBom para: guerreiros, idosos, fumantes.",
                     "roughness", 0, 100, profile.roughness, "%")
        _make_slider(pp_frame, "ENFASE", "Neutra (0) a Dramatica (100)\nIntensidade da entrega vocal.\nBom para: narradores, viloes, discursos.",
                     "emphasis", 0, 100, profile.emphasis, "%")

        # === EMOCOES ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(6, 4))
        em_lbl = ctk.CTkLabel(scroll, text="EMOCOES (modificadores por cena)", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold"))
        em_lbl.pack(anchor="w", padx=12)
        _ToolTip(em_lbl, "Cada emocao modifica a voz base automaticamente.\\n"
                 "A emocao e lida do campo EMOCAO no storyboard.\\n\\n"
                 "Clique numa emocao para ver/editar seus parametros.\\n"
                 "Os valores default funcionam bem para a maioria dos casos.")

        emotions_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                       border_color=C["border"], border_width=1)
        emotions_frame.pack(fill="x", padx=12, pady=(4, 6))

        # Emotion cards (grid)
        emotion_names = list(DEFAULT_EMOTIONS.keys())
        emotion_labels = {
            "neutral": "NEUTRO", "fear": "MEDO", "anger": "RAIVA",
            "sadness": "TRISTE", "whisper": "SUSSURRO", "shout": "GRITO",
            "sarcasm": "SARCASMO", "despair": "DESESPERO", "joy": "ALEGRIA",
            "seduction": "SEDUCAO", "fatigue": "CANSACO", "tension": "TENSAO",
            "relief": "ALIVIO",
        }
        emotion_colors = {
            "neutral": C["text2"], "fear": "#aa44ff", "anger": "#ff4444",
            "sadness": "#4488ff", "whisper": "#888888", "shout": "#ff8800",
            "sarcasm": "#ffcc00", "despair": "#ff00ff", "joy": "#44ff44",
            "seduction": "#ff6699", "fatigue": "#886644", "tension": "#ff6600",
            "relief": "#44ccaa",
        }

        cards_frame = ctk.CTkFrame(emotions_frame, fg_color="transparent")
        cards_frame.pack(fill="x", padx=8, pady=(8, 4))

        selected_emotion_var = ctk.StringVar(value="neutral")
        emotion_detail_frame = ctk.CTkFrame(emotions_frame, fg_color=C["panel"],
                                             corner_radius=4, border_color=C["border"], border_width=1)
        emotion_detail_frame.pack(fill="x", padx=8, pady=(0, 8))

        # Vars para emoção selecionada
        em_slider_vars = {}

        def _show_emotion_detail(em_name):
            selected_emotion_var.set(em_name)
            for w in emotion_detail_frame.winfo_children():
                w.destroy()

            em = DEFAULT_EMOTIONS.get(em_name, EmotionModifier())
            # Check custom override
            if em_name in profile.custom_emotions:
                em = EmotionModifier(**profile.custom_emotions[em_name])

            clr = emotion_colors.get(em_name, C["text2"])
            ctk.CTkLabel(emotion_detail_frame, text=f"CONFIG: {emotion_labels.get(em_name, em_name.upper())}",
                         text_color=clr, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 4))

            em_slider_vars.clear()

            def _em_slider(label, var_name, from_v, to_v, val, unit=""):
                r = ctk.CTkFrame(emotion_detail_frame, fg_color="transparent")
                r.pack(fill="x", padx=8, pady=2)
                ctk.CTkLabel(r, text=label, text_color=C["text3"], font=("Segoe UI", 8),
                             width=70, anchor="w").pack(side="left")
                v = ctk.DoubleVar(value=val)
                ctk.CTkSlider(r, from_=from_v, to=to_v, variable=v, width=220, height=14,
                              fg_color=C["input"], progress_color=clr,
                              button_color=clr, button_hover_color="#ffffff").pack(side="left", padx=4)
                vl = ctk.CTkLabel(r, text=f"{int(val)}{unit}", text_color=clr,
                             font=("Consolas", 8, "bold"), width=45)
                vl.pack(side="left")
                v.trace_add("write", lambda *_: vl.configure(text=f"{int(v.get())}{unit}"))
                em_slider_vars[var_name] = v

            _em_slider("Pitch", "pitch_delta", -20, 20, em.pitch_delta, "Hz")
            _em_slider("Rate", "rate_delta", -50, 50, em.rate_delta, "%")
            _em_slider("Volume", "volume_delta", -50, 50, em.volume_delta, "%")
            _em_slider("Tremor", "tremor", 0, 100, em.tremor, "%")
            _em_slider("Pausas", "pausas", 0, 100, em.pausas, "%")
            _em_slider("Quebras", "quebras", 0, 100, em.quebras, "%")
            _em_slider("Intensidade", "intensidade", 0, 100, em.intensidade, "%")

            # Bark tags
            if em.bark_tags:
                ctk.CTkLabel(emotion_detail_frame, text=f"  Bark tags: {' '.join(em.bark_tags)}",
                             text_color=C["text3"], font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(2, 6))

        # Criar cards de emoção
        row_frame = None
        for i, em_name in enumerate(emotion_names):
            if i % 5 == 0:
                row_frame = ctk.CTkFrame(cards_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=2)

            clr = emotion_colors.get(em_name, C["text2"])
            label = emotion_labels.get(em_name, em_name.upper())
            btn = ctk.CTkButton(row_frame, text=label, width=85, height=28,
                      font=("Segoe UI", 8, "bold"),
                      fg_color=C["panel"], border_color=clr, border_width=1,
                      text_color=clr, hover_color="#1a1a2a",
                      command=lambda n=em_name: _show_emotion_detail(n))
            btn.pack(side="left", padx=2)

        _show_emotion_detail("neutral")

        # === TESTE ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(scroll, text="TESTE", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12)

        test_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                   border_color=C["cyan"], border_width=1)
        test_frame.pack(fill="x", padx=12, pady=(4, 6))

        test_text_var = ctk.StringVar(value="Eu preciso sair daqui... agora!")
        ctk.CTkEntry(test_frame, textvariable=test_text_var, fg_color=C["input"],
                     border_color=C["border"], border_width=2, text_color=C["cyan"],
                     font=("Consolas", 11, "bold"), height=30, corner_radius=8,
                     placeholder_text="Texto para testar...").pack(fill="x", padx=8, pady=(8, 4))

        test_em_row = ctk.CTkFrame(test_frame, fg_color="transparent")
        test_em_row.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(test_em_row, text="Emocao:", text_color=C["text3"],
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        test_emotion_var = ctk.StringVar(value="NEUTRO")
        ctk.CTkOptionMenu(test_em_row, variable=test_emotion_var,
                          values=list(emotion_labels.values()),
                          fg_color=C["input"], button_color=C["cyan"],
                          text_color=C["text"], font=("Segoe UI", 9),
                          dropdown_fg_color=C["card"], dropdown_text_color=C["text"],
                          width=120, height=24).pack(side="left")

        test_btn_row = ctk.CTkFrame(test_frame, fg_color="transparent")
        test_btn_row.pack(fill="x", padx=8, pady=(0, 8))

        def _do_test():
            import threading
            from makevid.core.voice_engine import VoiceProfile, build_speech_params
            from makevid.core.tts_provider import generate_voice as gen_v, stop_audio
            from makevid.config import AUDIO_DIR

            # Parar audio anterior
            stop_audio()

            # Construir profile dos valores atuais
            p = _collect_profile()
            text = test_text_var.get() or "Teste de voz."
            # Mapear label PT → key EN
            em_label = test_emotion_var.get()
            em_key = "neutral"
            for k, v in emotion_labels.items():
                if v == em_label:
                    em_key = k
                    break
            params = build_speech_params(p, text, em_key)

            def run():
                from makevid.core.tts_provider import play_audio
                path = AUDIO_DIR / "_voice_test.wav"
                result = gen_v(text, path, voice_profile=params)
                if result:
                    play_audio(path)
            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(test_btn_row, text="\u25b6 OUVIR", width=80, height=28,
                      font=("Segoe UI", 9, "bold"), fg_color=C["cyan"],
                      text_color="#0a0a0f", hover_color="#00ffee",
                      command=_do_test).pack(side="left", padx=(0, 4))

        def _do_compare():
            """Salva config atual como slot de comparacao."""
            p = _collect_profile()
            text = test_text_var.get() or "Teste de voz."
            em_label = test_emotion_var.get()
            em_key = "neutral"
            for k, v in emotion_labels.items():
                if v == em_label:
                    em_key = k
                    break
            slot = {
                "name": f"Slot {len(compare_slots) + 1}",
                "profile": p,
                "text": text,
                "emotion": em_key,
                "emotion_label": em_label,
            }
            compare_slots.append(slot)
            _refresh_compare_slots()

        compare_slots = []

        ctk.CTkButton(test_btn_row, text="+ GUARDAR CONFIG", width=140, height=28,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["gold"], border_width=1,
                      text_color=C["gold"], hover_color="#2a2a0a",
                      command=_do_compare).pack(side="left", padx=(0, 4))

        # === SLOTS DE COMPARACAO ===
        compare_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                      border_color=C["border"], border_width=1)
        compare_frame.pack(fill="x", padx=12, pady=(4, 6))

        compare_slots_container = ctk.CTkFrame(compare_frame, fg_color="transparent")
        compare_slots_container.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(compare_slots_container, text="Nenhuma config salva. Ajuste os parametros e clique + GUARDAR CONFIG.",
                     text_color=C["text3"], font=("Segoe UI", 8)).pack(anchor="w")

        def _refresh_compare_slots():
            for w in compare_slots_container.winfo_children():
                w.destroy()
            if not compare_slots:
                ctk.CTkLabel(compare_slots_container, text="Nenhuma config salva.",
                             text_color=C["text3"], font=("Segoe UI", 8)).pack(anchor="w")
                return

            for idx, slot in enumerate(compare_slots):
                row = ctk.CTkFrame(compare_slots_container, fg_color=C["panel"],
                                    corner_radius=4, border_color=C["border"], border_width=1)
                row.pack(fill="x", pady=2)
                inner = ctk.CTkFrame(row, fg_color="transparent")
                inner.pack(fill="x", padx=6, pady=4)

                # Nome editavel
                name_var = ctk.StringVar(value=slot["name"])
                name_entry = ctk.CTkEntry(inner, textvariable=name_var, width=100, height=22,
                             fg_color=C["input"], border_width=0,
                             text_color=C["gold"], font=("Segoe UI", 9, "bold"))
                name_entry.pack(side="left", padx=(0, 4))
                name_var.trace_add("write", lambda *_, i=idx, v=name_var: _rename_slot(i, v))

                # Info
                voice_short = slot["profile"].voice_id.split("-")[-1].replace("Neural", "")[:10]
                info_text = f"{voice_short} | {slot['emotion_label']} | {slot['profile'].pitch_base:+d}Hz {slot['profile'].rate_base:+d}%"
                ctk.CTkLabel(inner, text=info_text, text_color=C["text3"],
                             font=("Segoe UI", 8)).pack(side="left", padx=(4, 0))

                # Botao ouvir
                ctk.CTkButton(inner, text="\u25b6", width=28, height=22,
                              font=("Segoe UI", 9), fg_color=C["cyan"],
                              text_color="#0a0a0f", hover_color="#00ffee",
                              command=lambda i=idx: _play_slot(i)).pack(side="right", padx=(4, 0))

                # Botao remover
                ctk.CTkButton(inner, text="\u2715", width=22, height=22,
                              font=("Segoe UI", 8), fg_color="transparent",
                              text_color="#ff4444", hover_color="#2a0808",
                              command=lambda i=idx: _remove_slot(i)).pack(side="right")

        def _rename_slot(idx, var):
            if idx < len(compare_slots):
                compare_slots[idx]["name"] = var.get()

        def _play_slot(idx):
            import threading
            from makevid.core.voice_engine import build_speech_params
            from makevid.core.tts_provider import generate_voice as gen_v, play_audio, stop_audio
            from makevid.config import AUDIO_DIR

            stop_audio()
            slot = compare_slots[idx]
            params = build_speech_params(slot["profile"], slot["text"], slot["emotion"])

            def run():
                path = AUDIO_DIR / f"_voice_slot_{idx}.wav"
                result = gen_v(slot["text"], path, voice_profile=params)
                if result:
                    play_audio(path)
            threading.Thread(target=run, daemon=True).start()

        def _remove_slot(idx):
            if idx < len(compare_slots):
                compare_slots.pop(idx)
                _refresh_compare_slots()

        # === PRESETS ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(scroll, text="PRESETS RAPIDOS", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12)

        presets_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                      border_color=C["border"], border_width=1)
        presets_frame.pack(fill="x", padx=12, pady=(4, 6))

        preset_labels = {
            "heroi_grave": "Heroi Grave", "vilao_sombrio": "Vilao Sombrio",
            "jovem_nervoso": "Jovem Nervoso", "ancia_sabia": "Ancia Sabia",
            "crianca": "Crianca", "narrador_epico": "Narrador Epico",
            "soldado_cansado": "Soldado Cansado", "femme_fatale": "Femme Fatale",
        }

        def _apply_preset(preset_key):
            preset = VOICE_PRESETS[preset_key]
            voice_id_var.set(preset.voice_id)
            engine_var.set(preset.engine)
            lang_var.set(preset.language)
            gender_var.set(preset.gender)
            slider_vars["pitch_base"].set(preset.pitch_base)
            slider_vars["rate_base"].set(preset.rate_base)
            slider_vars["volume_base"].set(preset.volume_base)
            slider_vars["breathiness"].set(preset.breathiness)
            slider_vars["roughness"].set(preset.roughness)
            slider_vars["emphasis"].set(preset.emphasis)

        preset_row = None
        for i, (key, label) in enumerate(preset_labels.items()):
            if i % 4 == 0:
                preset_row = ctk.CTkFrame(presets_frame, fg_color="transparent")
                preset_row.pack(fill="x", padx=8, pady=3)
            ctk.CTkButton(preset_row, text=label, width=110, height=26,
                          font=("Segoe UI", 8, "bold"), fg_color=C["panel"],
                          border_color=C["gold"], border_width=1,
                          text_color=C["gold"], hover_color="#2a2a0a",
                          command=lambda k=key: _apply_preset(k)).pack(side="left", padx=2)

        # === AMOSTRA DE VOZ (XTTS) ===
        ctk.CTkFrame(scroll, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkLabel(scroll, text="AMOSTRA DE VOZ (para XTTS/clone)", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12)

        sample_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4,
                                     border_color=C["border"], border_width=1)
        sample_frame.pack(fill="x", padx=12, pady=(4, 6))

        sample_path_var = ctk.StringVar(value=profile.voice_sample_path or char.voice_sample or "")
        sample_row = ctk.CTkFrame(sample_frame, fg_color="transparent")
        sample_row.pack(fill="x", padx=8, pady=8)

        sample_lbl = ctk.CTkLabel(sample_row,
            text=Path(sample_path_var.get()).name if sample_path_var.get() else "Nenhuma amostra",
            text_color=C["text3"] if not sample_path_var.get() else "#44cc88",
            font=("Segoe UI", 9))
        sample_lbl.pack(side="left", padx=(0, 8))

        def _import_sample():
            path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3 *.ogg")])
            if path:
                sample_path_var.set(path)
                sample_lbl.configure(text=Path(path).name, text_color="#44cc88")

        ctk.CTkButton(sample_row, text="Importar", width=65, height=24,
                      font=("Segoe UI", 8, "bold"), fg_color=C["card"],
                      border_color=C["border"], border_width=1,
                      text_color=C["text2"], hover_color=C["card_hover"],
                      command=_import_sample).pack(side="left", padx=(0, 4))
        ctk.CTkButton(sample_row, text="\u25cf Gravar", width=65, height=24,
                      font=("Segoe UI", 8, "bold"), fg_color="#2a0808",
                      border_color="#ff4444", border_width=1,
                      text_color="#ff4444", hover_color="#3a1010",
                      command=lambda: self._record_voice_sample(char)).pack(side="left")

        # === BOTOES FINAIS ===
        ctk.CTkFrame(scroll, height=2, fg_color=C["gold"]).pack(fill="x", padx=12, pady=(10, 6))

        def _collect_profile() -> VoiceProfile:
            """Coleta todos os valores da UI e retorna VoiceProfile."""
            p = VoiceProfile(
                engine=engine_var.get(),
                voice_id=voice_id_var.get(),
                language=lang_var.get(),
                gender=gender_var.get(),
                pitch_base=int(slider_vars["pitch_base"].get()),
                rate_base=int(slider_vars["rate_base"].get()),
                volume_base=int(slider_vars["volume_base"].get()),
                breathiness=int(slider_vars["breathiness"].get()),
                roughness=int(slider_vars["roughness"].get()),
                emphasis=int(slider_vars["emphasis"].get()),
                bark_speaker=profile.bark_speaker,
                voice_sample_path=sample_path_var.get(),
                voice_description=profile.voice_description,
                elevenlabs_voice_id=profile.elevenlabs_voice_id,
                elevenlabs_stability=profile.elevenlabs_stability,
                elevenlabs_similarity=profile.elevenlabs_similarity,
                elevenlabs_style=profile.elevenlabs_style,
            )
            # Salvar custom emotions se editadas
            em_key = selected_emotion_var.get()
            if em_slider_vars:
                custom = {
                    "name": em_key,
                    "pitch_delta": int(em_slider_vars.get("pitch_delta", ctk.DoubleVar(value=0)).get()),
                    "rate_delta": int(em_slider_vars.get("rate_delta", ctk.DoubleVar(value=0)).get()),
                    "volume_delta": int(em_slider_vars.get("volume_delta", ctk.DoubleVar(value=0)).get()),
                    "tremor": int(em_slider_vars.get("tremor", ctk.DoubleVar(value=0)).get()),
                    "pausas": int(em_slider_vars.get("pausas", ctk.DoubleVar(value=0)).get()),
                    "quebras": int(em_slider_vars.get("quebras", ctk.DoubleVar(value=0)).get()),
                    "intensidade": int(em_slider_vars.get("intensidade", ctk.DoubleVar(value=70)).get()),
                }
                p.custom_emotions[em_key] = custom
            return p

        def _save_and_close():
            p = _collect_profile()
            char.voice_profile = p.to_dict()
            char.voice_id = p.voice_id
            char.voice_sample = p.voice_sample_path
            self.app.project.save(PROJECTS_DIR)
            self._editor_char_id = None  # Forçar rebuild da ficha
            self._refresh_char_list()
            self._select_char(char)

        final_row = ctk.CTkFrame(scroll, fg_color="transparent")
        final_row.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(final_row, text="\u2714 SALVAR VOICE PROFILE", height=36,
                      font=("Segoe UI", 11, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700",
                      command=_save_and_close).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(final_row, text="CANCELAR", height=36, width=100,
                      font=("Segoe UI", 9, "bold"), fg_color=C["card"],
                      border_color=C["border"], border_width=1,
                      text_color=C["text3"], hover_color=C["card_hover"],
                      command=lambda: self._select_char(char)).pack(side="right")
