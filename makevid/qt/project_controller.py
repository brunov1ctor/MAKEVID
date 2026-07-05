"""ProjectController — troca, criação e carregamento de projetos."""

from makevid.config import PROJECTS_DIR
from makevid.core.project import Project


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
        w.project = proj
        w.state.project = proj
        w.project_changed.emit(proj)
        w.timeline.redraw()
        if hasattr(w, "_project_badge"):
            w._project_badge.set_text(proj.name)
