"""project_actions — limpar projeto."""

from makevid.config import PROJECTS_DIR


class ProjectActionsMixin:

    def _clear_project(self):
        self.project.clips.clear()
        self.project.track_items.clear()
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
