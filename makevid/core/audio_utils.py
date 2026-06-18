"""Audio Utils - Leitura universal de audio (WAV, MP3, OGG, FLAC).

Usa soundfile como backend principal. Retorna dados em formato padrao
para uso no projeto (numpy array, sample rate, channels).
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional


def read_audio(file_path: str) -> Tuple[np.ndarray, int, int]:
    """Le qualquer formato de audio suportado.

    Retorna: (samples_int16, sample_rate, n_channels)
    - samples_int16: numpy array dtype=int16 (intercalado se stereo)
    - sample_rate: taxa de amostragem
    - n_channels: numero de canais
    """
    import soundfile as sf
    data, sr = sf.read(file_path, dtype="float32")
    nch = 1 if len(data.shape) == 1 else data.shape[1]
    # Converter para int16 (formato compativel com wave)
    samples = (data * 32767).clip(-32768, 32767).astype(np.int16)
    return samples, sr, nch


def read_audio_mono(file_path: str) -> Tuple[np.ndarray, int]:
    """Le audio e retorna mono float32 normalizado.

    Retorna: (samples_float32_mono, sample_rate)
    """
    import soundfile as sf
    data, sr = sf.read(file_path, dtype="float32")
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    return data, sr


def get_audio_duration(file_path: str) -> float:
    """Retorna duracao em segundos de qualquer formato de audio."""
    p = Path(file_path)
    if not p.exists():
        return 0.0
    try:
        import soundfile as sf
        info = sf.info(file_path)
        return info.duration
    except Exception:
        return 0.0


def apply_volume_keyframes(audio: np.ndarray, sr: int, keyframes: list, duration: float) -> np.ndarray:
    """Aplica curva de volume por keyframes ao array de audio.

    Args:
        audio: array numpy (mono ou stereo)
        sr: sample rate
        keyframes: lista de {"time": float, "value": float}
        duration: duracao do item em segundos

    Returns:
        audio com volume modulado
    """
    if not keyframes or len(keyframes) < 2:
        return audio

    kfs = sorted(keyframes, key=lambda k: k["time"])
    n_samples = len(audio) if audio.ndim == 1 else audio.shape[0]
    times = np.linspace(0, duration, n_samples)

    kf_times = [k["time"] for k in kfs]
    kf_values = [k["value"] for k in kfs]
    volume_curve = np.interp(times, kf_times, kf_values)

    if audio.ndim == 2:
        audio = audio * volume_curve[:, np.newaxis]
    else:
        audio = audio * volume_curve

    return audio
