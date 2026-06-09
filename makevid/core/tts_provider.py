"""TTS Provider - Gera voz via edge-tts (Microsoft Edge, gratuito)."""

import asyncio
import logging
import wave
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Mapeamento de emoção → estilo de voz (edge-tts suporta via SSML)
EMOTION_RATE_MAP = {
    "neutral": "+0%",
    "calm": "-10%",
    "happy": "+10%",
    "sad": "-15%",
    "angry": "+20%",
    "fear": "+15%",
    "tension": "+5%",
    "relief": "-5%",
}

# Vozes padrão por gênero/idioma
DEFAULT_VOICES = {
    "pt-BR-male": "pt-BR-AntonioNeural",
    "pt-BR-female": "pt-BR-FranciscaNeural",
    "en-US-male": "en-US-GuyNeural",
    "en-US-female": "en-US-JennyNeural",
}


async def _generate_tts(
    text: str,
    output_path: Path,
    voice: str = "pt-BR-AntonioNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    """Gera WAV via edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )

    # edge-tts gera MP3, precisamos converter para WAV
    mp3_path = output_path.with_suffix(".mp3")
    await communicate.save(str(mp3_path))

    # Converter MP3 → WAV
    _mp3_to_wav(mp3_path, output_path)
    mp3_path.unlink(missing_ok=True)

    return output_path


def _mp3_to_wav(mp3_path: Path, wav_path: Path):
    """Converte MP3 para WAV."""
    import shutil
    import subprocess

    ffmpeg_path = _find_ffmpeg()
    if ffmpeg_path:
        cmd = [
            ffmpeg_path, "-y", "-i", str(mp3_path),
            "-ar", "44100", "-ac", "1", "-sample_fmt", "s16",
            str(wav_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    else:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(str(mp3_path))
            audio = audio.set_frame_rate(44100).set_channels(1).set_sample_width(2)
            audio.export(str(wav_path), format="wav")
        except Exception:
            shutil.copy(str(mp3_path), str(wav_path))
            logger.warning("Sem ffmpeg/pydub - audio pode nao funcionar")


def _find_ffmpeg() -> Optional[str]:
    """Encontra ffmpeg: PATH > ffmpeg-downloader > None."""
    import shutil
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    # Tentar path do ffmpeg-downloader
    local = Path.home() / "AppData" / "Local" / "ffmpegio" / "ffmpeg-downloader" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local.exists():
        return str(local)
    return None


def generate_voice(
    text: str,
    output_path: str | Path,
    voice_id: str = "",
    gender: str = "male",
    language: str = "pt-BR",
    emotion: str = "neutral",
) -> Optional[Path]:
    """API síncrona para gerar voz. Retorna path do WAV ou None."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Selecionar voz
    if not voice_id:
        key = f"{language}-{gender}"
        voice_id = DEFAULT_VOICES.get(key, DEFAULT_VOICES["pt-BR-male"])

    # Ajustar rate pela emoção
    rate = EMOTION_RATE_MAP.get(emotion, "+0%")

    try:
        asyncio.run(_generate_tts(
            text=text,
            output_path=output_path,
            voice=voice_id,
            rate=rate,
        ))
        logger.info(f"TTS OK: '{text[:30]}' → {output_path.name} ({voice_id})")
        return output_path
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return None


async def list_voices(language_filter: str = "pt-BR") -> List[Dict]:
    """Lista vozes disponíveis."""
    import edge_tts
    voices = await edge_tts.list_voices()
    if language_filter:
        voices = [v for v in voices if language_filter in v.get("Locale", "")]
    return voices


def get_available_voices(language: str = "pt-BR") -> List[Dict]:
    """API síncrona para listar vozes."""
    try:
        return asyncio.run(list_voices(language))
    except Exception:
        return []


def estimate_duration(text: str, rate: str = "+0%") -> float:
    """Estima duração da fala em segundos (heurística)."""
    # ~13 caracteres/segundo para pt-BR em velocidade normal
    chars_per_sec = 13.0
    rate_val = int(rate.replace("%", "").replace("+", "")) if rate != "+0%" else 0
    speed_factor = 1.0 + (rate_val / 100.0)
    return max(0.5, len(text) / (chars_per_sec * speed_factor))
