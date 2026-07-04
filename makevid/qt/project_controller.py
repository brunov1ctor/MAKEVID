"""ProjectController — troca, criação e carregamento de projetos."""

import logging
from makevid.config import PROJECTS_DIR
from makevid.core.project import Project

_log = logging.getLogger("gen")


def load_last_project() -> Project:
    files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        try:
            return Project.load(f)
        except Exception:
            pass
    return Project.create("")  # projeto em memória, sem salvar em disco


class ProjectController:
    """Coordena o projeto ativo e notifica a janela via project_changed."""

    def __init__(self, window):
        self._window = window

    def open(self, proj: Project):
        w = self._window
        _log.debug(f"[ctrl.open] id={proj.id} track_items={len(proj.track_items)} sel_track={w.timeline._selected_track_item_id}")
        w.project = proj
        w.state.project = proj
        w.project_changed.emit(proj)
        w.timeline.redraw()
        if hasattr(w, "_project_badge"):
            _log.debug(f"[ctrl.open] badge='{proj.name}' id={proj.id}")
            w._project_badge.set_text(proj.name)
