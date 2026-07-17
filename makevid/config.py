"""Config - paths e defaults. Funciona tanto em dev quanto instalado."""

import sys
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
OUTPUTS_DIR = DATA_DIR / "outputs"
PROJECTS_DIR = DATA_DIR / "projects"
AUDIO_DIR = DATA_DIR / "audio"
AMBIENCE_REFS_DIR = DATA_DIR / "ambience_refs"

for d in [DATA_DIR, MODELS_DIR, OUTPUTS_DIR, PROJECTS_DIR, AUDIO_DIR, AMBIENCE_REFS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# HARDWARE
# ============================================================

def _detect_gpu():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


HAS_GPU = _detect_gpu()
DEVICE = "cuda" if HAS_GPU else "cpu"
MAX_VRAM_GB = 32

# ============================================================
# GENERATION DEFAULTS
# ============================================================

DEFAULT_STEPS = 30
DEFAULT_GUIDANCE = 5.0
DEFAULT_FPS = 16
DEFAULT_HEIGHT = 480
DEFAULT_WIDTH = 832

# ============================================================
# CPU PRESETS (maquinas sem GPU)
# ============================================================

CPU_MAX_FRAMES = 17
CPU_MAX_STEPS = 8
CPU_WIDTH = 320
CPU_HEIGHT = 192
CPU_FPS = 8
