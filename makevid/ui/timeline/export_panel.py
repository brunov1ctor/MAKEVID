"""Export Panel - Painel de exportacao de video com audio mixado."""

import re
import shutil
import subprocess
import numpy as np
import wave
import customtkinter as ctk
from pathlib import Path
from makevid.ui.theme import C


class ExportPanel:
    """Constroi e gerencia painel de exportacao."""

    def __init__(self, fx_panel):
        self.fx_panel = fx_panel
        # Valores persistentes (sobrevivem ao fechar painel)
        self._saved_name = ""
        self._saved_tracks = {"video": True, "voice": True, "sfx": True, "music": True, "audio": True}
        self._saved_format = "MP4 (H.264)"

    def build(self, frame):
        """Constroi painel de exportacao."""
        p = frame
        app = self.fx_panel.timeline.app

        # Usar nome salvo ou nome do projeto
        if not self._saved_name:
            self._saved_name = app.project.name or "meu_video"

        self._track_vars = {
            k: ctk.BooleanVar(value=self._saved_tracks[k])
            for k in ["video", "voice", "sfx", "music", "audio"]
        }
        # Salvar ao mudar
        for k, var in self._track_vars.items():
            var.trace_add("write", lambda *a, key=k: self._save_track_state(key))

        # Header
        header = ctk.CTkFrame(p, fg_color="transparent", height=28)
        header.pack(fill="x", padx=8, pady=(8, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="EXPORTAR", font=("Segoe UI", 12, "bold"), text_color=C["gold"]).pack(side="left")
        ctk.CTkButton(header, text="X", width=24, height=20, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 9, "bold"),
                      command=self.fx_panel.hide).pack(side="right")
        ctk.CTkFrame(p, height=1, fg_color=C["gold"]).pack(fill="x", padx=8, pady=(4, 4))

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                        scrollbar_button_color=C["gold"],
                                        scrollbar_button_hover_color="#ffd700")
        scroll.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        total_dur = app.project.total_duration()
        clips = sorted(app.project.clips, key=lambda x: x.position)
        ctk.CTkLabel(scroll, text=f"{len(clips)} clips | {total_dur:.1f}s",
                     text_color=C["text3"], font=("Consolas", 9)).pack(anchor="w", padx=4, pady=(0, 4))

        # Nome do arquivo
        ctk.CTkLabel(scroll, text="Nome:", text_color=C["text2"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=4, pady=(0, 2))
        self._export_name_var = ctk.StringVar(value=self._saved_name)
        self._export_name_var.trace_add("write", lambda *a: setattr(self, '_saved_name', self._export_name_var.get()))
        name_entry = ctk.CTkEntry(scroll, textvariable=self._export_name_var, fg_color="#141828",
                     border_color=C["gold"], border_width=2, text_color="#ffffff",
                     font=("Segoe UI", 11, "bold"), height=34, corner_radius=4)
        name_entry.pack(fill="x", padx=4, pady=(0, 6))
        name_entry.after(100, lambda: name_entry.focus_force())

        # Tracks
        tracks_row = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4)
        tracks_row.pack(fill="x", padx=4, pady=(0, 6))
        ctk.CTkLabel(tracks_row, text="Tracks:", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"]).pack(anchor="w", padx=6, pady=(4, 2))
        track_info = [
            ("video", "VIDEO", "#3399ff"),
            ("voice", "VOICE", "#ff9944"),
            ("sfx", "SFX", "#44cc88"),
            ("music", "MUSIC", "#cc44aa"),
            ("audio", "AUDIO", "#0ac8b9"),
        ]
        for track_key, label, color in track_info:
            ctk.CTkCheckBox(tracks_row, text=label, variable=self._track_vars[track_key],
                            fg_color=color, hover_color=color,
                            text_color=C["text"], font=("Consolas", 9, "bold"),
                            checkmark_color="#0a0a0f",
                            height=20).pack(anchor="w", padx=6, pady=1)
        ctk.CTkFrame(tracks_row, height=3, fg_color="transparent").pack()

        # Formato
        fmt_row = ctk.CTkFrame(scroll, fg_color="transparent")
        fmt_row.pack(fill="x", padx=4, pady=(0, 6))
        ctk.CTkLabel(fmt_row, text="Formato:", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"]).pack(side="left", padx=(0, 6))
        self._format_var = ctk.StringVar(value=self._saved_format)
        self._format_var.trace_add("write", lambda *a: setattr(self, '_saved_format', self._format_var.get()))
        all_formats = [
            "MP4 (H.264)", "MP4 (H.265/HEVC)", "MOV (ProRes)",
            "WEBM (VP9)", "MKV (H.264)", "GIF (animado)", "PNG (sequencia)",
            "WAV (audio 16bit)", "WAV (audio 24bit)",
            "MP3 (320kbps)", "FLAC (lossless)", "OGG (Vorbis)",
        ]
        self._format_menu = ctk.CTkOptionMenu(fmt_row, variable=self._format_var,
                          values=all_formats,
                          fg_color=C["input"], button_color=C["purple"],
                          button_hover_color="#bb77ff",
                          text_color=C["text"], font=("Consolas", 9),
                          dropdown_fg_color=C["card"],
                          dropdown_hover_color=C["card_hover"],
                          dropdown_text_color=C["text"],
                          height=24)
        self._format_menu.pack(side="left", fill="x", expand=True)

        # Auto-update format
        def _update_format(*args):
            has_video = self._track_vars["video"].get()
            if has_video:
                opts = ["MP4 (H.264)", "MP4 (H.265/HEVC)", "MOV (ProRes)",
                        "WEBM (VP9)", "MKV (H.264)", "GIF (animado)", "PNG (sequencia)"]
            else:
                opts = ["WAV (audio 16bit)", "WAV (audio 24bit)",
                        "MP3 (320kbps)", "FLAC (lossless)", "OGG (Vorbis)"]
            self._format_menu.configure(values=opts)
            if self._format_var.get() not in opts:
                self._format_var.set(opts[0])
        for var in self._track_vars.values():
            var.trace_add("write", _update_format)
        _update_format()

        # Status (visivel durante export)
        self._export_status = ctk.CTkLabel(scroll, text="Use o botao EXPORTAR na timeline",
                     text_color=C["text3"], font=("Segoe UI", 9))
        self._export_status.pack(anchor="w", padx=4, pady=(4, 0))
        self._export_btn = None

    def _save_track_state(self, key):
        """Salva estado de uma track quando checkbox muda."""
        if hasattr(self, '_track_vars') and self._track_vars:
            self._saved_tracks[key] = self._track_vars[key].get()

    def _persist_state(self):
        """Salva todos os valores atuais."""
        if hasattr(self, '_export_name_var') and self._export_name_var:
            try:
                self._saved_name = self._export_name_var.get().strip()
            except Exception:
                pass
        if hasattr(self, '_track_vars') and self._track_vars:
            for k, v in self._track_vars.items():
                try:
                    self._saved_tracks[k] = v.get()
                except Exception:
                    pass
        if hasattr(self, '_format_var') and self._format_var:
            try:
                self._saved_format = self._format_var.get()
            except Exception:
                pass

    def get_export_name(self):
        """Retorna nome para export (persiste mesmo com painel fechado)."""
        return self._saved_name or "meu_video"

    def get_enabled_tracks(self):
        """Retorna tracks habilitadas (persiste mesmo com painel fechado)."""
        return [k for k, v in self._saved_tracks.items() if v and k != "video"]

    def _do_export(self):
        """Exporta timeline completa: video + audio mixado."""
        # Salvar estado atual antes de exportar
        self._persist_state()
        from makevid.config import OUTPUTS_DIR, PROJECTS_DIR
        from makevid.core.fx_processor import apply_fx_to_frame

        app = self.fx_panel.timeline.app
        clips = sorted(app.project.clips, key=lambda x: x.position)
        audio_items = app.project.get_track_items("audio")
        total_dur = app.project.total_duration()

        if total_dur <= 0:
            self._export_status.configure(text="Nada para exportar", text_color="#ff4444")
            return

        name = self._export_name_var.get().strip()
        if not name:
            self._export_status.configure(text="Digite um nome", text_color="#ff4444")
            return

        print(f"[Export] Iniciando: name='{name}', total_dur={total_dur:.1f}s")
        self._export_status.configure(text="Iniciando exportacao...", text_color=C["gold"])
        if hasattr(self, '_export_btn') and self._export_btn:
            self._export_btn.configure(state="disabled", text="EXPORTANDO...", fg_color="#3a2a0a")
        try:
            app.update()
        except Exception:
            pass

        try:
            safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') or "video_final"
            fps = app.project.output_fps or 16
            width = app.project.output_width or 832
            height = app.project.output_height or 480
            include_video = self._track_vars.get("video", ctk.BooleanVar(value=True)).get()
            fmt = self._format_var.get()
            audio_only = "audio only" in fmt
            video_only = "video only" in fmt

            import cv2
            import time as _time
            tmp_video = OUTPUTS_DIR / app.project.id / f"_tmp_{safe_name}.mp4"
            tmp_video.parent.mkdir(parents=True, exist_ok=True)

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(tmp_video), fourcc, fps, (width, height))

            fx_items = app.project.get_track_items("fx")
            video_dur = 0.0
            frame_count = 0
            total_frames_est = int(total_dur * fps)
            export_start = _time.time()
            for clip in clips:
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    cap = cv2.VideoCapture(str(clip.video_path))
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame = cv2.resize(frame, (width, height))
                        current_time = frame_count / fps
                        if fx_items:
                            frame_rgb = frame[:, :, ::-1]
                            frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, current_time, total_dur)
                            frame = frame_rgb[:, :, ::-1]
                        writer.write(frame)
                        frame_count += 1
                        # Atualizar progresso a cada 30 frames
                        if frame_count % 30 == 0 and total_frames_est > 0:
                            pct = int(frame_count / total_frames_est * 100)
                            elapsed = _time.time() - export_start
                            if frame_count > 0:
                                eta = int(elapsed / frame_count * (total_frames_est - frame_count))
                            else:
                                eta = 0
                            try:
                                self._export_status.configure(
                                    text=f"Video: {pct}% | ~{eta}s restantes")
                                app.update()
                            except Exception:
                                pass
                    cap.release()
                else:
                    num_frames = int(clip.duration * fps)
                    black = np.zeros((height, width, 3), dtype=np.uint8)
                    for _ in range(num_frames):
                        current_time = frame_count / fps
                        if fx_items:
                            black_rgb = apply_fx_to_frame(black.copy(), fx_items, current_time, total_dur)
                            writer.write(black_rgb[:, :, ::-1] if black_rgb.any() else black)
                        else:
                            writer.write(black)
                        frame_count += 1
                video_dur += clip.duration

            if total_dur > video_dur:
                extra_frames = int((total_dur - video_dur) * fps)
                black = np.zeros((height, width, 3), dtype=np.uint8)
                for _ in range(extra_frames):
                    writer.write(black)

            writer.release()

            # Audio mix (only enabled tracks)
            try:
                self._export_status.configure(text="Mixando audio...")
                app.update()
            except Exception:
                pass
            tmp_audio = None
            enabled_tracks = [k for k, v in self._track_vars.items() if v.get() and k != "video"]
            if enabled_tracks:
                all_track_items = []
                for track_name in enabled_tracks:
                    all_track_items.extend(app.project.get_track_items(track_name))
                if all_track_items:
                    tmp_audio = self._mix_audio(all_track_items, total_dur, OUTPUTS_DIR / app.project.id, safe_name)

            # Combinar
            try:
                self._export_status.configure(text="Finalizando arquivo...")
                app.update()
            except Exception:
                pass
            output_path = OUTPUTS_DIR / app.project.id / f"{safe_name}.mp4"
            if tmp_audio and shutil.which("ffmpeg"):
                cmd = [
                    "ffmpeg", "-y", "-i", str(tmp_video), "-i", str(tmp_audio),
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest",
                    str(output_path),
                ]
                subprocess.run(cmd, capture_output=True, check=True, timeout=300)
                tmp_video.unlink(missing_ok=True)
                tmp_audio.unlink(missing_ok=True)
            elif tmp_audio:
                # Sem ffmpeg: exportar separados e avisar
                shutil.move(str(tmp_video), str(output_path))
                audio_output = OUTPUTS_DIR / app.project.id / f"{safe_name}_audio.wav"
                shutil.move(str(tmp_audio), str(audio_output))
                downloads = Path.home() / "Downloads"
                shutil.copy2(str(audio_output), str(downloads / f"{safe_name}_audio.wav"))
                shutil.copy2(str(output_path), str(downloads / f"{safe_name}.mp4"))
                self._export_status.configure(
                    text="\u26a0 FFmpeg nao instalado! Video e audio salvos SEPARADOS em Downloads.\n"
                         "Instale: https://ffmpeg.org/download.html",
                    text_color="#ffaa00", font=("Segoe UI", 9))
                if hasattr(self, '_export_btn') and self._export_btn:
                    self._export_btn.configure(state="normal", text="EXPORTAR", fg_color=C["gold"])
                app.update()
                print("[Export] AVISO: ffmpeg nao encontrado. Arquivos salvos separados.")
                return
            else:
                shutil.move(str(tmp_video), str(output_path))

            downloads = Path.home() / "Downloads"
            output_dl = downloads / f"{safe_name}.mp4"
            shutil.copy2(str(output_path), str(output_dl))

            size_mb = output_path.stat().st_size / 1e6
            print(f"[Export] SUCESSO: {output_dl} ({size_mb:.1f} MB)")
            self._export_status.configure(
                text=f"\u2714 SALVO! ({size_mb:.1f} MB) em Downloads",
                text_color=C["cyan"], font=("Segoe UI", 10, "bold"))
            if hasattr(self, '_export_btn') and self._export_btn:
                self._export_btn.configure(state="normal", text="EXPORTAR", fg_color=C["gold"])
            try:
                app.update()
            except Exception:
                pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            if hasattr(self, '_export_btn') and self._export_btn:
                self._export_btn.configure(state="normal", text="EXPORTAR", fg_color=C["gold"])
            try:
                self._export_status.configure(text=f"Erro: {str(e)[:60]}", text_color="#ff4444")
            except Exception:
                print(f"[Export] Erro: {e}")

    def _mix_audio(self, track_items, total_dur, out_dir, safe_name):
        """Mixa todos os itens de audio com ducking automatico."""
        app = self.fx_panel.timeline.app
        sr = 44100
        total_samples = int(total_dur * sr)

        # Separar por track para ducking
        voice_items = [i for i in track_items if i.track == "voice"]
        other_items = [i for i in track_items if i.track in ("audio", "sfx", "music")]

        mix_voice = np.zeros((total_samples, 2), dtype=np.float32)
        mix_other = np.zeros((total_samples, 2), dtype=np.float32)

        def _load_and_place(item, target_mix):
            if not item.file_path or not Path(item.file_path).exists():
                return
            try:
                from makevid.core.audio_utils import read_audio_mono
                import soundfile as sf
                data, item_sr = sf.read(item.file_path, dtype="float32")
                if len(data.shape) == 1:
                    raw = np.column_stack([data, data])
                else:
                    raw = data if data.shape[1] == 2 else np.column_stack([data[:, 0], data[:, 0]])
                original_dur = len(raw) / item_sr
                if original_dur > 0 and abs(item.duration - original_dur) > 0.05:
                    target_samples_item = int(item.duration * item_sr)
                    raw = np.column_stack([
                        np.interp(np.linspace(0, len(raw)-1, target_samples_item), np.arange(len(raw)), raw[:, 0]),
                        np.interp(np.linspace(0, len(raw)-1, target_samples_item), np.arange(len(raw)), raw[:, 1]),
                    ])
                if item_sr != sr:
                    new_len = int(len(raw) * sr / item_sr)
                    raw = np.column_stack([
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 0]),
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 1]),
                    ])
                start_sample = int(item.start_time * sr)
                end_sample = min(start_sample + len(raw), total_samples)
                audio_len = end_sample - start_sample
                if audio_len > 0:
                    target_mix[start_sample:end_sample] += raw[:audio_len]
            except Exception:
                pass

        for item in voice_items:
            _load_and_place(item, mix_voice)
        for item in other_items:
            _load_and_place(item, mix_other)

        # Ducking: reduzir music/sfx onde tem voz
        # Detectar presenca de voz (envelope)
        voice_envelope = np.abs(mix_voice).max(axis=1)
        # Suavizar envelope (janela de ~100ms)
        kernel_size = int(0.1 * sr)
        if kernel_size > 0 and len(voice_envelope) > kernel_size:
            kernel = np.ones(kernel_size) / kernel_size
            voice_envelope = np.convolve(voice_envelope, kernel, mode='same')

        # Onde tem voz, reduzir other para -12dB (~0.25)
        duck_factor = np.where(voice_envelope > 0.01, 0.25, 1.0)
        # Suavizar transicao do duck (fade 50ms)
        fade_samples = int(0.05 * sr)
        if fade_samples > 0 and len(duck_factor) > fade_samples:
            kernel = np.ones(fade_samples) / fade_samples
            duck_factor = np.convolve(duck_factor, kernel, mode='same')

        mix_other[:, 0] *= duck_factor
        mix_other[:, 1] *= duck_factor

        # Mix final
        final_mix = np.clip(mix_voice + mix_other, -1.0, 1.0)
        audio_int16 = (final_mix * 32767).astype(np.int16)

        tmp_audio = out_dir / f"_tmp_{safe_name}.wav"
        with wave.open(str(tmp_audio), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())

        return tmp_audio
