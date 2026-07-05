"""Ícones pixel art 8x8 para layers de track na timeline."""

LAYER_ICONS = {
    # 🎧 Gravar — fone de ouvido
    "mic": [
        "00111100",
        "01000010",
        "10000001",
        "10000001",
        "11000011",
        "11000011",
        "01000010",
        "00111100",
    ],
    # 🗣 TTS — balão de fala com ondas
    "tts": [
        "01111110",
        "10010001",
        "10110101",
        "10010001",
        "10000001",
        "01111110",
        "00001100",
        "00000110",
    ],
    # 📂 Importar — pasta aberta com seta
    "import": [
        "00000000",
        "01111000",
        "11111100",
        "10000100",
        "10011100",
        "10111110",
        "10011100",
        "11111100",
    ],
    # 🎵 Música — nota musical dupla
    "music": [
        "00111110",
        "00100010",
        "00100010",
        "00100010",
        "01110110",
        "11110110",
        "11110000",
        "01110000",
    ],
    # 🔊 SFX — alto-falante com ondas
    "sfx": [
        "00001100",
        "00011100",
        "01111100",
        "01111100",
        "01111100",
        "00011100",
        "00001100",
        "00000000",
    ],
    # 🎤 Voice — microfone de estúdio
    "voice": [
        "00111100",
        "01111110",
        "01111110",
        "01111110",
        "00111100",
        "00011000",
        "00111100",
        "00011000",
    ],
    # ⏺ Rec — círculo de gravação
    "rec": [
        "00111100",
        "01111110",
        "11111111",
        "11111111",
        "11111111",
        "01111110",
        "00111100",
        "00000000",
    ],
    "default": [
        "00111100",
        "01000010",
        "10000001",
        "10000001",
        "10000001",
        "01000010",
        "00111100",
        "00000000",
    ],
}

LAYER_ICON_COLORS = {
    "mic":     "#ff6688",
    "tts":     "#44ddff",
    "import":  "#88ffcc",
    "music":   "#cc88ff",
    "sfx":     "#ffaa44",
    "voice":   "#44aaff",
    "rec":     "#ff4444",
    "default": "#aaaaff",
}

_SOURCE_TO_ICON = {
    "rec":      "mic",
    "tts":      "tts",
    "import":   "import",
    "voices":   "voice",
    "ambience": "sfx",
    "music":    "music",
}
_TRACK_TO_ICON = {
    "voice": "voice",
    "sfx":   "sfx",
    "music": "music",
    "audio": "import",
}

def infer_icon_key(name: str, track: str = "", source_type: str = "") -> str:
    if source_type in _SOURCE_TO_ICON:
        return _SOURCE_TO_ICON[source_type]
    if track in _TRACK_TO_ICON:
        return _TRACK_TO_ICON[track]
    n = name.lower()
    if any(k in n for k in ("tts", "fala", "texto", "speech")):
        return "tts"
    if any(k in n for k in ("music", "musica", "score", "trilha")):
        return "music"
    if any(k in n for k in ("sfx", "foley", "efeito", "sound")):
        return "sfx"
    if any(k in n for k in ("voz", "voice", "narr")):
        return "voice"
    if any(k in n for k in ("import", "arquivo", "file")):
        return "import"
    if any(k in n for k in ("mic", "grav", "rec")):
        return "mic"
    return "default"
