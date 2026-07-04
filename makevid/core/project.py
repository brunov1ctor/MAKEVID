"""Projeto - Timeline com clips, World Bible e Personagens."""

import json
import uuid
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class WorldBible:
    style: str = "cinematic"
    lighting: str = "natural"
    color_palette: str = "neutral"
    weather: str = "clear"
    time_of_day: str = "day"
    mood: str = ""
    location: str = ""
    camera_style: str = "cinematic"
    # Storyboard scenes (campos: visual, camera, dialogue, emotion, ambience, sfx, music_mood, duration)
    scenes: List[Dict[str, str]] = field(default_factory=list)

    def to_prompt(self) -> str:
        parts = [p for p in [self.style, f"{self.lighting} lighting", self.weather,
                             self.time_of_day, self.mood, self.camera_style] if p and p != "clear"]
        return ", ".join(parts)

    def get_scene_at(self, time_pos: float, total_dur: float) -> Optional[Dict[str, str]]:
        """Retorna a cena do storyboard que corresponde a posicao temporal."""
        if not self.scenes:
            return None
        # Distribuir cenas proporcionalmente ou usar duracao de cada cena
        current = 0.0
        for scene in self.scenes:
            scene_dur = float(scene.get("duration", 5.0))
            if current <= time_pos < current + scene_dur:
                return scene
            current += scene_dur
        return self.scenes[-1] if self.scenes else None

    def get_scene_for_clip_position(self, clip_position: int) -> Optional[Dict[str, str]]:
        """Retorna cena pelo indice do clip."""
        if not self.scenes:
            return None
        if clip_position < len(self.scenes):
            return self.scenes[clip_position]
        return None

    def total_storyboard_duration(self) -> float:
        """Duracao total do storyboard."""
        return sum(float(s.get("duration", 5.0)) for s in self.scenes)


@dataclass
class Character:
    id: str = ""
    name: str = ""
    # Tipo e resumo
    char_type: str = ""  # humano, humanoide, criatura, robo, alienigena, etc
    summary: str = ""  # descricao curta
    # Demografico
    demographic: str = ""  # perfil demografico base
    age: str = ""  # idade ou idade aparente
    height_build: str = ""  # altura | constituicao
    proportion_style: str = ""  # realista 7-7.5 cabecas, heroico, chibi...
    # Rosto e cabeca
    face_design: str = ""  # formato, olhos, nariz, mandibula, expressao
    hair_head: str = ""  # cabelo, chifres, orelhas, capacete, etc
    # Pele / superficie
    skin_surface: str = ""  # tonalidade, cicatrizes, tatuagens, escamas...
    # Traje
    costume: str = ""  # traje/armadura completo
    # Detalhes assimetricos
    asymmetric_details: str = ""  # lado exato de cada detalhe
    # Acessorios
    accessories: str = ""  # joias, armas, bolsas, asas, cauda...
    # Continuidade
    continuity_locks: str = ""  # recursos inegociaveis
    # Visual style
    visual_style: str = ""  # UE5 MetaHuman, anime, fantasia sombria...
    # Voz
    voice_id: str = ""  # ID da voz TTS (ex: pt-BR-AntonioNeural)
    voice_sample: str = ""  # path de amostra de voz gravada/importada
    voice_profile: Dict[str, any] = field(default_factory=dict)  # VoiceProfile serializado
    # Compat legado
    description: str = ""
    traits: List[str] = field(default_factory=list)
    clothing_default: Dict[str, str] = field(default_factory=dict)
    reference_image: str = ""

    def to_prompt(self) -> str:
        """Gera prompt completo de character sheet no estilo producao."""
        parts = []
        if self.summary:
            parts.append(self.summary)
        if self.demographic:
            parts.append(self.demographic)
        if self.age:
            parts.append(f"age {self.age}")
        if self.height_build:
            parts.append(self.height_build)
        if self.face_design:
            parts.append(self.face_design)
        if self.hair_head:
            parts.append(self.hair_head)
        if self.skin_surface:
            parts.append(self.skin_surface)
        if self.costume:
            parts.append(self.costume)
        if self.asymmetric_details:
            parts.append(self.asymmetric_details)
        if self.accessories:
            parts.append(self.accessories)
        # Fallback legado
        if not parts and self.description:
            parts.append(self.description)
        if not parts and self.traits:
            parts.append(", ".join(self.traits))
        return ", ".join(parts)

    def to_sheet_prompt(self) -> str:
        """Gera ficha do personagem com todos os campos (label: valor)."""
        fields = [
            ("NOME", self.name),
            ("TIPO", self.char_type),
            ("RESUMO", self.summary),
            ("PERFIL DEMOGRAFICO", self.demographic),
            ("IDADE", self.age),
            ("ALTURA E CONSTITUICAO", self.height_build),
            ("PROPORCAO", self.proportion_style),
            ("ROSTO E CABECA", self.face_design),
            ("CABELO / CABECA", self.hair_head),
            ("PELE / SUPERFICIE", self.skin_surface),
            ("TRAJE / ARMADURA", self.costume),
            ("DETALHES ASSIMETRICOS", self.asymmetric_details),
            ("ACESSORIOS", self.accessories),
            ("CONTINUIDADE", self.continuity_locks),
            ("ESTILO VISUAL", self.visual_style),
        ]
        lines = []
        for label, val in fields:
            lines.append(f"{label}: {val if val else ''}")
        return "\n".join(lines)


@dataclass
class Clip:
    """Um clip de video na timeline."""
    id: str = ""
    prompt: str = ""
    duration: float = 5.0
    fps: int = 16
    seed: int = 0
    video_path: str = ""  # path relativo ao projeto
    thumbnail_path: str = ""
    image_ref_path: str = ""  # se foi gerado via I2V
    position: int = 0  # ordem na timeline (0, 1, 2...)
    status: str = "empty"  # empty, generating, done, error

    @classmethod
    def create(cls, prompt: str = "", position: int = 0) -> "Clip":
        return cls(id=str(uuid.uuid4())[:8], prompt=prompt, position=position)


# Tipos de track validos
TRACK_TYPES = ("fx", "voice", "sfx", "music", "audio")


@dataclass
class TrackItem:
    """Item na track - posicao e duracao independentes.
    track: fx | voice | sfx | music | audio
    """
    id: str = ""
    name: str = ""
    track: str = ""  # fx, voice, sfx, music, audio
    start_time: float = 0.0  # posicao em segundos na timeline
    duration: float = 2.0  # duracao em segundos
    file_path: str = ""  # path do arquivo (WAV para audio)
    clip_index: int = -1  # indice do clip/video que gerou este item (-1 = nao associado)
    params: Dict[str, str] = field(default_factory=dict)  # parametros extras (cor, intensidade, volume, emotion, etc)
    # Keyframes de volume: lista de {"time": float (segundos relativos ao item), "value": float (0.0-2.0)}
    volume_keyframes: List[Dict[str, float]] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, track: str, start_time: float, duration: float = 2.0, file_path: str = "") -> "TrackItem":
        return cls(id=str(uuid.uuid4())[:8], name=name, track=track,
                   start_time=start_time, duration=duration, file_path=file_path)


@dataclass
class Project:
    id: str = ""
    name: str = ""
    created_at: float = field(default_factory=time.time)
    world: WorldBible = field(default_factory=WorldBible)
    characters: List[Character] = field(default_factory=list)
    clips: List[Clip] = field(default_factory=list)
    track_items: List[TrackItem] = field(default_factory=list)
    track_volumes: Dict[str, float] = field(default_factory=lambda: {
        "voice": 1.0, "sfx": 0.8, "music": 0.3, "audio": 0.7
    })
    output_fps: int = 16
    output_width: int = 832
    output_height: int = 480
    export_format: str = "MP4 (H.264)"
    export_tracks: Dict[str, bool] = field(default_factory=lambda: {
        "video": True,
        "voice": True,
        "sfx": True,
        "music": True,
        "audio": True,
    })

    def add_clip(self, prompt: str = "", position: Optional[int] = None) -> Clip:
        pos = position if position is not None else len(self.clips)
        clip = Clip.create(prompt=prompt, position=pos)
        self.clips.append(clip)
        self._reindex()
        return clip

    def remove_clip(self, clip_id: str):
        self.clips = [c for c in self.clips if c.id != clip_id]
        self._reindex()

    def move_clip(self, clip_id: str, new_position: int):
        clip = next((c for c in self.clips if c.id == clip_id), None)
        if not clip:
            return
        self.clips.remove(clip)
        self.clips.insert(new_position, clip)
        self._reindex()

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        return next((c for c in self.clips if c.id == clip_id), None)

    def total_duration(self) -> float:
        """Duracao total = max entre fim dos clips e fim dos track items."""
        video_dur = sum(c.duration for c in self.clips)
        track_end = max((i.start_time + i.duration for i in self.track_items), default=0)
        return max(video_dur, track_end)

    def add_track_item(self, name: str, track: str, start_time: float, duration: float = 2.0, file_path: str = "", params: Dict[str, str] = None, clip_index: int = -1) -> TrackItem:
        item = TrackItem.create(name=name, track=track, start_time=start_time, duration=duration, file_path=file_path)
        item.clip_index = clip_index
        if params:
            item.params = params
        self.track_items.append(item)
        return item

    def remove_track_item(self, item_id: str):
        self.track_items = [i for i in self.track_items if i.id != item_id]

    def get_track_items(self, track: str) -> List[TrackItem]:
        return [i for i in self.track_items if i.track == track]

    def _reindex(self):
        for i, clip in enumerate(self.clips):
            clip.position = i

    def save(self, base_dir: Path):
        path = base_dir / f"{self.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Project":
        data = json.loads(path.read_text(encoding="utf-8"))
        proj = cls(
            id=data["id"],
            name=data["name"],
            created_at=data.get("created_at", 0.0),
            world=WorldBible(**data.get("world", {})),
            characters=[Character(**c) for c in data.get("characters", [])],
            clips=[Clip(**c) for c in data.get("clips", [])],
            track_items=[TrackItem(**i) for i in data.get("track_items", [])],
            track_volumes=data.get("track_volumes", {"voice": 1.0, "sfx": 0.8, "music": 0.3, "audio": 0.7}),
            output_fps=data.get("output_fps", 16),
            output_width=data.get("output_width", 832),
            output_height=data.get("output_height", 480),
            export_format=data.get("export_format", "MP4 (H.264)"),
            export_tracks=data.get("export_tracks", {
                "video": True,
                "voice": True,
                "sfx": True,
                "music": True,
                "audio": True,
            }),
        )
        return proj

    @classmethod
    def create(cls, name: str) -> "Project":
        return cls(id=str(uuid.uuid4())[:8], name=name)
