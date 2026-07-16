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


def render_audio_item(item) -> Tuple[Optional[np.ndarray], int]:
    """Função central: renderiza um item de áudio aplicando todos os efeitos em ordem.

    Ordem: file_offset → duration → speed/pitch → muted_regions → volume/keyframes → fades/EQ/reverb
    Retorna: (stereo_float32, sample_rate) ou (None, 0) em caso de erro.
    """
    file_offset = float(getattr(item, 'file_offset', 0.0))
    duration = float(getattr(item, 'duration', 0.0))
    muted_regions = list(getattr(item, 'muted_regions', []) or [])
    volume_keyframes = list(getattr(item, 'volume_keyframes', []) or [])
    params = dict(getattr(item, 'params', {}) or {})
    return process_audio_item(
        file_path=item.file_path,
        params=params,
        volume_keyframes=volume_keyframes,
        duration=duration,
        muted_regions=muted_regions,
        file_offset=file_offset,
    )


def process_audio_item(file_path: str, params: dict, volume_keyframes: list, duration: float, muted_regions: list = None, file_offset: float = 0.0) -> Tuple[Optional[np.ndarray], int]:
    """Aplica todos os efeitos de mixagem a um item de audio.

    Parametros em `params` (todos opcionais, com defaults):
        volume (0-200, default 100), pan (-100..100), speed (25-400, default 100),
        pitch (semitons, default 0), fade_in (segundos), fade_out (segundos),
        eq_low/eq_mid/eq_high (dB, default 0), reverb (0-100, default 0)

    Retorna: (stereo_float32, sample_rate) ou (None, 0) em caso de erro.
    """
    p = Path(file_path)
    if not p.exists():
        return None, 0

    try:
        import soundfile as sf
        data, sr = sf.read(file_path, dtype="float32")
        audio = np.array(data.mean(axis=1) if len(data.shape) > 1 else data, copy=True)
    except Exception:
        return None, 0

    # Aplicar file_offset e limitar ao duration antes de qualquer efeito
    if file_offset > 0:
        offset_samples = int(file_offset * sr)
        audio = audio[offset_samples:]
    if duration > 0:
        duration_samples = int(duration * sr)
        if len(audio) > duration_samples:
            audio = audio[:duration_samples]

    def _get(key, default, divisor=1):
        try:
            return float(params.get(key, default)) / divisor
        except (TypeError, ValueError):
            return default / divisor

    speed  = _get("speed",  100, 100)
    pitch  = _get("pitch",  0)
    volume = _get("volume", 100, 100)
    pan    = _get("pan",    0,   100)
    fade_in  = _get("fade_in",  0, 10)
    fade_out = _get("fade_out", 0, 10)
    eq_low   = _get("eq_low",  0)
    eq_mid   = _get("eq_mid",  0)
    eq_high  = _get("eq_high", 0)
    reverb   = _get("reverb",  0, 100)

    if speed != 1.0:
        new_len = max(1, int(len(audio) / speed))
        audio = np.interp(np.linspace(0, len(audio) - 1, new_len), np.arange(len(audio)), audio)

    if pitch != 0:
        factor = 2.0 ** (pitch / 12.0)
        stretched_len = max(1, int(len(audio) / factor))
        pitched = np.interp(np.linspace(0, len(audio) - 1, stretched_len), np.arange(len(audio)), audio)
        if len(pitched) >= len(audio):
            pitched = pitched[:len(audio)]
        else:
            pitched = np.pad(pitched, (0, len(audio) - len(pitched)))
        audio = pitched

    if eq_low != 0 or eq_mid != 0 or eq_high != 0:
        try:
            from scipy.signal import butter, lfilter
            b, a = butter(2, 300 / (sr / 2), btype="low")
            low = lfilter(b, a, audio)
            b, a = butter(2, 3000 / (sr / 2), btype="high")
            high = lfilter(b, a, audio)
            mid = audio - low - high
            audio = (low  * 10 ** (eq_low  / 20.0) +
                     mid  * 10 ** (eq_mid  / 20.0) +
                     high * 10 ** (eq_high / 20.0))
        except ImportError:
            pass

    audio = audio * volume

    if volume_keyframes and len(volume_keyframes) >= 2:
        audio = apply_volume_keyframes(audio, sr, volume_keyframes, duration)

    # Aplicar regioes silenciadas (em segundos relativos ao início do item) — remove os trechos
    muted = muted_regions or params.get('_muted_regions', [])
    if muted:
        keep = []
        prev = 0
        for region in sorted(muted, key=lambda r: r['start']):
            ca = int(float(region['start']) * sr)
            cb = int(float(region['end']) * sr)
            ca = max(0, min(ca, len(audio)))
            cb = max(ca, min(cb, len(audio)))
            if ca > prev:
                keep.append(audio[prev:ca])
            prev = cb
        if prev < len(audio):
            keep.append(audio[prev:])
        audio = np.concatenate(keep) if keep else np.array([], dtype=np.float32)

    if fade_in > 0:
        n = min(int(fade_in * sr), len(audio))
        if n > 0:
            audio[:n] *= np.linspace(0, 1, n)
    if fade_out > 0:
        n = min(int(fade_out * sr), len(audio))
        if n > 0:
            audio[-n:] *= np.linspace(1, 0, n)

    stereo = np.column_stack([
        audio * min(1.0, 1.0 - pan),
        audio * min(1.0, 1.0 + pan),
    ])

    if reverb > 0:
        reverb_len = int(0.3 * sr)
        impulse = np.exp(-np.linspace(0, 5, reverb_len))
        impulse = impulse / impulse.sum()
        wet_l = np.convolve(stereo[:, 0], impulse)[:len(audio)]
        wet_r = np.convolve(stereo[:, 1], impulse)[:len(audio)]
        stereo[:, 0] = stereo[:, 0] * (1 - reverb) + wet_l * reverb
        stereo[:, 1] = stereo[:, 1] * (1 - reverb) + wet_r * reverb

    return np.clip(stereo, -1.0, 1.0).astype(np.float32), sr


def compute_normalize_gain(file_path: str, mode: str, target: float = -1.0, file_offset: float = 0.0, duration: float = 0.0) -> float:
    """Calcula o ganho (0..200, escala do slider VOL) necessario para normalizar.

    mode:
        'peak'  -> normaliza pelo pico para target dBFS
        'lufs'  -> normaliza pelo loudness integrado para target LUFS (aproximacao RMS)

    Retorna o valor inteiro para o slider VOL (0-200), ou -1 em caso de erro.
    """
    try:
        import soundfile as sf
        data, sr = sf.read(file_path, dtype="float32")
        mono = data.mean(axis=1) if data.ndim > 1 else data

        if file_offset > 0:
            mono = mono[int(file_offset * sr):]
        if duration > 0:
            mono = mono[:int(duration * sr)]

        if len(mono) == 0:
            return -1

        if mode == "peak":
            peak = float(np.max(np.abs(mono)))
            if peak < 1e-9:
                return -1
            target_linear = 10 ** (target / 20.0)
            gain_linear = target_linear / peak
        else:  # lufs — aproximacao via RMS integrado
            rms = float(np.sqrt(np.mean(mono ** 2)))
            if rms < 1e-9:
                return -1
            rms_db = 20 * np.log10(rms)
            current_lufs_approx = rms_db + 3.0
            gain_db = target - current_lufs_approx
            gain_linear = 10 ** (gain_db / 20.0)

        vol_value = int(round(gain_linear * 100))
        return max(0, min(200, vol_value))
    except Exception:
        return -1


def slice_volume_keyframes(keyframes: list, duration: float, seg_start: float, seg_end: float) -> list:
    """Recorta keyframes para [seg_start, seg_end] e remapeia tempo para 0..seg_len."""
    if not keyframes:
        return []
    dur = max(0.001, float(duration))
    a = max(0.0, min(dur, float(seg_start)))
    b = max(a,   min(dur, float(seg_end)))
    if b - a <= 1e-6:
        return []

    pts = sorted(
        [{"time": float(k.get("time", 0.0)), "value": float(k.get("value", 1.0))} for k in keyframes],
        key=lambda k: k["time"],
    )

    def _value_at(t):
        if t <= pts[0]["time"]:  return pts[0]["value"]
        if t >= pts[-1]["time"]: return pts[-1]["value"]
        for i in range(1, len(pts)):
            p0, p1 = pts[i - 1], pts[i]
            if p0["time"] <= t <= p1["time"]:
                dt = p1["time"] - p0["time"]
                if dt <= 1e-9: return p1["value"]
                return p0["value"] + (p1["value"] - p0["value"]) * (t - p0["time"]) / dt
        return pts[-1]["value"]

    sliced = [{"time": 0.0, "value": round(_value_at(a), 3)}]
    for p in pts:
        if a < p["time"] < b:
            sliced.append({"time": round(p["time"] - a, 2), "value": round(p["value"], 3)})
    sliced.append({"time": round(b - a, 2), "value": round(_value_at(b), 3)})

    dedup = {round(float(p["time"]), 2): round(float(p["value"]), 3) for p in sliced}
    return [{"time": t, "value": dedup[t]} for t in sorted(dedup)]


def split_volume_keyframes(keyframes: list, duration: float, cut_time: float) -> Tuple[list, list]:
    """Divide keyframes em duas listas mantendo continuidade no ponto de corte."""
    cut = max(0.0, min(float(duration), float(cut_time)))
    if not keyframes:
        return [], []

    pts = sorted(
        [{"time": float(k.get("time", 0.0)), "value": float(k.get("value", 1.0))} for k in keyframes],
        key=lambda k: k["time"],
    )

    def _value_at(t):
        if t <= pts[0]["time"]:  return pts[0]["value"]
        if t >= pts[-1]["time"]: return pts[-1]["value"]
        for i in range(1, len(pts)):
            a, b = pts[i - 1], pts[i]
            if a["time"] <= t <= b["time"]:
                dt = b["time"] - a["time"]
                if dt <= 1e-9: return b["value"]
                return a["value"] + (b["value"] - a["value"]) * (t - a["time"]) / dt
        return pts[-1]["value"]

    v_cut = _value_at(cut)
    left  = [p for p in pts if p["time"] < cut - 1e-6]
    left.append({"time": round(cut, 2), "value": round(v_cut, 3)})
    right = [{"time": 0.0, "value": round(v_cut, 3)}]
    right += [{"time": round(p["time"] - cut, 2), "value": round(p["value"], 3)}
              for p in pts if p["time"] > cut + 1e-6]

    left.sort(key=lambda k: k["time"])
    right.sort(key=lambda k: k["time"])
    return left, right


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
