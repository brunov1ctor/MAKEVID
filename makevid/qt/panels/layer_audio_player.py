"""Lógica de reprodução de áudio para layers — streaming com callback em tempo real."""

import logging
import time as _time
from pathlib import Path

import numpy as np
import soundfile as sf
import sounddevice as sd

_log = logging.getLogger(__name__)


def _file_exists(path) -> bool:
    return bool(path) and Path(path).exists()


def _prepare_audio(item):
    """Carrega áudio aplicando file_offset, duration e removendo muted_regions."""
    if not _file_exists(item.file_path):
        return None, 0
    try:
        raw, sr = sf.read(item.file_path, dtype="float32")
        data = np.array(raw, copy=True)
        if len(data.shape) == 1:
            data = np.column_stack([data, data])
        offset_sec = float(getattr(item, 'file_offset', 0.0))
        if offset_sec > 0:
            data = data[int(offset_sec * sr):]
        max_samples = int(float(item.duration) * sr)
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
        return data, sr
    except Exception:
        _log.exception("Erro ao preparar audio")
        return None, 0


def _prepare_audio_visual(item):
    """Carrega áudio SEM muted_regions — usado apenas para desenhar a waveform."""
    if not _file_exists(item.file_path):
        return None, 0
    try:
        raw, sr = sf.read(item.file_path, dtype="float32")
        data = np.array(raw, copy=True)
        if len(data.shape) == 1:
            data = np.column_stack([data, data])
        offset_sec = float(getattr(item, 'file_offset', 0.0))
        if offset_sec > 0:
            data = data[int(offset_sec * sr):]
        max_samples = int(float(item.duration) * sr)
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

    def __init__(self, audio_base: np.ndarray, sr: int, item):
        self._base   = audio_base
        self._sr     = sr
        self._item   = item
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
            return
        n   = len(self._base)
        end = self._pos + frames
        if end <= n:
            block = self._base[self._pos:end].copy()
        else:
            block = np.concatenate([self._base[self._pos:], self._base[:end - n]])
        self._pos = end % n
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
