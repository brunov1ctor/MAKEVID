"""Logger - Sistema de logs compacto para MAKEVID."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from makevid.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "makevid.log"

# Max 500KB por arquivo, manter 2 backups (total max ~1.5MB)
MAX_LOG_SIZE = 500 * 1024
BACKUP_COUNT = 2


def setup_logging():
    """Configura logging global com rotacao automatica + console."""
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console: apenas INFO+ (sem DEBUG spam)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Silenciar libs externas e modulos internos ruidosos
    noisy = (
        "PIL", "urllib3", "httpx", "diffusers", "transformers",
        "torch", "huggingface_hub", "asyncio", "concurrent",
        "matplotlib", "numba", "sounddevice", "soundfile",
    )
    for lib in noisy:
        logging.getLogger(lib).setLevel(logging.ERROR)

    # Player: so WARNING+ (evita spam de frames)
    logging.getLogger("player").setLevel(logging.WARNING)
    logging.getLogger("preview").setLevel(logging.WARNING)

    logging.info("MAKEVID iniciado")


def get_log_content(max_lines: int = 200) -> str:
    if not LOG_FILE.exists():
        return "(nenhum log)"
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return "\n".join(lines)
    except Exception as e:
        return f"Erro: {e}"


def clear_logs():
    try:
        LOG_FILE.write_text("", encoding="utf-8")
    except Exception as _e:
        logger.debug(f"Suppressed: {_e}")


def log_generation(prompt: str, engine: str, duration: float, status: str, error: str = ""):
    """Loga geracao de clip."""
    logger = logging.getLogger("gen")
    if status == "done":
        logger.info(f"OK [{engine}] {duration:.1f}s | {prompt[:50]}")
    elif status == "error":
        logger.error(f"FALHA [{engine}] {prompt[:40]} | {error[:60]}")
    elif status == "generating":
        logger.info(f"INICIO [{engine}] {prompt[:50]}")


def log_clip_action(action: str, clip_id: str, details: str = ""):
    """Loga acao em clip (criar, duplicar, dividir, remover)."""
    logging.getLogger("clip").info(f"{action} {clip_id} {details}")


def log_export(format: str, path: str, duration: float):
    """Loga exportacao."""
    logging.getLogger("export").info(f"{format} {duration:.1f}s | {path}")


def log_error(context: str, error: str):
    """Loga erro generico para debug."""
    logging.getLogger("error").error(f"[{context}] {error[:100]}")
