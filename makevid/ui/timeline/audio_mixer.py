"""Audio Mixer - Painel de mixagem profissional para itens de audio."""

import numpy as np
import wave
import customtkinter as ctk
from pathlib import Path
from makevid.ui.theme import C


class AudioMixer:
    """Constroi e gerencia painel de mixagem de audio."""

    def __init__(self, fx_panel):
        self.fx_panel = fx_panel
        self._mixer_item = None
        self._mixer_params = {}

    @property
    def item(self):
        return self._mixer_item

    def build(self, frame, item):
        """Constroi painel de mixagem de audio profissional."""
        from makevid.config import PROJECTS_DIR
        p = frame
        self._mixer_item = item
        self._mixer_params = {}

        header = ctk.CTkFrame(p, fg_color="transparent", height=32)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="MIXER", font=("Segoe UI", 13, "bold"), text_color=C["cyan"]).pack(side="left")
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=self.fx_panel.hide).pack(side="right")

        ctk.CTkFrame(p, height=2, fg_color=C["cyan"]).pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkLabel(p, text=item.name, font=("Segoe UI", 10, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=12, pady=(0, 4))
        ctk.CTkLabel(p, text=f"{item.duration:.1f}s | Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w", padx=12, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                        scrollbar_button_color=C["cyan"],
                                        scrollbar_button_hover_color="#00ffee")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        from makevid.ui.menus import _ToolTip

        # VOLUME
        vol_lbl = ctk.CTkLabel(scroll, text="VOLUME", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        vol_lbl.pack(anchor="w", padx=4, pady=(4, 0))
        _ToolTip(vol_lbl, "Volume do audio de 0% a 200%.\n100% = volume original.")
        self._mixer_params["volume"] = self._slider(scroll, "", 0, 200, 100, "%", C["cyan"])

        # PAN
        pan_lbl_title = ctk.CTkLabel(scroll, text="PAN (L/R)", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        pan_lbl_title.pack(anchor="w", padx=4, pady=(4, 2))
        _ToolTip(pan_lbl_title, "Posicao estereo.\nL = esquerdo, R = direito.")
        pan_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4)
        pan_frame.pack(fill="x", padx=4, pady=(0, 8))
        pan_row = ctk.CTkFrame(pan_frame, fg_color="transparent")
        pan_row.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(pan_row, text="L", font=("Consolas", 8, "bold"), text_color=C["text3"]).pack(side="left")
        pan_slider = ctk.CTkSlider(pan_row, from_=-100, to=100, number_of_steps=200,
                                    fg_color=C["border"], progress_color=C["cyan"],
                                    button_color=C["cyan"], button_hover_color="#00ffee")
        pan_slider.set(0)
        pan_slider.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(pan_row, text="R", font=("Consolas", 8, "bold"), text_color=C["text3"]).pack(side="left")
        pan_lbl = ctk.CTkLabel(pan_frame, text="Centro", font=("Consolas", 9), text_color=C["text3"])
        pan_lbl.pack(padx=8, pady=(0, 6))
        pan_slider.configure(command=lambda v: pan_lbl.configure(
            text="Centro" if int(v) == 0 else f"L {abs(int(v))}%" if int(v) < 0 else f"R {int(v)}%"))
        self._mixer_params["pan"] = pan_slider

        # FADES
        fades_lbl = ctk.CTkLabel(scroll, text="FADES", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        fades_lbl.pack(anchor="w", padx=4, pady=(4, 2))
        fade_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4)
        fade_frame.pack(fill="x", padx=4, pady=(0, 8))
        self._mixer_params["fade_in"] = self._row_slider(fade_frame, "Fade In", 0, 5.0, 0, "s", "#6b3fa0")
        self._mixer_params["fade_out"] = self._row_slider(fade_frame, "Fade Out", 0, 5.0, 0, "s", "#6b3fa0")
        ctk.CTkFrame(fade_frame, height=4, fg_color="transparent").pack()

        # PITCH
        pitch_lbl = ctk.CTkLabel(scroll, text="PITCH (semitons)", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        pitch_lbl.pack(anchor="w", padx=4, pady=(4, 0))
        self._mixer_params["pitch"] = self._slider(scroll, "", -12, 12, 0, "st", C["gold"], steps=24)

        # SPEED
        speed_lbl = ctk.CTkLabel(scroll, text="VELOCIDADE", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        speed_lbl.pack(anchor="w", padx=4, pady=(4, 0))
        self._mixer_params["speed"] = self._slider(scroll, "", 25, 400, 100, "x", C["gold"], steps=75,
                                                    fmt_fn=lambda v: f"{v/100:.2f}x")

        # EQ
        eq_lbl = ctk.CTkLabel(scroll, text="EQUALIZADOR", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        eq_lbl.pack(anchor="w", padx=4, pady=(4, 2))
        eq_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4)
        eq_frame.pack(fill="x", padx=4, pady=(0, 8))
        self._mixer_params["eq_low"] = self._row_slider(eq_frame, "Low", -12, 12, 0, "dB", "#ff6644")
        self._mixer_params["eq_mid"] = self._row_slider(eq_frame, "Mid", -12, 12, 0, "dB", "#ffcc44")
        self._mixer_params["eq_high"] = self._row_slider(eq_frame, "High", -12, 12, 0, "dB", "#44ccff")
        ctk.CTkFrame(eq_frame, height=4, fg_color="transparent").pack()

        # REVERB
        reverb_lbl = ctk.CTkLabel(scroll, text="REVERB", font=("Segoe UI", 9, "bold"), text_color=C["text2"])
        reverb_lbl.pack(anchor="w", padx=4, pady=(4, 0))
        self._mixer_params["reverb"] = self._slider(scroll, "", 0, 100, 0, "%", "#8855bb")

        # PREVIEW
        ctk.CTkButton(scroll, text="\u25b6 PREVIEW", height=28, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["cyan"], border_width=1,
                      text_color=C["cyan"], hover_color="#0a2a2a",
                      command=lambda: self._preview_audio(item)).pack(fill="x", padx=4, pady=(8, 4))

    def get_values(self):
        """Retorna valores atuais do mixer."""
        p = self._mixer_params
        return {
            "volume": p["volume"].get() / 100.0,
            "pan": p["pan"].get() / 100.0,
            "fade_in": p["fade_in"].get(),
            "fade_out": p["fade_out"].get(),
            "pitch": int(p["pitch"].get()),
            "speed": p["speed"].get() / 100.0,
            "eq_low": p["eq_low"].get(),
            "eq_mid": p["eq_mid"].get(),
            "eq_high": p["eq_high"].get(),
            "reverb": p["reverb"].get() / 100.0,
        }

    def process_audio(self, item):
        """Processa audio com todos os efeitos do mixer. Retorna (audio_array, sample_rate)."""
        if not item.file_path or not Path(item.file_path).exists():
            return None, 0

        with wave.open(item.file_path, "r") as wf:
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            if wf.getnchannels() == 2:
                audio = audio.reshape(-1, 2).mean(axis=1)

        original_dur = n_frames / sr
        if original_dur > 0 and abs(item.duration - original_dur) > 0.05:
            target_samples = int(item.duration * sr)
            if target_samples > 0:
                audio = np.interp(
                    np.linspace(0, len(audio) - 1, target_samples),
                    np.arange(len(audio)), audio)

        vals = self.get_values()

        # Speed
        if vals["speed"] != 1.0:
            new_len = int(len(audio) / vals["speed"])
            audio = np.interp(np.linspace(0, len(audio) - 1, new_len), np.arange(len(audio)), audio)

        # Pitch
        if vals["pitch"] != 0:
            factor = 2.0 ** (vals["pitch"] / 12.0)
            stretched_len = int(len(audio) / factor)
            pitched = np.interp(np.linspace(0, len(audio) - 1, stretched_len), np.arange(len(audio)), audio)
            if len(pitched) > len(audio):
                pitched = pitched[:len(audio)]
            else:
                pitched = np.pad(pitched, (0, len(audio) - len(pitched)))
            audio = pitched

        # EQ
        if vals["eq_low"] != 0 or vals["eq_mid"] != 0 or vals["eq_high"] != 0:
            try:
                from scipy.signal import butter, lfilter
                b, a = butter(2, 300 / (sr / 2), btype='low')
                low = lfilter(b, a, audio)
                b, a = butter(2, 3000 / (sr / 2), btype='high')
                high = lfilter(b, a, audio)
                mid = audio - low - high
                audio = (low * 10 ** (vals["eq_low"] / 20.0) +
                         mid * 10 ** (vals["eq_mid"] / 20.0) +
                         high * 10 ** (vals["eq_high"] / 20.0))
            except ImportError:
                pass

        # Volume
        audio = audio * vals["volume"]

        # Fade In/Out
        if vals["fade_in"] > 0:
            fade_samples = min(int(vals["fade_in"] * sr), len(audio))
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
        if vals["fade_out"] > 0:
            fade_samples = min(int(vals["fade_out"] * sr), len(audio))
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        # Pan
        pan = vals["pan"]
        stereo = np.column_stack([audio * min(1.0, 1.0 - pan), audio * min(1.0, 1.0 + pan)])

        # Reverb
        if vals["reverb"] > 0:
            reverb_len = int(0.3 * sr)
            impulse = np.exp(-np.linspace(0, 5, reverb_len))
            impulse = impulse / impulse.sum()
            wet_l = np.convolve(stereo[:, 0], impulse)[:len(audio)]
            wet_r = np.convolve(stereo[:, 1], impulse)[:len(audio)]
            mix = vals["reverb"]
            stereo[:, 0] = stereo[:, 0] * (1 - mix) + wet_l * mix
            stereo[:, 1] = stereo[:, 1] * (1 - mix) + wet_r * mix

        return np.clip(stereo, -1.0, 1.0), sr

    def _preview_audio(self, item):
        tl = self.fx_panel.timeline
        tl.playhead_pos = item.start_time
        tl.draw()
        audio, sr = self.process_audio(item)
        if audio is not None:
            try:
                import sounddevice as sd
                sd.play(audio, samplerate=sr)
            except Exception:
                pass
        player = tl.app.preview_panel.player
        tl.app.preview_panel._on_play_click(lambda: self.fx_panel._start_player_at_time(player, item.start_time))

    def _slider(self, parent, label, from_, to, default, unit, color, steps=100, fmt_fn=None):
        if label:
            ctk.CTkLabel(parent, text=label, font=("Segoe UI", 9, "bold"),
                         text_color=C["text2"]).pack(anchor="w", padx=4, pady=(4, 2))
        frame = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=4)
        frame.pack(fill="x", padx=4, pady=(0, 8))
        slider = ctk.CTkSlider(frame, from_=from_, to=to, number_of_steps=steps,
                                fg_color=C["border"], progress_color=color,
                                button_color=color, button_hover_color=color)
        slider.set(default)
        slider.pack(fill="x", padx=8, pady=(8, 2))
        if fmt_fn:
            lbl = ctk.CTkLabel(frame, text=fmt_fn(default), font=("Consolas", 9), text_color=C["text3"])
            slider.configure(command=lambda v: lbl.configure(text=fmt_fn(v)))
        else:
            lbl = ctk.CTkLabel(frame, text=f"{int(default)}{unit}", font=("Consolas", 9), text_color=C["text3"])
            slider.configure(command=lambda v: lbl.configure(text=f"{int(v)}{unit}"))
        lbl.pack(padx=8, pady=(0, 6))
        return slider

    def _row_slider(self, parent, label, from_, to, default, unit, color):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row, text=label, font=("Consolas", 8, "bold"), text_color=C["text3"], width=50).pack(side="left")
        slider = ctk.CTkSlider(row, from_=from_, to=to,
                                number_of_steps=int(abs(to - from_) * 10),
                                fg_color=C["border"], progress_color=color,
                                button_color=color, button_hover_color=color)
        slider.set(default)
        slider.pack(side="left", fill="x", expand=True, padx=4)
        val_lbl = ctk.CTkLabel(row, text=f"{default:.1f}{unit}" if isinstance(default, float) else f"{default}{unit}",
                                font=("Consolas", 8), text_color=C["text3"], width=40)
        val_lbl.pack(side="left")
        if isinstance(from_, float):
            slider.configure(command=lambda v: val_lbl.configure(text=f"{v:.1f}{unit}"))
        else:
            slider.configure(command=lambda v: val_lbl.configure(text=f"{int(v)}{unit}"))
        return slider
