"""TTS Provider - Gera voz via múltiplas engines.

Engines suportadas:
    - edge-tts (Microsoft Edge, gratuito, sem GPU)
    - bark (Suno, local, GPU ~5GB, emoções reais)
    - xtts (Coqui, local, GPU ~4GB, voice cloning)
    - parler (HuggingFace, local, GPU ~4GB, describe voice)
    - elevenlabs (API paga, melhor qualidade)
"""

import asyncio
import logging
import wave
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


# ============================================================
# EDGE-TTS (padrão, gratuito, sem GPU)
# ============================================================

async def _generate_edge_tts(
    text: str,
    output_path: Path,
    voice: str = "pt-BR-AntonioNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    ssml: str = "",
) -> Path:
    """Gera WAV via edge-tts."""
    import edge_tts

    if ssml:
        # edge-tts não suporta SSML direto via Communicate,
        # usar pitch/rate/volume como params
        pass

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )

    mp3_path = output_path.with_suffix(".mp3")
    await communicate.save(str(mp3_path))
    _mp3_to_wav(mp3_path, output_path)
    try:
        mp3_path.unlink(missing_ok=True)
    except OSError as _e:
        logger.debug(f"Suppressed: {_e}")
    return output_path


# ============================================================
# BARK (emoções reais, GPU)
# ============================================================

def _generate_bark(
    text: str,
    output_path: Path,
    speaker: str = "v2/pt_speaker_0",
) -> Optional[Path]:
    """Gera WAV via Bark (Suno). Requer GPU ~5GB."""
    try:
        from bark import generate_audio, SAMPLE_RATE
        import numpy as np

        audio_array = generate_audio(text, history_prompt=speaker)

        # Salvar como WAV
        audio_int16 = (np.clip(audio_array, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        return output_path
    except ImportError:
        logger.error("Bark não instalado. pip install git+https://github.com/suno-ai/bark.git")
        return None
    except Exception as e:
        logger.error(f"Bark failed: {e}")
        return None


# ============================================================
# XTTS (voice cloning, GPU)
# ============================================================

def _generate_xtts(
    text: str,
    output_path: Path,
    speaker_wav: str = "",
    language: str = "pt",
) -> Optional[Path]:
    """Gera WAV via Coqui XTTS v2 (voice cloning). Requer GPU ~4GB."""
    try:
        from TTS.api import TTS

        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        tts.tts_to_file(
            text=text,
            speaker_wav=speaker_wav,
            language=language,
            file_path=str(output_path),
        )
        return output_path
    except ImportError:
        logger.error("Coqui TTS não instalado. pip install TTS")
        return None
    except Exception as e:
        logger.error(f"XTTS failed: {e}")
        return None


# ============================================================
# PARLER-TTS (describe voice, GPU)
# ============================================================

def _generate_parler(
    text: str,
    output_path: Path,
    description: str = "A deep male voice, slow pace, calm",
) -> Optional[Path]:
    """Gera WAV via Parler-TTS (voice from description). Requer GPU ~4GB."""
    try:
        import torch
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        import numpy as np

        model = ParlerTTSForConditionalGeneration.from_pretrained("parler-tts/parler-tts-mini-v1")
        tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-mini-v1")

        input_ids = tokenizer(description, return_tensors="pt").input_ids
        prompt_ids = tokenizer(text, return_tensors="pt").input_ids

        generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_ids)
        audio = generation.cpu().numpy().squeeze()

        audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        sr = model.config.sampling_rate
        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())

        return output_path
    except ImportError:
        logger.error("Parler-TTS não instalado. pip install parler-tts")
        return None
    except Exception as e:
        logger.error(f"Parler failed: {e}")
        return None


# ============================================================
# ELEVENLABS (API paga, melhor qualidade)
# ============================================================

def _generate_elevenlabs(
    text: str,
    output_path: Path,
    voice_id: str = "",
    stability: float = 0.5,
    similarity: float = 0.75,
    style: float = 0.5,
) -> Optional[Path]:
    """Gera WAV via ElevenLabs API. Requer API key."""
    try:
        from elevenlabs import generate, set_api_key, Voice, VoiceSettings
        import os

        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            logger.error("ELEVENLABS_API_KEY não configurada")
            return None

        set_api_key(api_key)

        audio = generate(
            text=text,
            voice=Voice(
                voice_id=voice_id,
                settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=similarity,
                    style=style,
                )
            ),
        )

        with open(str(output_path), "wb") as f:
            f.write(audio)

        return output_path
    except ImportError:
        logger.error("ElevenLabs não instalado. pip install elevenlabs")
        return None
    except Exception as e:
        logger.error(f"ElevenLabs failed: {e}")
        return None


# ============================================================
# POST-PROCESSING (simula respiração, rouquidão, tremor)
# ============================================================

def _apply_post_processing(wav_path: Path, params: dict) -> Path:
    """Aplica efeitos de pós-processamento no áudio gerado."""
    breathiness = params.get("breathiness", 0)
    roughness = params.get("roughness", 0)
    tremor = params.get("tremor", 0)

    if breathiness == 0 and roughness == 0 and tremor == 0:
        return wav_path

    try:
        import numpy as np

        with wave.open(str(wav_path), "r") as wf:
            sr = wf.getframerate()
            channels = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        # Tremor (vibrato leve no pitch — simulado com AM)
        if tremor > 0:
            t = np.arange(len(audio)) / sr
            tremor_freq = 5.0 + (tremor / 100.0) * 3.0  # 5-8 Hz
            tremor_depth = (tremor / 100.0) * 0.08
            modulation = 1.0 + tremor_depth * np.sin(2 * np.pi * tremor_freq * t)
            audio = audio * modulation

        # Breathiness (adiciona ruído branco suave)
        if breathiness > 0:
            noise = np.random.randn(len(audio)) * (breathiness / 100.0) * 0.03
            audio = audio + noise

        # Roughness (distorção suave / saturação)
        if roughness > 0:
            gain = 1.0 + (roughness / 100.0) * 2.0
            audio = np.tanh(audio * gain) / gain

        # Normalizar
        peak = np.abs(audio).max()
        if peak > 0.95:
            audio = audio * (0.9 / peak)

        audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())

        return wav_path
    except Exception as e:
        logger.warning(f"Post-processing failed: {e}")
        return wav_path


# ============================================================
# API PÚBLICA (unificada)
# ============================================================

def generate_voice(
    text: str,
    output_path: str | Path,
    voice_id: str = "",
    gender: str = "male",
    language: str = "pt-BR",
    emotion: str = "neutral",
    voice_profile: dict = None,
) -> Optional[Path]:
    """API principal — gera voz usando VoiceProfile ou params simples.

    Se voice_profile é fornecido (dict de build_speech_params), usa ele.
    Senão, usa params legados (voice_id/gender/emotion).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parar playback anterior para liberar arquivo
    stop_audio()

    # Se temos voice_profile completo (vem do voice_engine)
    if voice_profile:
        return _generate_with_profile(text, output_path, voice_profile)

    # Fallback legado (edge-tts simples)
    return _generate_legacy(text, output_path, voice_id, gender, language, emotion)


def _generate_with_profile(text: str, output_path: Path, params: dict) -> Optional[Path]:
    """Gera usando params completos do voice_engine.build_speech_params()."""
    engine = params.get("engine", "edge-tts")

    try:
        if engine == "edge-tts":
            pitch = params.get("pitch", 0)
            rate = params.get("rate", 0)
            volume = params.get("volume", 100)
            asyncio.run(_generate_edge_tts(
                text=params.get("text", text),
                output_path=output_path,
                voice=params.get("voice_id", "pt-BR-AntonioNeural"),
                pitch=f"{pitch:+d}Hz",
                rate=f"{rate:+d}%",
                volume=f"{volume - 100:+d}%",
            ))

        elif engine == "bark":
            result = _generate_bark(
                text=params.get("bark_text", text),
                output_path=output_path,
                speaker=params.get("bark_speaker", "v2/pt_speaker_0"),
            )
            if not result:
                # Fallback para edge-tts
                return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})

        elif engine == "xtts":
            sample = params.get("voice_sample_path", "")
            if not sample or not Path(sample).exists():
                return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})
            result = _generate_xtts(
                text=text,
                output_path=output_path,
                speaker_wav=sample,
                language=params.get("language", "pt")[:2],
            )
            if not result:
                return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})

        elif engine == "parler":
            desc = params.get("voice_description", "A male voice, neutral tone")
            result = _generate_parler(text=text, output_path=output_path, description=desc)
            if not result:
                return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})

        elif engine == "elevenlabs":
            result = _generate_elevenlabs(
                text=text,
                output_path=output_path,
                voice_id=params.get("elevenlabs_voice_id", ""),
                stability=params.get("elevenlabs_stability", 0.5),
                similarity=params.get("elevenlabs_similarity", 0.75),
                style=params.get("elevenlabs_style", 0.5),
            )
            if not result:
                return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})

        else:
            # Engine desconhecida → edge-tts
            return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})

        # Post-processing
        post = params.get("post_processing", {})
        if any(v > 0 for v in post.values()):
            _apply_post_processing(output_path, post)

        logger.info(f"TTS OK [{engine}]: '{text[:30]}' → {output_path.name}")
        return output_path

    except Exception as e:
        logger.error(f"TTS [{engine}] failed: {e}")
        # Fallback final
        if engine != "edge-tts":
            return _generate_with_profile(text, output_path, {**params, "engine": "edge-tts"})
        return None


def _generate_legacy(
    text: str,
    output_path: Path,
    voice_id: str,
    gender: str,
    language: str,
    emotion: str,
) -> Optional[Path]:
    """Geração legada (compatibilidade com código antigo)."""
    # Mapeamento de emoção → rate
    EMOTION_RATE_MAP = {
        "neutral": "+0%", "calm": "-10%", "happy": "+10%",
        "sad": "-15%", "angry": "+20%", "fear": "+15%",
        "tension": "+5%", "relief": "-5%",
    }

    DEFAULT_VOICES = {
        "pt-BR-male": "pt-BR-AntonioNeural",
        "pt-BR-female": "pt-BR-FranciscaNeural",
        "en-US-male": "en-US-GuyNeural",
        "en-US-female": "en-US-JennyNeural",
    }

    if not voice_id:
        key = f"{language}-{gender}"
        voice_id = DEFAULT_VOICES.get(key, DEFAULT_VOICES["pt-BR-male"])

    rate = EMOTION_RATE_MAP.get(emotion, "+0%")

    try:
        asyncio.run(_generate_edge_tts(
            text=text, output_path=output_path, voice=voice_id, rate=rate))
        logger.info(f"TTS OK [legacy]: '{text[:30]}' → {output_path.name} ({voice_id})")
        return output_path
    except Exception as e:
        logger.error(f"TTS legacy failed: {e}")
        return None


# ============================================================
# UTILIDADES
# ============================================================

def _mp3_to_wav(mp3_path: Path, wav_path: Path):
    """Converte MP3 para WAV. Tenta ffmpeg > pydub > miniaudio > raw copy."""
    import shutil
    import subprocess

    # 1. ffmpeg (melhor - para quando tiver instalado)
    ffmpeg_path = _find_ffmpeg()
    if ffmpeg_path:
        try:
            cmd = [
                ffmpeg_path, "-y", "-i", str(mp3_path),
                "-ar", "44100", "-ac", "1", "-sample_fmt", "s16",
                str(wav_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            return
        except Exception as _e:
            logger.debug(f"Suppressed: {_e}")

    # 2. pydub (precisa de ffmpeg tambem, mas tenta)
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio = audio.set_frame_rate(44100).set_channels(1).set_sample_width(2)
        audio.export(str(wav_path), format="wav")
        return
    except Exception as _e:
        logger.debug(f"Suppressed: {_e}")

    # 3. miniaudio (decoder MP3 embutido, sem dependencias externas)
    try:
        import miniaudio
        import struct
        decoded = miniaudio.decode_file(str(mp3_path), output_format=miniaudio.SampleFormat.SIGNED16,
                                         nchannels=1, sample_rate=44100)
        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(decoded.samples)
        return
    except Exception as _e:
        logger.debug(f"Suppressed: {_e}")

    # 4. Fallback: copia raw (winsound nao vai tocar)
    shutil.copy(str(mp3_path), str(wav_path))
    logger.warning("Sem decoder MP3 disponivel - instale miniaudio: pip install miniaudio")


def _find_ffmpeg() -> Optional[str]:
    """Encontra ffmpeg: PATH > ffmpeg-downloader > None."""
    import shutil
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    local = Path.home() / "AppData" / "Local" / "ffmpegio" / "ffmpeg-downloader" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local.exists():
        return str(local)
    return None




async def list_voices(language_filter: str = "pt-BR") -> List[Dict]:
    """Lista vozes disponíveis do edge-tts."""
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


def estimate_duration(text: str, rate: int = 0) -> float:
    """Estima duração da fala em segundos."""
    chars_per_sec = 13.0
    speed_factor = 1.0 + (rate / 100.0)
    return max(0.5, len(text) / (chars_per_sec * speed_factor))


def play_audio(path: Path):
    """Toca WAV de forma async sem travar arquivos."""
    import winsound
    path = Path(path)
    if not path.exists():
        return
    try:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as _e:
        logger.debug(f"Suppressed: {_e}")


def stop_audio():
    """Para playback atual."""
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception as _e:
        logger.debug(f"Suppressed: {_e}")
