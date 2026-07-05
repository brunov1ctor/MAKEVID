"""Logger - Sistema de logs compacto para MAKEVID."""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

from makevid.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "makevid.log"

# Max 500KB por arquivo, manter 2 backups (total max ~1.5MB)
MAX_LOG_SIZE = 500 * 1024
BACKUP_COUNT = 2


def _resolve_log_level() -> int:
    """Resolve nivel de log a partir de variaveis de ambiente.

    Prioridade:
    1) MAKEVID_LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
    2) MAKEVID_DEBUG=1/true/on/yes -> DEBUG
    3) padrao -> INFO
    """
    level_name = os.getenv("MAKEVID_LOG_LEVEL", "").strip().upper()
    if level_name:
        return getattr(logging, level_name, logging.INFO)

    debug_flag = os.getenv("MAKEVID_DEBUG", "").strip().lower()
    if debug_flag in {"1", "true", "on", "yes"}:
        return logging.DEBUG

    return logging.INFO


def setup_logging():
    """Configura logging global com rotacao automatica (arquivo apenas)."""
    log_level = _resolve_log_level()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(file_handler)

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
    # Timeline: INFO em producao; DEBUG quando modo debug esta ativo.
    timeline_level = logging.DEBUG if log_level <= logging.DEBUG else logging.INFO
    logging.getLogger("timeline").setLevel(timeline_level)

    # Glow: so vai pro arquivo, nao pro console
    glow_log = logging.getLogger("glow")
    glow_log.propagate = False
    glow_log.handlers.clear()
    glow_log.setLevel(log_level)
    glow_log.addHandler(file_handler)

    logging.info(f"MAKEVID iniciado | log_level={logging.getLevelName(log_level)}")


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
    """Fecha handlers, limpa todos os arquivos de log e reabre."""
    root = logging.getLogger()
    glow = logging.getLogger("glow")

    # fecha todos os handlers que usam arquivos de log
    for logger in (root, glow):
        for h in list(logger.handlers):
            if hasattr(h, 'baseFilename') and 'makevid' in h.baseFilename:
                h.close()
                logger.removeHandler(h)

    # apaga todos os arquivos de backup e limpa o principal
    for f in LOG_DIR.glob("makevid.log*"):
        try:
            f.unlink()
        except Exception:
            pass

    # reconfigura o logging do zero
    setup_logging()


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
