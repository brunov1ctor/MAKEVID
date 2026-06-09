"""Audio Director - Analisa cenas do storyboard e decide layers de audio.

Pipeline:
    Scene metadata → Audio Director → Timeline Plan (JSON)

O director recebe metadata de uma cena e produz um plano de audio
com timings relativos ao clip (scene_relative_time).
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class VoicePlan:
    """Plano de voz para uma cena."""
    text: str = ""
    character: str = ""
    emotion: str = "neutral"
    voice_id: str = ""
    start: float = 0.0  # offset relativo ao inicio da cena
    end: float = 0.0
    volume: float = 1.0


@dataclass
class SfxPlan:
    """Plano de efeito sonoro."""
    description: str = ""
    time: float = 0.0  # offset relativo ao inicio da cena
    duration: float = 1.0
    volume: float = 0.8


@dataclass
class AmbiencePlan:
    """Plano de ambiencia/ambiente."""
    description: str = ""
    start: float = 0.0
    duration: float = 0.0  # 0 = toda a cena
    volume: float = 0.4


@dataclass
class MusicPlan:
    """Plano de musica."""
    mood: str = ""
    start: float = 0.0
    duration: float = 0.0  # 0 = toda a cena
    volume: float = 0.2
    ducking: bool = True  # reduzir quando houver dialogo


@dataclass
class SceneAudioPlan:
    """Plano completo de audio para uma cena."""
    scene_index: int = 0
    scene_duration: float = 5.0
    voices: List[VoicePlan] = field(default_factory=list)
    sfx: List[SfxPlan] = field(default_factory=list)
    ambience: Optional[AmbiencePlan] = None
    music: Optional[MusicPlan] = None

    def to_dict(self) -> dict:
        return asdict(self)


class AudioDirector:
    """Analisa metadata de cena e produz plano de audio.

    Fluxo:
        1. Recebe scene_metadata (do storyboard expandido)
        2. Parseia dialogue, emotion, ambience, sfx, music_mood
        3. Estima duracao de fala (TTS estimation)
        4. Posiciona layers com offsets relativos
        5. Retorna SceneAudioPlan
    """

    # Estimativa de velocidade de fala (caracteres por segundo)
    CHARS_PER_SECOND = 12.0
    # Offset padrao antes da fala comecar
    VOICE_START_OFFSET = 0.5
    # Volume ducking quando ha dialogo
    MUSIC_DUCK_VOLUME = 0.08

    def analyze_scene(self, scene_metadata: Dict[str, str], scene_index: int = 0) -> SceneAudioPlan:
        """Analisa uma cena do storyboard e retorna plano de audio.
        Se não tem campos explícitos de audio, infere do prompt visual."""
        duration = float(scene_metadata.get("duration", 5.0))
        visual = scene_metadata.get("visual", "").strip()

        plan = SceneAudioPlan(
            scene_index=scene_index,
            scene_duration=duration,
        )

        # Voice (dialogue)
        dialogue = scene_metadata.get("dialogue", "").strip()
        if dialogue:
            plan.voices = self._plan_voices(dialogue, duration,
                                            scene_metadata.get("emotion", "neutral"))

        # SFX - explícito ou inferido do visual
        sfx_str = scene_metadata.get("sfx", "").strip()
        if not sfx_str:
            sfx_str = scene_metadata.get("audio", "").strip()  # campo legado SE/BGM
        if not sfx_str and visual:
            sfx_str = self._infer_sfx_from_prompt(visual)
        if sfx_str:
            plan.sfx = self._plan_sfx(sfx_str, duration)

        # Ambience - explícito ou inferido do visual
        ambience_str = scene_metadata.get("ambience", "").strip()
        if not ambience_str and visual:
            ambience_str = self._infer_ambience_from_prompt(visual)
        if ambience_str:
            plan.ambience = AmbiencePlan(description=ambience_str, duration=duration)

        # Music
        music_str = scene_metadata.get("music_mood", "").strip()
        if not music_str and visual:
            music_str = self._infer_music_from_prompt(visual)
        if music_str:
            has_dialogue = bool(dialogue)
            plan.music = MusicPlan(
                mood=music_str, duration=duration,
                ducking=has_dialogue,
                volume=self.MUSIC_DUCK_VOLUME if has_dialogue else 0.2
            )

        logger.info(f"AudioDirector: scene {scene_index} → "
                    f"{len(plan.voices)} voices, {len(plan.sfx)} sfx, "
                    f"ambience={'yes' if plan.ambience else 'no'}, "
                    f"music={'yes' if plan.music else 'no'}")

        return plan

    def analyze_storyboard(self, scenes: List[Dict[str, str]]) -> List[SceneAudioPlan]:
        """Analisa todas as cenas do storyboard."""
        return [self.analyze_scene(s, i) for i, s in enumerate(scenes)]

    def _plan_voices(self, dialogue: str, scene_duration: float, emotion: str) -> List[VoicePlan]:
        """Parseia dialogo e estima timings."""
        voices = []
        # Suporta formato "Personagem: fala" ou fala simples
        lines = [l.strip() for l in dialogue.split("\n") if l.strip()]

        current_offset = self.VOICE_START_OFFSET
        for line in lines:
            character = ""
            text = line
            if ":" in line:
                parts = line.split(":", 1)
                character = parts[0].strip()
                text = parts[1].strip()

            estimated_duration = max(1.0, len(text) / self.CHARS_PER_SECOND)
            # Nao ultrapassar duracao da cena
            end = min(current_offset + estimated_duration, scene_duration - 0.2)

            voices.append(VoicePlan(
                text=text,
                character=character,
                emotion=emotion,
                start=current_offset,
                end=end,
            ))
            current_offset = end + 0.3  # gap entre falas

        return voices

    def _plan_sfx(self, sfx_str: str, scene_duration: float) -> List[SfxPlan]:
        """Parseia SFX (separados por virgula) e distribui ao longo da cena."""
        items = [s.strip() for s in sfx_str.split(",") if s.strip()]
        sfx_list = []
        if not items:
            return sfx_list

        # Distribuir uniformemente
        interval = scene_duration / (len(items) + 1)
        for i, desc in enumerate(items):
            sfx_list.append(SfxPlan(
                description=desc,
                time=(i + 1) * interval,
                duration=min(1.5, interval),
            ))

        return sfx_list

    # ============================================================
    # INFERENCIA DE AUDIO A PARTIR DO PROMPT VISUAL
    # ============================================================

    # Mapeamento de palavras-chave → SFX (agrupados por conceito)
    _SFX_KEYWORDS = {
        # Veiculos
        "car": "car engine driving",
        "carro": "car engine driving",
        "driving": "car driving road",
        "dirigindo": "car driving road",
        "estrada": "car passing highway",
        "rodovia": "traffic passing fast",
        "highway": "traffic passing fast",
        "motorcycle": "motorcycle engine",
        "moto": "motorcycle engine",
        "helicopter": "helicopter flying",
        "truck": "truck driving",
        "caminhao": "truck driving",
        # Natureza
        "rain": "rain falling",
        "chuva": "rain falling",
        "lightning": "thunder crack",
        "raio": "thunder crack",
        "storm": "thunderstorm rain",
        "tempestade": "thunderstorm rain",
        "ocean": "ocean waves",
        "mar": "ocean waves",
        "wind": "strong wind",
        "vento": "strong wind",
        "water": "water stream",
        "agua": "water stream",
        "fire": "fire crackling",
        "fogo": "fire crackling",
        "snow": "footsteps snow",
        "neve": "footsteps snow",
        # Animais
        "horse": "horse galloping",
        "cavalo": "horse galloping",
        "dog": "dog barking",
        "cachorro": "dog barking",
        "wolf": "wolf howling",
        "lobo": "wolf howling",
        "bird": "birds singing",
        "passaro": "birds singing",
        "owl": "owl night",
        "coruja": "owl night",
        # Ambientes
        "forest": "forest birds leaves",
        "floresta": "forest birds leaves",
        "city": "city traffic crowd",
        "cidade": "city traffic crowd",
        # Combate
        "fight": "punch impact",
        "luta": "punch impact",
        "sword": "sword metal clash",
        "espada": "sword metal clash",
        "gun": "gunshot",
        "tiro": "gunshot",
        "explosion": "explosion boom",
        "explosao": "explosion boom",
        "armor": "metal armor clank",
        "armadura": "metal armor clank",
        # Acoes
        "running": "running footsteps",
        "correndo": "running footsteps",
        "walking": "footsteps walking",
        "andando": "footsteps walking",
        "footsteps": "footsteps",
        "passos": "footsteps",
        "door": "door opening creak",
        "porta": "door opening creak",
        "knock": "knocking door",
        # Sci-fi
        "space": "spaceship ambience",
        "espaco": "spaceship ambience",
        "robot": "robot servo motor",
        "robo": "robot servo motor",
        "laser": "laser shot",
    }

    # Mapeamento de palavras-chave → Ambiência
    _AMBIENCE_KEYWORDS = {
        "car": "car interior driving",
        "carro": "car interior driving",
        "highway": "highway traffic",
        "rodovia": "highway traffic",
        "estrada": "road driving wind",
        "rain": "rain ambient",
        "chuva": "rain ambient",
        "night": "night crickets",
        "noite": "night crickets",
        "forest": "forest ambience",
        "floresta": "forest ambience",
        "city": "city ambience traffic",
        "cidade": "city ambience traffic",
        "ocean": "ocean waves ambient",
        "mar": "ocean waves ambient",
        "beach": "beach waves",
        "praia": "beach waves",
        "cave": "cave dripping",
        "caverna": "cave dripping",
        "space": "spaceship interior",
        "espaco": "spaceship interior",
        "desert": "desert wind",
        "deserto": "desert wind",
        "snow": "winter wind cold",
        "neve": "winter wind cold",
        "indoor": "room tone quiet",
        "interior": "room tone quiet",
    }

    # Mapeamento de palavras-chave → Mood musical
    _MUSIC_KEYWORDS = {
        "action": "intense epic action",
        "acao": "intense epic action",
        "fight": "aggressive combat",
        "luta": "aggressive combat",
        "sad": "melancholic piano",
        "triste": "melancholic piano",
        "happy": "upbeat cheerful",
        "alegre": "upbeat cheerful",
        "love": "romantic soft",
        "amor": "romantic soft",
        "horror": "dark suspense horror",
        "terror": "dark suspense horror",
        "epic": "orchestral epic",
        "epico": "orchestral epic",
        "calm": "peaceful ambient",
        "calmo": "peaceful ambient",
        "chase": "fast paced tension",
        "perseguicao": "fast paced tension",
        "mystery": "mysterious subtle",
        "misterio": "mysterious subtle",
        "space": "sci-fi synthwave",
        "espaco": "sci-fi synthwave",
        "war": "military drums epic",
        "guerra": "military drums epic",
    }

    def _infer_sfx_from_prompt(self, prompt: str) -> str:
        """Infere efeitos sonoros a partir do prompt visual. Retorna todos os matches."""
        prompt_lower = prompt.lower()
        found = []
        seen = set()
        for keyword, sfx in self._SFX_KEYWORDS.items():
            if keyword in prompt_lower:
                first_item = sfx.split(",")[0].strip()
                if first_item and first_item not in seen:
                    found.append(first_item)
                    seen.add(first_item)
        return ", ".join(found) if found else ""

    def _infer_ambience_from_prompt(self, prompt: str) -> str:
        """Infere ambiencia a partir do prompt visual. Retorna queries separadas por |."""
        prompt_lower = prompt.lower()
        layers = []
        for keyword, ambience in self._AMBIENCE_KEYWORDS.items():
            if keyword in prompt_lower:
                layers.append(ambience)
        if not layers:
            return ""
        # Adicionar "room tone" como base se indoor
        if any(k in prompt_lower for k in ["indoor", "interior", "room", "house", "casa", "quarto"]):
            if "room tone" not in layers:
                layers.insert(0, "room tone")
        return "|".join(layers[:5])  # max 5 layers

    def _infer_music_from_prompt(self, prompt: str) -> str:
        """Infere mood musical a partir do prompt visual."""
        prompt_lower = prompt.lower()
        for keyword, mood in self._MUSIC_KEYWORDS.items():
            if keyword in prompt_lower:
                return mood
        return "cinematic ambient"  # fallback: sempre ter musica
