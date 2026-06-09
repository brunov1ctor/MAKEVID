"""Recorder - Gravacao de microfone e adicao na timeline."""

import time
import threading
import numpy as np
import wave
import customtkinter as ctk
from makevid.ui.theme import C


class AudioRecorder:
    """Gravador de microfone com janela popup."""

    def __init__(self, fx_panel):
        self.fx_panel = fx_panel

    def open(self, track="voice"):
        """Constroi gravador integrado dentro do painel lateral."""
        import sounddevice as sd
        from makevid.config import AUDIO_DIR

        self._target_track = track
        fx = self.fx_panel
        tl = fx.timeline
        app = tl.app

        # Usa o painel lateral existente
        if fx._visible:
            fx.hide()
        app.generator_panel.container.pack_forget()
        fx._frame = ctk.CTkFrame(app._main, width=320, fg_color=C["panel"],
                                 border_color=C["gold"], border_width=1, corner_radius=6)
        fx._frame.pack(side="left", fill="y", padx=(0, 4), pady=4, before=app.preview_panel.panel)
        fx._frame.pack_propagate(False)
        fx._visible = True

        p = fx._frame
        color = {"voice": "#ff9944", "sfx": "#44cc88", "music": "#cc44aa", "audio": C["cyan"]}.get(track, C["cyan"])

        # Header
        header = ctk.CTkFrame(p, fg_color="transparent", height=32)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="\u25cf GRAVAR", font=("Segoe UI", 13, "bold"),
                     text_color=color).pack(side="left")
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=fx.hide).pack(side="right")
        ctk.CTkFrame(p, height=2, fg_color=color).pack(fill="x", padx=10, pady=(4, 8))

        # Timer
        time_lbl = ctk.CTkLabel(p, text="00:00.0", font=("Consolas", 28, "bold"),
                                text_color=C["text"])
        time_lbl.pack(pady=(10, 4))

        # Waveform canvas
        import tkinter as tk
        wave_canvas = tk.Canvas(p, height=60, bg="#080a14", highlightthickness=1,
                                highlightbackground=color)
        wave_canvas.pack(fill="x", padx=10, pady=(0, 8))

        # Status
        status_lbl = ctk.CTkLabel(p, text=f"Track: {track.upper()}",
                                  text_color=C["text3"], font=("Segoe UI", 9))
        status_lbl.pack(anchor="w", padx=12)

        state = {"recording": False, "frames": [], "start_time": 0,
                 "stream": None, "wave_job": None}
        SAMPLE_RATE = 44100
        CHANNELS = 1

        def update_time():
            if state["recording"]:
                elapsed = time.time() - state["start_time"]
                m = int(elapsed) // 60
                s = elapsed % 60
                time_lbl.configure(text=f"{m:02d}:{s:04.1f}")
                p.after(100, update_time)

        def draw_waveform():
            if not state["recording"]:
                return
            wave_canvas.delete("all")
            w = wave_canvas.winfo_width() or 280
            h = 60
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
                        val_max = block.max()
                        val_min = block.min()
                        y1 = mid - int(val_max * (mid - 2))
                        y2 = mid - int(val_min * (mid - 2))
                        wave_canvas.create_line(i, y1, i, y2, fill=color, width=1)
            else:
                wave_canvas.create_line(0, mid, w, mid, fill="#1a2a3a", width=1, dash=(2, 4))
            state["wave_job"] = p.after(50, draw_waveform)

        def start_rec():
            state["recording"] = True
            state["frames"] = []
            state["start_time"] = time.time()
            status_lbl.configure(text="\u25cf GRAVANDO...", text_color="#ff4444")
            rec_btn.configure(text="\u25a0 PARAR", fg_color="#2a0808",
                              border_color="#ff4444", text_color="#ff4444",
                              command=stop_rec)
            update_time()
            draw_waveform()

            def callback(indata, frames, t, status):
                if state["recording"]:
                    state["frames"].append(indata.copy())

            state["stream"] = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS,
                dtype="int16", callback=callback)
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
                return

            audio_data = np.concatenate(state["frames"], axis=0)
            duration = len(audio_data) / SAMPLE_RATE

            out_dir = AUDIO_DIR / app.project.id
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"rec_{int(time.time())}.wav"
            filepath = out_dir / filename

            with wave.open(str(filepath), "w") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())

            existing = tl.project.get_track_items(self._target_track)
            if existing:
                last = max(existing, key=lambda i: i.start_time + i.duration)
                start = last.start_time + last.duration
            else:
                start = tl.playhead_pos

            tl.project.add_track_item(
                name=f"Gravacao ({duration:.1f}s)", track=self._target_track,
                start_time=start, duration=duration, file_path=str(filepath))

            from makevid.config import PROJECTS_DIR
            tl.project.save(PROJECTS_DIR)
            tl.draw()

            # Desenhar waveform final
            wave_canvas.delete("all")
            w = wave_canvas.winfo_width() or 280
            h = 60
            mid = h // 2
            samples = audio_data.flatten().astype(float) / 32768.0
            peak = max(abs(samples.max()), abs(samples.min()), 0.001)
            samples = samples / peak
            block_size = max(1, len(samples) // w)
            for i in range(w):
                start_s = i * block_size
                end_s = min(start_s + block_size, len(samples))
                block = samples[start_s:end_s]
                if len(block) > 0:
                    val_max = block.max()
                    val_min = block.min()
                    y1 = mid - int(val_max * (mid - 2))
                    y2 = mid - int(val_min * (mid - 2))
                    wave_canvas.create_line(i, y1, i, y2, fill=color, width=1)

            status_lbl.configure(text=f"\u2714 Salvo! {duration:.1f}s → {track.upper()}", text_color=C["cyan"])
            time_lbl.configure(text=f"{int(duration)//60:02d}:{duration%60:04.1f}")
            rec_btn.configure(text="\u25cf GRAVAR NOVO", fg_color=color,
                              border_color=color, text_color="#0a0a0f",
                              command=start_rec)

        rec_btn = ctk.CTkButton(p, text="\u25cf REC", command=start_rec, height=44,
                                font=("Segoe UI", 14, "bold"), fg_color=color,
                                border_color=color, border_width=2,
                                text_color="#0a0a0f", hover_color="#ffd700")
        rec_btn.pack(fill="x", padx=10, pady=(10, 10))
