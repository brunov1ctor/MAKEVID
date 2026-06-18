"""Audio Service - Orquestra geracao de audio (TTS, SFX, Music, Ambience).

Pipeline:
    Storyboard → AudioDirector (plan) → AudioService (generate) → Timeline (TrackItems)

Providers suportados (configuravel):
    - Voice: ElevenLabs, Edge-TTS (gratuito), local
    - SFX: AI Foley, freesound, local
    - Music: Suno, MusicGen, local
    - Ambience: freesound, AI generation
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Callable, List, Dict

from makevid.config import AUDIO_DIR
from makevid.core.audio_director import AudioDirector, SceneAudioPlan

logger = logging.getLogger(__name__)


# Provider registry (extensivel)
VOICE_PROVIDERS = ["edge-tts", "elevenlabs", "local"]
MUSIC_PROVIDERS = ["suno", "musicgen", "local"]
SFX_PROVIDERS = ["ai-foley", "freesound", "local"]


class AudioService:
    """Orquestra geracao de audio para cenas do storyboard."""

    def __init__(self):
        self.director = AudioDirector()
        self.voice_provider = "edge-tts"
        self.music_provider = "local"
        self.sfx_provider = "local"

    def generate_scene_audio(
        self,
        project_id: str,
        scene_metadata: Dict[str, str],
        scene_index: int = 0,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        characters: list = None,
    ):
        """Gera todo o audio de uma cena em background."""
        self._characters = characters or []

        def run():
            try:
                plan = self.director.analyze_scene(scene_metadata, scene_index)
                out_dir = AUDIO_DIR / project_id / f"scene_{scene_index:03d}"
                out_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"AudioService: plan V={len(plan.voices)} S={len(plan.sfx)} A={plan.ambience is not None} M={plan.music is not None}")

                # Guardar visual para deteccao de genero
                self._current_visual = scene_metadata.get("visual", "")

                results = {}

                # Voice
                if plan.voices:
                    if on_progress:
                        on_progress(f"Gerando voz ({len(plan.voices)} falas)...")
                    try:
                        voice_paths = self._generate_voices(plan, out_dir)
                        if voice_paths:
                            results["voices"] = voice_paths
                    except Exception as e:
                        logger.warning(f"Voice generation failed: {e}")

                # Ambience
                if plan.ambience:
                    if on_progress:
                        on_progress("Gerando ambiencia...")
                    try:
                        amb_path = self._generate_ambience(plan, out_dir)
                        if amb_path:
                            results["ambience"] = amb_path
                    except Exception as e:
                        logger.warning(f"Ambience generation failed: {e}")

                # SFX
                if plan.sfx:
                    if on_progress:
                        on_progress(f"Gerando SFX ({len(plan.sfx)} efeitos)...")
                    try:
                        sfx_paths = self._generate_sfx(plan, out_dir)
                        if sfx_paths:
                            results["sfx"] = sfx_paths
                    except Exception as e:
                        logger.warning(f"SFX generation failed: {e}")

                # Music
                if plan.music:
                    if on_progress:
                        on_progress("Gerando musica...")
                    try:
                        music_path = self._generate_music(plan, out_dir)
                        if music_path:
                            results["music"] = music_path
                    except Exception as e:
                        logger.warning(f"Music generation failed: {e}")

                if on_done:
                    on_done(plan, results)

            except Exception as e:
                logger.error(f"AudioService error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    def generate_all_scenes(
        self,
        project_id: str,
        scenes: List[Dict[str, str]],
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        characters: list = None,
    ):
        """Gera audio para todas as cenas do storyboard."""
        self._characters = characters or []

        def run():
            try:
                plans = self.director.analyze_storyboard(scenes)
                all_results = []

                for i, plan in enumerate(plans):
                    if on_progress:
                        on_progress(f"Cena {i+1}/{len(plans)}...")

                    out_dir = AUDIO_DIR / project_id / f"scene_{i:03d}"
                    out_dir.mkdir(parents=True, exist_ok=True)

                    result = {}
                    if plan.voices:
                        result["voices"] = self._generate_voices(plan, out_dir)
                    if plan.ambience:
                        result["ambience"] = self._generate_ambience(plan, out_dir)
                    if plan.sfx:
                        result["sfx"] = self._generate_sfx(plan, out_dir)
                    if plan.music:
                        result["music"] = self._generate_music(plan, out_dir)

                    all_results.append((plan, result))

                if on_done:
                    on_done(all_results)

            except Exception as e:
                logger.error(f"AudioService batch error: {e}")
                if on_error:
                    on_error(str(e))

        threading.Thread(target=run, daemon=True).start()

    # ============================================================
    # GENERATORS (implementacao placeholder - cada provider sera um modulo)
    # ============================================================

    def _generate_voices(self, plan: SceneAudioPlan, out_dir: Path) -> List[str]:
        """Gera arquivos WAV de voz para cada VoicePlan usando VoiceProfile."""
        from makevid.core.tts_provider import generate_voice
        from makevid.core.voice_engine import resolve_voice_for_scene, build_speech_params, VoiceProfile

        # Buscar personagens do projeto
        characters = getattr(self, '_characters', [])

        paths = []
        for i, voice in enumerate(plan.voices):
            path = out_dir / f"voice_{i:02d}.wav"

            # Tentar resolver VoiceProfile do personagem
            voice_params = None
            if voice.character and characters:
                voice_params = resolve_voice_for_scene(
                    voice.character, voice.emotion, characters)
                if voice_params:
                    # Rebuild params com o texto real
                    char = next((c for c in characters if c.name.lower() == voice.character.lower()), None)
                    if char and char.voice_profile:
                        profile = VoiceProfile.from_dict(char.voice_profile)
                        voice_params = build_speech_params(profile, voice.text, voice.emotion)

            if voice_params:
                result = generate_voice(text=voice.text, output_path=path, voice_profile=voice_params)
            else:
                # Fallback: inferir genero do contexto
                context = (voice.text + " " + voice.character).lower()
                if hasattr(self, '_current_visual'):
                    context += " " + self._current_visual.lower()
                female_hints = ["woman", "girl", "she", "her", "mulher", "menina", "ela",
                                "maria", "ana", "female", "mother", "mae", "sister", "irma"]
                gender = "female" if any(h in context for h in female_hints) else "male"
                result = generate_voice(
                    text=voice.text, output_path=path,
                    gender=gender, emotion=voice.emotion)

            if result:
                paths.append(str(result))
            else:
                self._generate_silence(path, voice.end - voice.start)
                paths.append(str(path))
            logger.info(f"Voice generated: {voice.character} '{voice.text[:30]}' profile={'yes' if voice_params else 'no'}")
        return paths

    def _generate_ambience(self, plan: SceneAudioPlan, out_dir: Path) -> str:
        """Gera WAV de ambiencia via Freesound com layering."""
        from makevid.core.freesound_provider import search_and_download
        import numpy as np
        import wave

        duration = plan.ambience.duration or plan.scene_duration
        description = plan.ambience.description

        # Split layers (separated by |)
        queries = [q.strip() for q in description.split("|") if q.strip()]
        if not queries:
            queries = [description]

        # Download each layer
        layer_paths = []
        for i, query in enumerate(queries):
            layer_path = out_dir / f"amb_layer_{i:02d}"
            result = search_and_download(query, layer_path, max_duration=30)
            if result:
                layer_paths.append(result)
                logger.info(f"Ambience layer {i}: '{query}' → {result.name}")

        if not layer_paths:
            # Fallback: silencio
            fallback = out_dir / "ambience.wav"
            self._generate_silence(fallback, duration)
            return str(fallback)

        # Mix layers into single WAV (duracao natural, sem loop/corte)
        sr = 44100

        # Volume decreases per layer (base louder, details quieter)
        volumes = [0.7, 0.4, 0.3, 0.25, 0.2]

        # Primeiro pass: ler todos e descobrir duracao maxima
        layer_data = []
        max_samples = 0
        for i, path in enumerate(layer_paths):
            vol = volumes[i] if i < len(volumes) else 0.2
            try:
                import soundfile as sf
                raw, file_sr = sf.read(str(path), dtype="float32")
                if len(raw.shape) == 1:
                    raw = np.column_stack([raw, raw])
                elif raw.shape[1] == 1:
                    raw = np.column_stack([raw[:, 0], raw[:, 0]])
                # Resample if needed
                if file_sr != sr:
                    new_len = int(len(raw) * sr / file_sr)
                    raw = np.column_stack([
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 0]),
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 1]),
                    ])
                layer_data.append((raw, vol, i))
                if len(raw) > max_samples:
                    max_samples = len(raw)
            except Exception as e:
                logger.warning(f"Failed to read layer {i}: {e}")

        if max_samples == 0:
            fallback = out_dir / "ambience.wav"
            self._generate_silence(fallback, duration)
            return str(fallback)

        mix = np.zeros((max_samples, 2), dtype=np.float32)
        layer_metadata = []
        for raw, vol, i in layer_data:
            mix[:len(raw)] += raw * vol
            layer_metadata.append({"query": queries[i] if i < len(queries) else "",
                                   "volume": int(vol * 100)})

        # Normalize
        peak = np.abs(mix).max()
        if peak > 0.95:
            mix = mix * (0.9 / peak)

        mix_int16 = (np.clip(mix, -1.0, 1.0) * 32767).astype(np.int16)
        output_path = out_dir / "ambience.wav"
        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(mix_int16.tobytes())

        # Store metadata for layer editor
        self._last_ambience_layers = layer_metadata
        logger.info(f"Ambience mixed: {len(layer_paths)} layers → {output_path.name}")
        return str(output_path)

    def _generate_sfx(self, plan: SceneAudioPlan, out_dir: Path) -> List[str]:
        """Gera um unico WAV mixado com todos os SFX da cena."""
        from makevid.core.freesound_provider import search_and_download
        import numpy as np
        import wave

        sr = 44100
        layer_names = []
        # Primeiro pass: ler layers e calcular duracao total
        sfx_layers = []
        max_end = 0
        for i, sfx in enumerate(plan.sfx):
            path = out_dir / f"sfx_{i:02d}"
            result = search_and_download(sfx.description, path, max_duration=sfx.duration + 3)
            if not result:
                continue
            try:
                import soundfile as sf
                data, file_sr = sf.read(str(result), dtype="float32")
                if len(data.shape) == 1:
                    raw = np.column_stack([data, data])
                else:
                    raw = data if data.shape[1] == 2 else np.column_stack([data[:, 0], data[:, 0]])
                if file_sr != sr:
                    new_len = int(len(raw) * sr / file_sr)
                    raw = np.column_stack([
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 0]),
                        np.interp(np.linspace(0, len(raw)-1, new_len), np.arange(len(raw)), raw[:, 1]),
                    ])
                start_sample = int(sfx.time * sr)
                end = start_sample + len(raw)
                if end > max_end:
                    max_end = end
                sfx_layers.append((raw, start_sample, sfx.volume, sfx.description))
            except Exception as e:
                logger.warning(f"SFX layer failed: {e}")

        if not sfx_layers:
            return []

        mix = np.zeros((max_end, 2), dtype=np.float32)
        for raw, start_sample, vol, desc in sfx_layers:
            end_sample = start_sample + len(raw)
            mix[start_sample:end_sample] += raw * vol
            layer_names.append(desc)
            logger.info(f"SFX layer: '{desc}' at {start_sample/sr:.1f}s")

        # Normalize
        peak = np.abs(mix).max()
        if peak > 0.95:
            mix = mix * (0.9 / peak)

        # Salvar mix
        output_path = out_dir / "sfx_mix.wav"
        audio_int16 = (np.clip(mix, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())

        logger.info(f"SFX mixed: {len(layer_names)} layers → {output_path.name}")
        # Retorna path unico + metadata das layers
        self._last_sfx_layers = "|".join(layer_names)
        return [str(output_path)]

    def _generate_music(self, plan: SceneAudioPlan, out_dir: Path) -> str:
        """Gera WAV de musica via Freesound (busca por mood/genre)."""
        from makevid.core.freesound_provider import search_and_download
        import numpy as np
        import soundfile as sf
        import wave

        path = out_dir / "music"
        duration = plan.music.duration or plan.scene_duration
        mood = plan.music.mood or "ambient"

        # Buscar musica no Freesound (permitir arquivos mais longos)
        result = search_and_download(f"{mood} music loop", path, max_duration=30)
        if not result:
            result = search_and_download(f"{mood} background", path, max_duration=30)
        if not result:
            result = search_and_download("ambient music", path, max_duration=30)

        if result:
            # Manter duracao natural do audio (sem loop/corte)
            try:
                data, sr = sf.read(str(result), dtype="float32")
                if len(data.shape) == 1:
                    data = np.column_stack([data, data])
                # Fade in/out suave
                fade = int(0.5 * sr)
                if fade > 0 and len(data) > fade * 2:
                    data[:fade] *= np.linspace(0, 1, fade).reshape(-1, 1)
                    data[-fade:] *= np.linspace(1, 0, fade).reshape(-1, 1)
                # Salvar como WAV
                output_path = out_dir / "music.wav"
                audio_int16 = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
                with wave.open(str(output_path), "w") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(audio_int16.tobytes())
                logger.info(f"Music downloaded: mood='{mood}' → {output_path.name}")
                return str(output_path)
            except Exception as e:
                logger.warning(f"Music processing failed: {e}")

        # Fallback: silencio
        fallback = out_dir / "music.wav"
        self._generate_silence(fallback, duration)
        logger.info(f"Music fallback silence: mood='{mood}' → {fallback.name}")
        return str(fallback)

    def _generate_silence(self, path: Path, duration: float):
        """Placeholder: gera arquivo WAV silencioso."""
        import wave
        import numpy as np

        sr = 44100
        samples = int(duration * sr)
        audio = np.zeros(samples, dtype=np.int16)

        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio.tobytes())
