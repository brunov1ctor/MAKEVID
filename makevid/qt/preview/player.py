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
        self._audio_stream = None

        self._project = None
        self._master_volume = 1.0
        # Niveis RMS por faixa, atualizados pelo callback de audio em tempo real
        # {"voice": db_float, "sfx": db_float, ...}  (dBFS, 0 = silencio)
        self.track_levels: dict = {"voice": -60.0, "sfx": -60.0, "music": -60.0, "audio": -60.0}

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

        self._clips = clips
        self._total_dur = self._project.total_duration()
        self._speed = speed

        if self._total_dur <= 0:
            return

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

        self._clips = clips
        self._total_dur = float(self._project.total_duration() or 0.0)
        self._speed = speed

        if self._total_dur <= 0:
            return

        self._clip_starts = []
        t = 0.0
        for c in clips:
            self._clip_starts.append(t)
            t += c.duration

        self._start_offset = max(0.0, min(float(time_pos), self._total_dur))
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
        total = float(self._total_dur or 0.0)
        target_time = max(0.0, min(float(target_time), total))
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
        self._total_dur = float(self._project.total_duration() or 0.0)

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
        if clip is not None and clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
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
        except ImportError:
            log.debug("sounddevice nao instalado - sem som")
            return

        try:
            import numpy as np
            from makevid.core.audio_utils import render_audio_item

            all_audio_items = []
            for track_name in ("voice", "sfx", "music", "audio"):
                all_audio_items.extend(self._project.get_track_items(track_name))

            if not all_audio_items:
                return

            sr = 44100
            total_samples = int(self._total_dur * sr)
            if total_samples <= 0:
                return

            # Monta as faixas base SEM volume/pan (serao aplicados no callback)
            # Cada entrada: (base_stereo, start_sample, item_ref)
            tracks = []
            for item in all_audio_items:
                if not item.file_path or not Path(item.file_path).exists():
                    continue
                try:
                    raw, item_sr = render_audio_item(item)
                    if raw is None or len(raw) == 0:
                        continue
                    if item_sr != sr:
                        new_len = int(len(raw) * sr / item_sr)
                        xs = np.linspace(0, len(raw) - 1, new_len)
                        raw = np.column_stack([
                            np.interp(xs, np.arange(len(raw)), raw[:, 0]),
                            np.interp(xs, np.arange(len(raw)), raw[:, 1]),
                        ])
                    # Desfaz volume/pan que render_audio_item ja aplicou
                    # para poder reaplicar em tempo real no callback
                    vol = float(item.params.get('volume', 100)) / 100.0
                    if vol > 1e-6:
                        raw = raw / vol
                    tracks.append((raw, int(item.start_time * sr), item))
                except Exception as e:
                    log.warning(f"Erro ao processar {item.file_path}: {e}")
                    continue

            if not tracks:
                return

            try:
                sd.query_devices(kind='output')
            except Exception as e:
                log.warning(f"Nenhum dispositivo de saida disponivel: {e}")
                return

            play_sr = int(sr / max(self._speed, 0.1))
            sd.stop()

            out_device = None
            try:
                dev_info = sd.query_devices(kind='output')
                if int(dev_info.get('max_output_channels', 2)) < 2:
                    raise ValueError("dispositivo padrao sem stereo")
            except Exception:
                for i, d in enumerate(sd.query_devices()):
                    if d['max_output_channels'] >= 2 and 'MME' in d['name']:
                        out_device = i
                        break

            # Posicao de leitura em samples (relativa ao inicio do mix)
            start_s = int(self._start_offset * sr)
            # Agrupa tracks por nome para calcular nivel por faixa
            track_groups: dict = {}
            for base, item_start, item in tracks:
                track_groups.setdefault(item.track, []).append((base, item_start, item))

            player_ref = self
            pos = [start_s]
            project_ref = self._project
            master_vol_ref = self

            BLOCK = 1024

            def _callback(outdata, frames, time_info, status):
                block = np.zeros((frames, 2), dtype=np.float32)
                cur = pos[0]

                for track_name, items in track_groups.items():
                    track_block = np.zeros((frames, 2), dtype=np.float32)
                    for base, item_start, item in items:
                        item_end = item_start + len(base)
                        if cur >= item_end or cur + frames <= item_start:
                            continue
                        src_start = max(0, cur - item_start)
                        dst_start = max(0, item_start - cur)
                        n = min(frames - dst_start, len(base) - src_start)
                        if n <= 0:
                            continue
                        chunk = base[src_start:src_start + n].copy()
                        try:
                            vol = float(item.params.get('volume', 100)) / 100.0
                            pan = float(item.params.get('pan', 0)) / 100.0
                            track_vol = project_ref.track_volumes.get(item.track, 1.0)
                        except Exception:
                            vol, pan, track_vol = 1.0, 0.0, 1.0
                        chunk *= vol * track_vol
                        if pan != 0.0:
                            angle = (pan + 1.0) * np.pi / 4.0
                            chunk[:, 0] *= float(np.cos(angle))
                            chunk[:, 1] *= float(np.sin(angle))
                        track_block[dst_start:dst_start + n] += chunk

                    # Nivel RMS da faixa em dBFS
                    rms = float(np.sqrt(np.mean(track_block ** 2)))
                    db = 20.0 * np.log10(max(rms, 1e-9))
                    player_ref.track_levels[track_name] = max(-60.0, db)
                    block += track_block

                mv = max(0.0, float(getattr(master_vol_ref, '_master_volume', 1.0)))
                block *= mv
                np.clip(block, -1.0, 1.0, out=block)
                outdata[:] = block
                pos[0] += frames

            self._audio_stream = sd.OutputStream(
                samplerate=play_sr,
                channels=2,
                dtype='float32',
                blocksize=BLOCK,
                device=out_device,
                callback=_callback,
            )
            self._audio_stream.start()
            log.debug(f"Audio stream iniciado: {len(tracks)} faixa(s), offset={self._start_offset:.1f}s")

        except Exception as e:
            log.exception(f"_start_audio erro: {e}")

    def _stop_audio(self):
        stream = getattr(self, '_audio_stream', None)
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
            self._audio_stream = None
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
