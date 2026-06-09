"""Player - Playback de timeline sincronizado por relogio real (frame-seek)."""

import logging
import time as _time
from pathlib import Path

log = logging.getLogger("player")


class TimelinePlayer:
    """Controla playback de video e audio na timeline.
    
    Abordagem: timer real → calcula tempo → seek no clip correto → mostra frame.
    Nunca depende de leitura sequencial de frames.
    """

    def __init__(self, preview_panel):
        self.pp = preview_panel
        self.app = preview_panel.app
        self._playing = False
        self._paused = False
        self._playback_after_id = None
        self._caps = {}  # clip_id -> cv2.VideoCapture (cache aberto)
        self._clip_fps = {}  # clip_id -> fps real do video
        self._start_time = 0.0  # time.time() quando play comecou
        self._start_offset = 0.0  # posicao na timeline quando play comecou
        self._speed = 1.0
        self._total_dur = 0.0
        self._clips = []
        self._clip_starts = []  # tempo de inicio de cada clip na timeline
        self._progress_canvas = None

    @property
    def is_playing(self):
        return self._playing

    @property
    def is_paused(self):
        return self._paused

    # ============================================================
    # PUBLIC API
    # ============================================================

    def play(self, start_clip=None):
        """Inicia ou retoma playback."""
        if self._paused:
            self._resume()
            return
        if self._playing:
            self.pause()
            return

        clips = sorted(self.app.project.clips, key=lambda x: x.position)
        if not clips:
            return

        self._clips = clips
        self._total_dur = self.app.project.total_duration()
        self._speed = self.app.timeline.playback_speed

        # Calcular inicio de cada clip na timeline
        self._clip_starts = []
        t = 0.0
        for c in clips:
            self._clip_starts.append(t)
            t += c.duration

        # Determinar posicao inicial
        self._start_offset = 0.0
        if start_clip:
            for i, c in enumerate(clips):
                if c.id == start_clip.id:
                    self._start_offset = self._clip_starts[i]
                    break

        self._start_time = _time.time()
        self._playing = True
        self._paused = False

        self._open_clips()
        self._show_progress_bar()
        self._start_audio()
        self._tick()

    def pause(self):
        """Pausa o playback."""
        if not self._playing:
            return
        self._playing = False
        self._paused = True
        # Guardar posicao atual
        self._start_offset = self._get_current_time()
        if self._playback_after_id:
            self.pp.preview_frame.after_cancel(self._playback_after_id)
            self._playback_after_id = None
        self._stop_audio()

    def stop(self):
        """Para completamente."""
        self._playing = False
        self._paused = False
        if self._playback_after_id:
            self.pp.preview_frame.after_cancel(self._playback_after_id)
            self._playback_after_id = None
        self._close_clips()
        self._stop_audio()
        self._hide_progress_bar()
        if hasattr(self.pp, '_playback_img_size'):
            del self.pp._playback_img_size
        self.pp._tk_photo = None
        try:
            self.app.timeline.draw()
        except Exception:
            pass

    def _resume(self):
        self._paused = False
        self._playing = True
        self._speed = self.app.timeline.playback_speed
        self._start_time = _time.time()
        # _start_offset ja tem a posicao onde pausou
        self._start_audio()
        self._tick()

    # ============================================================
    # CORE TICK - sincronizado por relogio
    # ============================================================

    def _get_current_time(self):
        """Retorna posicao atual na timeline em segundos."""
        if not self._playing:
            return self._start_offset
        elapsed = _time.time() - self._start_time
        return min(self._start_offset + elapsed * self._speed, self._total_dur)

    def _tick(self):
        """Loop principal: calcula tempo, busca frame correto, renderiza."""
        if not self._playing:
            return

        current_time = self._get_current_time()

        # Fim da timeline
        if current_time >= self._total_dur:
            self.stop()
            self.pp._on_playback_ended()
            return

        # Atualizar playhead
        self.app.timeline.playhead_pos = current_time
        self.app.timeline._update_playhead_only()
        self._update_progress_bar(current_time / self._total_dur)

        # Encontrar clip e frame correto
        clip, time_in_clip = self._get_clip_at_time(current_time)
        if clip:
            self._render_frame(clip, time_in_clip)

        # Proximo tick (~16ms = 60fps de UI, independente do video fps)
        self._playback_after_id = self.pp.preview_frame.after(16, self._tick)

    def _get_clip_at_time(self, t):
        """Retorna (clip, tempo_dentro_do_clip) para um tempo na timeline."""
        for i, clip in enumerate(self._clips):
            clip_start = self._clip_starts[i]
            if t < clip_start + clip.duration:
                return clip, t - clip_start
        # Alem do ultimo clip
        return None, 0

    def _render_frame(self, clip, time_in_clip):
        """Renderiza o frame correto do clip na posicao temporal."""
        if clip.status != "done" or not clip.video_path or not Path(clip.video_path).exists():
            self.pp._set_black_frame()
            return

        cap = self._caps.get(clip.id)
        if not cap:
            return

        # Calcular frame number baseado no tempo
        clip_fps = self._clip_fps.get(clip.id, 16)
        target_frame = int(time_in_clip * clip_fps)

        # Seek direto ao frame
        import cv2
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if ret:
            # Aplicar FX
            fx_items = self.app.project.get_track_items("fx")
            if fx_items:
                from makevid.core.fx_processor import apply_fx_to_frame
                frame_rgb = frame[:, :, ::-1]
                frame_rgb = apply_fx_to_frame(frame_rgb, fx_items,
                                              self._get_current_time(), self._total_dur)
                frame = frame_rgb[:, :, ::-1]
            self.pp._set_video_frame(frame)
        else:
            self.pp._set_black_frame()

    # ============================================================
    # CLIP MANAGEMENT
    # ============================================================

    def _open_clips(self):
        """Abre VideoCapture para todos os clips (cache)."""
        import cv2
        self._close_clips()
        for clip in self._clips:
            if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                cap = cv2.VideoCapture(str(clip.video_path))
                if cap.isOpened():
                    self._caps[clip.id] = cap
                    self._clip_fps[clip.id] = cap.get(cv2.CAP_PROP_FPS) or 16

    def _close_clips(self):
        """Fecha todos os VideoCaptures."""
        for cap in self._caps.values():
            try:
                cap.release()
            except Exception:
                pass
        self._caps.clear()
        self._clip_fps.clear()

    # ============================================================
    # SEEK (chamado pela timeline ao arrastar playhead)
    # ============================================================

    def _seek_to_frame(self, target_frame):
        """Seek por frame number (compatibilidade)."""
        if self._total_dur <= 0 or not self._clips:
            return
        # Converter frame para tempo
        total_frames = sum(int(c.duration * 16) for c in self._clips)
        if total_frames <= 0:
            return
        ratio = target_frame / total_frames
        target_time = ratio * self._total_dur
        self._seek_to_time(target_time)

    def _seek_to_time(self, target_time):
        """Seek para um tempo especifico na timeline."""
        target_time = max(0, min(target_time, self._total_dur))
        self._start_offset = target_time
        self._start_time = _time.time()
        self.app.timeline.playhead_pos = target_time
        self._update_progress_bar(target_time / self._total_dur if self._total_dur > 0 else 0)

        # Mostrar frame no display
        clip, time_in_clip = self._get_clip_at_time(target_time)
        if clip:
            self._render_frame(clip, time_in_clip)

        # Reiniciar audio se tocando
        if self._playing:
            self._stop_audio()
            self._start_audio()

    # ============================================================
    # AUDIO
    # ============================================================

    def _start_audio(self):
        try:
            import sounddevice as sd
            import numpy as np

            all_audio_items = []
            for track_name in ("voice", "sfx", "music", "audio"):
                all_audio_items.extend(self.app.project.get_track_items(track_name))

            if not all_audio_items:
                return

            sr = 44100
            total_samples = int(self._total_dur * sr)
            if total_samples <= 0:
                return

            mix = np.zeros((total_samples, 2), dtype=np.float32)

            for item in all_audio_items:
                if not item.file_path or not Path(item.file_path).exists():
                    continue
                track_vol = self.app.project.track_volumes.get(item.track, 1.0)
                try:
                    import soundfile as sf
                    data, item_sr = sf.read(item.file_path, dtype="float32")
                    if len(data.shape) == 1:
                        raw = np.column_stack([data, data])
                    else:
                        raw = data if data.shape[1] == 2 else np.column_stack([data[:, 0], data[:, 0]])
                    if item_sr != sr:
                        new_len = int(len(raw) * sr / item_sr)
                        raw = np.column_stack([
                            np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 0]),
                            np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 1]),
                        ])
                    item_vol = int(item.params.get("volume", 100)) / 100.0
                    raw *= track_vol * item_vol
                    # Fade in
                    fade_in_pct = int(item.params.get("fade_in", 0)) / 100.0
                    if fade_in_pct > 0:
                        fade_samples = int(len(raw) * fade_in_pct)
                        if fade_samples > 0:
                            raw[:fade_samples] *= np.linspace(0, 1, fade_samples).reshape(-1, 1)
                    # Fade out
                    fade_out_pct = int(item.params.get("fade_out", 0)) / 100.0
                    if fade_out_pct > 0:
                        fade_samples = int(len(raw) * fade_out_pct)
                        if fade_samples > 0:
                            raw[-fade_samples:] *= np.linspace(1, 0, fade_samples).reshape(-1, 1)
                    # Pan
                    pan = int(item.params.get("pan", 0)) / 100.0
                    if pan != 0:
                        raw[:, 0] *= max(0, 1.0 - pan)
                        raw[:, 1] *= max(0, 1.0 + pan)
                except Exception:
                    continue

                start_sample = int(item.start_time * sr)
                max_samples = int(item.duration * sr)
                if len(raw) > max_samples:
                    raw = raw[:max_samples]
                end_sample = min(start_sample + len(raw), total_samples)
                audio_len = end_sample - start_sample
                if audio_len > 0:
                    mix[start_sample:end_sample] += raw[:audio_len]

            mix = np.clip(mix, -1.0, 1.0)

            # Comecar do ponto atual
            start_sample = int(self._start_offset * sr)
            remaining = mix[start_sample:]

            if len(remaining) > 0:
                play_sr = int(sr * self._speed)
                sd.stop()
                sd.play(np.ascontiguousarray(remaining.astype(np.float32)), samplerate=play_sr)
        except Exception as e:
            log.warning(f"Audio playback failed: {e}")

    def _stop_audio(self):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

    def _restart_audio_at_current_pos(self):
        """Reinicia audio na posicao atual com nova velocidade."""
        current_time = self._get_current_time()
        self._stop_audio()
        self._start_offset = current_time
        self._start_time = _time.time()
        self._speed = self.app.timeline.playback_speed
        self._start_audio()

    # ============================================================
    # PROGRESS BAR
    # ============================================================

    def _show_progress_bar(self):
        self._hide_progress_bar()
        import tkinter as tk
        self._progress_canvas = tk.Canvas(
            self.pp.preview_frame, height=6, bg="#1a1a1a",
            highlightthickness=0, bd=0, cursor="hand2"
        )
        self._progress_canvas.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)
        self._progress_bg_id = self._progress_canvas.create_rectangle(0, 1, 0, 5, fill="#444444", outline="")
        self._progress_bar_id = self._progress_canvas.create_rectangle(0, 1, 0, 5, fill="#ff0000", outline="")
        self._progress_canvas.bind("<Button-1>", self._on_progress_click)
        self._progress_canvas.bind("<B1-Motion>", self._on_progress_click)
        self._progress_canvas.after(50, self._progress_update_bg)

    def _progress_update_bg(self):
        if not self._progress_canvas:
            return
        w = self._progress_canvas.winfo_width()
        self._progress_canvas.coords(self._progress_bg_id, 0, 1, w, 5)

    def _on_progress_click(self, event):
        """Seek via click na barra de progresso."""
        w = self._progress_canvas.winfo_width()
        if w <= 0 or self._total_dur <= 0:
            return
        ratio = max(0.0, min(1.0, event.x / w))
        target_time = ratio * self._total_dur
        self._seek_to_time(target_time)

    def _update_progress_bar(self, progress):
        if self._progress_canvas:
            w = self._progress_canvas.winfo_width()
            bw = int(w * progress)
            self._progress_canvas.coords(self._progress_bar_id, 0, 1, bw, 5)

    def _hide_progress_bar(self):
        if self._progress_canvas:
            self._progress_canvas.destroy()
            self._progress_canvas = None
