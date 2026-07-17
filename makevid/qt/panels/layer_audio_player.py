"""Lógica de reprodução de áudio para layers — streaming com callback em tempo real."""

import logging
import time as _time
from pathlib import Path

import numpy as np
import soundfile as sf
import sounddevice as sd

_log = logging.getLogger(__name__)


def _resolve_file(item) -> str:
    """Retorna o arquivo a usar: seamless se ativo e existir, senão o original."""
    if str(getattr(item, 'params', {}).get('seamless', '0')) == '1':
        sf_path = item.params.get('seamless_file', '')
        if sf_path and Path(sf_path).exists():
            return sf_path
    return item.file_path


def _file_exists(path) -> bool:
    return bool(path) and Path(path).exists()


def _prepare_audio(item):
    """Carrega áudio aplicando file_offset, duration, muted_regions e fades."""
    seamless_on = str(getattr(item, 'params', {}).get('seamless', '0')) == '1'
    path = _resolve_file(item)
    if not _file_exists(path):
        return None, 0
    try:
        raw, sr = sf.read(path, dtype="float32")
        data = np.array(raw, copy=True)
        if len(data.shape) == 1:
            data = np.column_stack([data, data])
        if not seamless_on:
            offset_sec = float(getattr(item, 'file_offset', 0.0))
            if offset_sec > 0:
                data = data[int(offset_sec * sr):]
            file_dur = float((getattr(item, 'params', {}) or {}).get('file_duration', 0.0))
            trunc_dur = file_dur if file_dur > 0 else float(item.duration)
            max_samples = int(trunc_dur * sr)
            _log.debug(
                "[PREP] id=%s sr=%d raw_samples=%d file_dur=%.3f trunc_dur=%.3f "
                "max_samples=%d seamless=%s muted=%s",
                getattr(item, 'id', '?'), sr, len(raw), file_dur, trunc_dur,
                max_samples, seamless_on, getattr(item, 'muted_regions', []),
            )
            if max_samples > 0 and len(data) > max_samples:
                data = data[:max_samples]
            muted = getattr(item, 'muted_regions', [])
            if muted:
                keep, prev = [], 0
                for region in sorted(muted, key=lambda r: r['start']):
                    ca = max(0, min(int(float(region['start']) * sr), len(data)))
                    cb = max(ca, min(int(float(region['end'])   * sr), len(data)))
                    if ca > prev:
                        keep.append(data[prev:ca])
                    prev = cb
                if prev < len(data):
                    keep.append(data[prev:])
                data = np.concatenate(keep) if keep else np.zeros((0, 2), dtype=np.float32)
                _log.debug("[PREP] apos muted_regions: samples=%d (%.3fs)", len(data), len(data)/max(1,sr))
        else:
            _log.debug("[PREP] seamless ativo, usando arquivo direto: %s samples=%d", path, len(data))
        duration = len(data) / sr if sr > 0 else float(item.duration)
        _log.debug("[PREP] resultado final: samples=%d duration=%.3fs", len(data), duration)
        try:
            params = getattr(item, 'params', {}) or {}
            fade_in_pct  = float(params.get('fade_in',  0))
            fade_out_pct = float(params.get('fade_out', 0))
            reverb_pct   = float(params.get('reverb',   0)) / 100.0
            room_pct     = float(params.get('room',     0)) / 100.0
            if fade_in_pct > 0 and duration > 0:
                n = min(int((fade_in_pct / 100.0) * duration * sr), len(data))
                if n > 0:
                    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32) ** 2
                    data[:n] *= ramp[:, np.newaxis]
            if fade_out_pct > 0 and duration > 0:
                n = min(int((fade_out_pct / 100.0) * duration * sr), len(data))
                if n > 0:
                    ramp = np.linspace(1.0, 0.0, n, dtype=np.float32) ** 2
                    data[-n:] *= ramp[:, np.newaxis]
            if reverb_pct > 0:
                tail_sec   = 0.1 + room_pct * 2.9
                reverb_len = int(tail_sec * sr)
                decay      = 3.0 + room_pct * 9.0
                impulse    = np.exp(-np.linspace(0, decay, reverb_len)).astype(np.float32)
                impulse   /= impulse.sum()
                wet_l = np.convolve(data[:, 0], impulse)[:len(data)]
                wet_r = np.convolve(data[:, 1], impulse)[:len(data)]
                data[:, 0] = np.clip(data[:, 0] + wet_l * reverb_pct, -1.0, 1.0)
                data[:, 1] = np.clip(data[:, 1] + wet_r * reverb_pct, -1.0, 1.0)
        except Exception:
            pass
        return data, sr
    except Exception:
        _log.exception("Erro ao preparar audio")
        return None, 0


def _prepare_audio_visual(item):
    """Carrega áudio SEM muted_regions — usado apenas para desenhar a waveform."""
    path = _resolve_file(item)
    if not _file_exists(path):
        return None, 0
    try:
        raw, sr = sf.read(path, dtype="float32")
        data = np.array(raw, copy=True)
        if len(data.shape) == 1:
            data = np.column_stack([data, data])
        # seamless file já é o resultado final — não aplica offset/duration
        if str(getattr(item, 'params', {}).get('seamless', '0')) != '1':
            offset_sec = float(getattr(item, 'file_offset', 0.0))
            if offset_sec > 0:
                data = data[int(offset_sec * sr):]
            file_dur = float((getattr(item, 'params', {}) or {}).get('file_duration', 0.0))
            trunc_dur = file_dur if file_dur > 0 else float(item.duration)
            max_samples = int(trunc_dur * sr)
            if max_samples > 0 and len(data) > max_samples:
                data = data[:max_samples]
        return data, sr
    except Exception:
        _log.exception("Erro ao preparar audio visual")
        return None, 0


class _LayerStreamPlayer:
    """OutputStream com callback — volume e pan aplicados em tempo real por bloco.

    Parâmetros leves (volume, pan): lidos a cada bloco sem reiniciar.
    Parâmetros pesados (speed, reverb, cortes): exigem reconstruir o áudio base.
    """

    BLOCK = 1024

    def __init__(self, audio_base: np.ndarray, sr: int, item, loop: bool = True):
        self._base   = audio_base
        self._sr     = sr
        self._item   = item
        self._loop   = loop
        self._pos    = 0
        self._stream = None
        self._active = False

    def start(self, start_ratio: float = 0.0):
        self._pos    = int(start_ratio * len(self._base))
        self._active = True
        self._stream = sd.OutputStream(
            samplerate=self._sr, channels=2, dtype='float32',
            blocksize=self.BLOCK, callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        self._active = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                _log.debug("Erro ao fechar stream", exc_info=True)
            self._stream = None

    @property
    def position_ratio(self) -> float:
        n = len(self._base)
        return self._pos / n if n > 0 else 0.0

    def _callback(self, outdata, frames, time_info, status):
        if not self._active or len(self._base) == 0:
            outdata[:] = 0
            raise sd.CallbackStop()
        n   = len(self._base)
        end = self._pos + frames
        if end >= n:
            if self._loop:
                block = np.concatenate([self._base[self._pos:], self._base[:end - n]])
                self._pos = end % n
            else:
                remaining = n - self._pos
                block = np.zeros((frames, 2), dtype=np.float32)
                if remaining > 0:
                    block[:remaining] = self._base[self._pos:n]
                self._pos    = n
                self._active = False
                try:
                    vol = float(self._item.params.get('volume', 80)) / 100.0
                    pan = float(self._item.params.get('pan', 0))    / 100.0
                except Exception:
                    vol, pan = 0.8, 0.0
                block *= vol
                if pan != 0.0:
                    angle = (pan + 1.0) * np.pi / 4.0
                    block[:, 0] *= float(np.cos(angle))
                    block[:, 1] *= float(np.sin(angle))
                np.clip(block, -1.0, 1.0, out=block)
                outdata[:] = block
                raise sd.CallbackStop()
        else:
            block = self._base[self._pos:end].copy()
            self._pos = end
        try:
            vol = float(self._item.params.get('volume', 80)) / 100.0
            pan = float(self._item.params.get('pan', 0))    / 100.0
        except Exception:
            vol, pan = 0.8, 0.0
        block *= vol
        if pan != 0.0:
            angle = (pan + 1.0) * np.pi / 4.0
            block[:, 0] *= float(np.cos(angle))
            block[:, 1] *= float(np.sin(angle))
        np.clip(block, -1.0, 1.0, out=block)
        outdata[:] = block
