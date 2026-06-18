"""Voice Engine - Sistema profissional de voz por personagem.

Arquitetura:
    VoiceProfile (identidade fixa) + EmotionModifier (varia por cena)
    → build_speech() → TTS engine (edge-tts / bark / xtts / parler / elevenlabs)

Fluxo:
    1. Character tem um VoiceProfile salvo (timbre, pitch, rate, aspereza...)
    2. Storyboard define emoção por cena (medo, raiva, tristeza...)
    3. AudioDirector chama: voice_engine.build_speech(profile, text, emotion)
    4. O engine gera o áudio final com timbre + emoção aplicada
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================
# EMOTION MODIFIERS
# ============================================================

@dataclass
class EmotionModifier:
    """Modificador de emoção sobre a voz base."""
    name: str = "neutral"
    pitch_delta: int = 0        # Hz (-20 a +20)
    rate_delta: int = 0         # % (-50 a +50)
    volume_delta: int = 0       # % (-50 a +50)
    tremor: int = 0             # 0-100 (variação micro de pitch)
    pausas: int = 0             # 0-100 (insere breaks no texto)
    quebras: int = 0            # 0-100 (voz falha/corta)
    intensidade: int = 70       # 0-100 (escala todos os deltas)
    bark_tags: List[str] = field(default_factory=list)  # tags bark: [gasps], [sighs]...


# Emoções pré-definidas (o usuario pode customizar)
DEFAULT_EMOTIONS: Dict[str, EmotionModifier] = {
    "neutral": EmotionModifier(name="neutral"),
    "fear": EmotionModifier(
        name="fear", pitch_delta=5, rate_delta=20, volume_delta=-10,
        tremor=70, pausas=50, quebras=40, bark_tags=["[gasps]", "[nervous breathing]"]),
    "anger": EmotionModifier(
        name="anger", pitch_delta=-3, rate_delta=15, volume_delta=30,
        tremor=10, pausas=0, quebras=0, bark_tags=["[angrily]"]),
    "sadness": EmotionModifier(
        name="sadness", pitch_delta=-5, rate_delta=-25, volume_delta=-20,
        tremor=20, pausas=60, quebras=10, bark_tags=["[sighs]", "[sadly]"]),
    "whisper": EmotionModifier(
        name="whisper", pitch_delta=2, rate_delta=-10, volume_delta=-40,
        tremor=5, pausas=30, quebras=0, bark_tags=["[whispers]"]),
    "shout": EmotionModifier(
        name="shout", pitch_delta=8, rate_delta=10, volume_delta=50,
        tremor=15, pausas=0, quebras=5, bark_tags=["[shouts]"]),
    "sarcasm": EmotionModifier(
        name="sarcasm", pitch_delta=3, rate_delta=-5, volume_delta=5,
        tremor=0, pausas=20, quebras=0, bark_tags=["[sarcastically]"]),
    "despair": EmotionModifier(
        name="despair", pitch_delta=10, rate_delta=30, volume_delta=10,
        tremor=90, pausas=40, quebras=60, bark_tags=["[gasps]", "[crying]"]),
    "joy": EmotionModifier(
        name="joy", pitch_delta=5, rate_delta=10, volume_delta=10,
        tremor=0, pausas=0, quebras=0, bark_tags=["[laughs]", "[happily]"]),
    "seduction": EmotionModifier(
        name="seduction", pitch_delta=-2, rate_delta=-15, volume_delta=-15,
        tremor=5, pausas=40, quebras=0, bark_tags=["[softly]"]),
    "fatigue": EmotionModifier(
        name="fatigue", pitch_delta=-3, rate_delta=-20, volume_delta=-20,
        tremor=30, pausas=70, quebras=20, bark_tags=["[sighs]", "[exhausted]"]),
    "tension": EmotionModifier(
        name="tension", pitch_delta=3, rate_delta=5, volume_delta=0,
        tremor=30, pausas=20, quebras=10, bark_tags=["[tense]"]),
    "relief": EmotionModifier(
        name="relief", pitch_delta=-2, rate_delta=-10, volume_delta=-5,
        tremor=0, pausas=30, quebras=0, bark_tags=["[sighs with relief]"]),
}

# Mapeamento PT → EN para emoções do storyboard
EMOTION_ALIASES = {
    "neutro": "neutral", "medo": "fear", "raiva": "anger",
    "triste": "sadness", "tristeza": "sadness", "sussurro": "whisper",
    "grito": "shout", "sarcasmo": "sarcasm", "desespero": "despair",
    "alegria": "joy", "feliz": "joy", "seducao": "seduction",
    "cansaco": "fatigue", "cansado": "fatigue", "tensao": "tension",
    "alivio": "relief", "angry": "anger", "sad": "sadness",
    "happy": "joy", "calm": "neutral", "tension": "tension",
}


# ============================================================
# VOICE PROFILE
# ============================================================

@dataclass
class VoiceProfile:
    """Perfil de voz completo de um personagem."""
    # Engine
    engine: str = "edge-tts"  # edge-tts | bark | xtts | parler | elevenlabs

    # Timbre base (edge-tts / bark)
    voice_id: str = "pt-BR-AntonioNeural"
    language: str = "pt-BR"
    gender: str = "male"

    # Parâmetros base
    pitch_base: int = 0         # Hz (-20 a +20)
    rate_base: int = 0          # % (-50 a +50)
    volume_base: int = 100      # % (50 a 150)

    # Post-processing (simulação via audio manipulation)
    breathiness: int = 0        # 0-100 (ar na voz)
    roughness: int = 0          # 0-100 (rouquidão)
    emphasis: int = 50          # 0-100 (dramaticidade)

    # Bark-specific
    bark_speaker: str = "v2/pt_speaker_0"  # preset do bark

    # XTTS-specific
    voice_sample_path: str = ""  # path do audio de referência (15s)

    # Parler-specific
    voice_description: str = ""  # "old man, deep raspy voice, slow pace"

    # ElevenLabs-specific
    elevenlabs_voice_id: str = ""
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity: float = 0.75
    elevenlabs_style: float = 0.5

    # Emoções customizadas (overrides dos defaults)
    custom_emotions: Dict[str, dict] = field(default_factory=dict)

    def get_emotion(self, emotion_name: str) -> EmotionModifier:
        """Retorna EmotionModifier para a emoção (custom ou default)."""
        # Normalizar nome
        key = EMOTION_ALIASES.get(emotion_name.lower().strip(), emotion_name.lower().strip())
        # Custom override?
        if key in self.custom_emotions:
            return EmotionModifier(**self.custom_emotions[key])
        # Default
        return DEFAULT_EMOTIONS.get(key, DEFAULT_EMOTIONS["neutral"])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceProfile":
        if not data:
            return cls()
        # Filtrar campos invalidos
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


# ============================================================
# PRESETS DE VOZ
# ============================================================

VOICE_PRESETS: Dict[str, VoiceProfile] = {
    "heroi_grave": VoiceProfile(
        voice_id="en-US-ChristopherNeural", pitch_base=-10, rate_base=-5,
        roughness=20, emphasis=80, gender="male",
        bark_speaker="v2/pt_speaker_4",
        voice_description="deep male voice, heroic, confident, slow pace"),
    "vilao_sombrio": VoiceProfile(
        voice_id="en-US-RogerNeural", pitch_base=-15, rate_base=-10,
        roughness=40, emphasis=70, breathiness=10, gender="male",
        bark_speaker="v2/pt_speaker_6",
        voice_description="dark sinister male voice, deep, menacing, slow"),
    "jovem_nervoso": VoiceProfile(
        voice_id="en-US-BrianNeural", pitch_base=5, rate_base=10,
        roughness=0, emphasis=40, gender="male",
        bark_speaker="v2/pt_speaker_1",
        voice_description="young nervous male voice, fast, slightly high pitched"),
    "ancia_sabia": VoiceProfile(
        voice_id="en-US-JennyNeural", pitch_base=-5, rate_base=-20,
        roughness=30, breathiness=20, emphasis=60, gender="female",
        bark_speaker="v2/pt_speaker_9",
        voice_description="old wise female voice, slow, gentle, raspy"),
    "crianca": VoiceProfile(
        voice_id="en-US-AnaNeural", pitch_base=10, rate_base=5,
        roughness=0, emphasis=30, gender="female",
        bark_speaker="v2/pt_speaker_2",
        voice_description="young child voice, high pitched, innocent, cute"),
    "narrador_epico": VoiceProfile(
        voice_id="en-US-GuyNeural", pitch_base=-5, rate_base=-15,
        roughness=10, emphasis=90, gender="male",
        bark_speaker="v2/pt_speaker_0",
        voice_description="epic narrator male voice, deep, dramatic, authoritative"),
    "soldado_cansado": VoiceProfile(
        voice_id="en-US-EricNeural", pitch_base=-3, rate_base=-10,
        roughness=35, breathiness=30, emphasis=40, gender="male",
        bark_speaker="v2/pt_speaker_5",
        voice_description="tired male soldier voice, rough, exhausted, deep"),
    "femme_fatale": VoiceProfile(
        voice_id="en-US-AriaNeural", pitch_base=-2, rate_base=-10,
        roughness=5, breathiness=25, emphasis=70, gender="female",
        bark_speaker="v2/pt_speaker_8",
        voice_description="seductive female voice, smooth, low, breathy, slow"),
}


# ============================================================
# SPEECH BUILDER
# ============================================================

def build_speech_params(profile: VoiceProfile, text: str, emotion: str = "neutral") -> dict:
    """Constrói parâmetros de geração baseado no profile + emoção.

    Retorna dict com tudo necessário para o tts_provider gerar:
        engine, voice_id, text (processado), ssml, pitch, rate, volume,
        post_processing, bark_tags, etc.
    """
    em = profile.get_emotion(emotion)
    intensity = em.intensidade / 100.0

    # Calcular valores finais (base + delta escalado pela intensidade)
    final_pitch = profile.pitch_base + int(em.pitch_delta * intensity)
    final_rate = profile.rate_base + int(em.rate_delta * intensity)
    final_volume = profile.volume_base + int(em.volume_delta * intensity)

    # Processar texto (inserir pausas/quebras baseado na emoção)
    processed_text = _apply_text_effects(text, em, intensity)

    # Construir SSML (para edge-tts)
    ssml = _build_ssml(processed_text, profile.voice_id, final_pitch, final_rate, final_volume)

    # Bark text (com tags)
    bark_text = _build_bark_text(text, em, intensity)

    return {
        "engine": profile.engine,
        "voice_id": profile.voice_id,
        "language": profile.language,
        "text": processed_text,
        "ssml": ssml,
        "pitch": final_pitch,
        "rate": final_rate,
        "volume": final_volume,
        "post_processing": {
            "breathiness": profile.breathiness,
            "roughness": profile.roughness,
            "emphasis": profile.emphasis,
            "tremor": int(em.tremor * intensity),
        },
        # Bark
        "bark_speaker": profile.bark_speaker,
        "bark_text": bark_text,
        # XTTS
        "voice_sample_path": profile.voice_sample_path,
        # Parler
        "voice_description": profile.voice_description,
        # ElevenLabs
        "elevenlabs_voice_id": profile.elevenlabs_voice_id,
        "elevenlabs_stability": profile.elevenlabs_stability,
        "elevenlabs_similarity": profile.elevenlabs_similarity,
        "elevenlabs_style": profile.elevenlabs_style,
    }


def _apply_text_effects(text: str, em: EmotionModifier, intensity: float) -> str:
    """Insere pausas e quebras no texto baseado na emoção."""
    if em.pausas == 0 and em.quebras == 0:
        return text

    import random
    random.seed(hash(text))  # determinístico por texto
    words = text.split()
    result = []

    pause_threshold = 1.0 - (em.pausas * intensity / 100.0)
    break_threshold = 1.0 - (em.quebras * intensity / 100.0)

    for i, word in enumerate(words):
        result.append(word)
        if i < len(words) - 1:
            r = random.random()
            # Pausas em pontuação natural
            if word.endswith((",", ".", "!", "?", "...", ";")):
                if r > pause_threshold * 0.5:
                    result.append("...")
            # Pausas aleatórias (hesitação)
            elif r > pause_threshold and em.pausas > 30:
                result.append("...")
            # Quebras (voz falha)
            elif r > break_threshold and em.quebras > 30:
                result.append("—")

    return " ".join(result)


def _build_ssml(text: str, voice_id: str, pitch: int, rate: int, volume: int) -> str:
    """Gera SSML completo para edge-tts."""
    pitch_str = f"{pitch:+d}Hz"
    rate_str = f"{rate:+d}%"
    volume_str = f"{volume - 100:+d}%" if volume != 100 else "+0%"

    # Converter ... em breaks SSML
    text_ssml = text.replace("...", '<break time="300ms"/>')
    text_ssml = text_ssml.replace("—", '<break time="150ms"/>')

    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pt-BR">'
        f'<voice name="{voice_id}">'
        f'<prosody pitch="{pitch_str}" rate="{rate_str}" volume="{volume_str}">'
        f'{text_ssml}'
        f'</prosody></voice></speak>'
    )
    return ssml


def _build_bark_text(text: str, em: EmotionModifier, intensity: float) -> str:
    """Gera texto com tags do Bark para emoção."""
    if not em.bark_tags:
        return text

    # Inserir tag principal no início
    prefix = em.bark_tags[0] + " " if em.bark_tags else ""
    # Se tem tag secundária, inserir no meio
    suffix = ""
    if len(em.bark_tags) > 1 and intensity > 0.5:
        suffix = " " + em.bark_tags[1]

    return f"{prefix}{text}{suffix}"


# ============================================================
# INTEGRAÇÃO COM AUDIO DIRECTOR
# ============================================================

def resolve_voice_for_scene(
    character_name: str,
    emotion: str,
    characters: list,
) -> Optional[dict]:
    """Busca VoiceProfile do personagem e retorna params de geração.

    Chamado pelo AudioDirector/AudioService ao gerar voz de uma cena.
    """
    # Buscar personagem pelo nome
    char = None
    name_lower = character_name.lower().strip()
    for c in characters:
        if c.name.lower().strip() == name_lower:
            char = c
            break

    if not char:
        return None

    # Carregar profile
    profile_data = getattr(char, "voice_profile", None)
    if isinstance(profile_data, dict):
        profile = VoiceProfile.from_dict(profile_data)
    else:
        profile = VoiceProfile()
        # Usar voice_id legado se existir
        if char.voice_id:
            profile.voice_id = char.voice_id

    return build_speech_params(profile, "", emotion)
