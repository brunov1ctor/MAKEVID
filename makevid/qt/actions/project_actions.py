"""project_actions — limpar projeto, abrir logs."""

import logging
from makevid.config import PROJECTS_DIR
from makevid.core.logger import log_clip_action, clear_logs

_log = logging.getLogger("clip")


class ProjectActionsMixin:

    def _clear_project(self):
        n_clips = len(self.project.clips)
        n_items = len(self.project.track_items)
        self.project.clips.clear()
        self.project.track_items.clear()
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        _log.info(f"Projeto limpo: {n_clips} clips e {n_items} track items removidos")

    def _open_logs(self):
        """Delega para o dialog completo de logs (com filtros e auto-refresh)."""
        from makevid.qt.actions.export_actions import ExportActionsMixin
        ExportActionsMixin._open_logs(self)

    def _clear_logs(self):
        clear_logs()
