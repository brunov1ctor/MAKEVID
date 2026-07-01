"""Player Qt - Playback sincronizado por relógio real (porta do tkinter player)."""

import logging
import time as _time
from pathlib import Path

from PySide6.QtCore import QTimer, Signal, QObject

log = logging.getLogger("player_qt")


class TimelinePlayerQt(QObject):
    """Controla playback de video e audio na timeline Qt.

    Abordagem idêntica ao tkinter: timer real → calcula tempo → seek frame.
    """

    frame_ready = Signal(object)  # emite numpy array BGR
    playback_ended = Signal()
    time_updated = Signal(float)  # emite posicao em segundos

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playing = False
        self._paused = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps UI
        self._timer.timeout.connect(self._tick)

        self._caps = {}
        self._clip_fps = {}
        self._start_time = 0.0
        self._start_offset = 0.0
        self._speed = 1.0
        self._total_dur = 0.0
        self._clips = []
        self._clip_starts = []

        self._project = None

    @property
    def is_playing(self):
        return self._playing

    @property
    def is_paused(self):
        return self._paused

    # ============================================================
    # PUBLIC API
    # ============================================================

    def set_project(self, project):
        self._project = project

    def play(self, start_clip=None, speed=1.0):
        """Inicia ou retoma playback."""
        if self._paused:
            self._resume()
            return
        if self._playing:
            self.pause()
            return

        if not self._project:
            return
        clips = sorted(self._project.clips, key=lambda x: x.position)
        if not clips:
            return

        self._clips = clips
        self._total_dur = self._project.total_duration()
        self._speed = speed

        # Calcular inicio de cada clip
        self._clip_starts = []
        t = 0.0
        for c in clips:
            self._clip_starts.append(t)
            t += c.duration

        # Posicao inicial
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
        self._start_audio()
        self._timer.start()

    def play_from(self, time_pos, speed=1.0):
        """Inicia playback de uma posição específica."""
        if not self._project:
            return
        clips = sorted(self._project.clips, key=lambda x: x.position)
        if not clips:
            return

        self._clips = clips
        self._total_dur = self._project.total_duration()
        self._speed = speed

        self._clip_starts = []
        t = 0.0
        for c in clips:
            self._clip_starts.append(t)
            t += c.duration

        self._start_offset = max(0, min(time_pos, self._total_dur))
        self._start_time = _time.time()
        self._playing = True
        self._paused = False

        self._open_clips()
        self._start_audio()
        self._timer.start()

    def pause(self):
        if not self._playing:
            return
        self._playing = False
        self._paused = True
        self._start_offset = self._get_current_time()
        self._timer.stop()
        self._stop_audio()

    def stop(self):
        self._playing = False
        self._paused = False
        self._timer.stop()
        self._close_clips()
        self._stop_audio()

    def set_speed(self, speed):
        """Altera velocidade em tempo real durante playback."""
        import time as _time
        self._speed = max(0.25, min(4.0, speed))
        if self._playing and not self._paused:
            current = self._get_current_time()
            self._start_offset = current
            self._start_time = _time.time()
            self._stop_audio()
            self._start_audio()

    def seek_to_time(self, target_time):
        """Seek para tempo específico."""
        target_time = max(0, min(target_time, self._total_dur))
        self._start_offset = target_time
        self._start_time = _time.time()
        self.time_updated.emit(target_time)

        # Mostrar frame
        clip, time_in_clip = self._get_clip_at_time(target_time)
        if clip:
            self._render_frame(clip, time_in_clip)

        # Reiniciar audio se tocando
        if self._playing:
            self._stop_audio()
            self._start_audio()

    # ============================================================
    # CORE TICK
    # ============================================================

    def _get_current_time(self):
        if not self._playing:
            return self._start_offset
        elapsed = _time.time() - self._start_time
        return min(self._start_offset + elapsed * self._speed, self._total_dur)

    def _tick(self):
        if not self._playing:
            return

        # Recalcular duração total (pode mudar se items foram removidos)
        self._total_dur = self._project.total_duration()

        current_time = self._get_current_time()

        if current_time >= self._total_dur:
            # Verificar loop
            preview = self.parent()
            timeline = getattr(preview, 'timeline', None)
            if timeline and getattr(timeline, 'loop_enabled', False):
                # Recalcular duração (pode ter mudado)
                self._total_dur = self._project.total_duration()
                # Reiniciar do começo
                self._start_offset = 0.0
                self._start_time = _time.time()
                self._stop_audio()
                self._start_audio()
                return
            self.stop()
            self.playback_ended.emit()
            return

        self.time_updated.emit(current_time)

        clip, time_in_clip = self._get_clip_at_time(current_time)
        if clip:
            self._render_frame(clip, time_in_clip)

    def _get_clip_at_time(self, t):
        for i, clip in enumerate(self._clips):
            clip_start = self._clip_starts[i]
            if t < clip_start + clip.duration:
                return clip, t - clip_start
        return None, 0

    def _render_frame(self, clip, time_in_clip):
        import cv2
        import numpy as np

        frame = None
        if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
            cap = self._caps.get(clip.id)
            if cap:
                clip_fps = self._clip_fps.get(clip.id, 16)
                target_frame = int(time_in_clip * clip_fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, f = cap.read()
                if ret:
                    frame = f

        # Clip vazio: frame preto
        if frame is None:
            w = getattr(self._project, 'output_width', 832) or 832
            h = getattr(self._project, 'output_height', 480) or 480
            frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Aplicar FX
        fx_items = self._project.get_track_items("fx")
        if fx_items:
            from makevid.core.fx_processor import apply_fx_to_frame
            frame_rgb = frame[:, :, ::-1]
            frame_rgb = apply_fx_to_frame(frame_rgb, fx_items,
                                          self._get_current_time(), self._total_dur)
            frame = frame_rgb[:, :, ::-1]
        self.frame_ready.emit(frame)

    # ============================================================
    # CLIP MANAGEMENT
    # ============================================================

    def _open_clips(self):
        import cv2
        self._close_clips()
        for clip in self._clips:
            if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                cap = cv2.VideoCapture(str(clip.video_path))
                if cap.isOpened():
                    self._caps[clip.id] = cap
                    self._clip_fps[clip.id] = cap.get(cv2.CAP_PROP_FPS) or 16

    def _close_clips(self):
        for cap in self._caps.values():
            try:
                cap.release()
            except Exception:
                pass
        self._caps.clear()
        self._clip_fps.clear()

    def _resume(self):
        self._paused = False
        self._playing = True
        self._start_time = _time.time()
        if not self._caps:
            self._open_clips()
        self._start_audio()
        self._timer.start()

    # ============================================================
    # AUDIO
    # ============================================================

    def _start_audio(self):
        if not self._project:
            return
        try:
            import sounddevice as sd
            import numpy as np

            all_audio_items = []
            for track_name in ("voice", "sfx", "music", "audio"):
                all_audio_items.extend(self._project.get_track_items(track_name))

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
                track_vol = self._project.track_volumes.get(item.track, 1.0)
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
                        n = int(len(raw) * fade_in_pct)
                        if n > 0:
                            raw[:n] *= np.linspace(0, 1, n).reshape(-1, 1)
                    # Fade out
                    fade_out_pct = int(item.params.get("fade_out", 0)) / 100.0
                    if fade_out_pct > 0:
                        n = int(len(raw) * fade_out_pct)
                        if n > 0:
                            raw[-n:] *= np.linspace(1, 0, n).reshape(-1, 1)
                    # Pan
                    pan = int(item.params.get("pan", 0)) / 100.0
                    if pan != 0:
                        raw[:, 0] *= max(0, 1.0 - pan)
                        raw[:, 1] *= max(0, 1.0 + pan)
                    # Volume Keyframes
                    if item.volume_keyframes and len(item.volume_keyframes) >= 2:
                        from makevid.core.audio_utils import apply_volume_keyframes
                        raw = apply_volume_keyframes(raw, sr, item.volume_keyframes, item.duration)
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
