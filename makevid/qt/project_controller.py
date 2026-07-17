"""ProjectController — troca, criação e carregamento de projetos."""

import logging
from makevid.config import PROJECTS_DIR
from makevid.core.project import Project

_log = logging.getLogger("clip")


def load_last_project() -> Project:
    files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        try:
            return Project.load(f)
        except Exception as e:
            _log.warning(f"Projeto {f.name} ignorado (corrompido?): {e}")
    return Project.create("")  # projeto em memória, sem salvar em disco


class ProjectController:
    """Coordena o projeto ativo e notifica a janela via project_changed."""

    def __init__(self, window):
        self._window = window

    def open(self, proj: Project):
        w = self._window
        w.project = proj
        w.state.project = proj
        w.project_changed.emit(proj)
        w.timeline.redraw()
        if hasattr(w, "_project_badge"):
            w._project_badge.set_text(proj.name)
