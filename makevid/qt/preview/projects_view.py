"""projects_view — painel de projetos embutido no preview."""

from makevid.qt.panels.projects_panel import ProjectsPanel


class ProjectsViewMixin:
    """Mixin para PreviewWidget: exibe ProjectsPanel no lugar do display."""

    def show_projects_panel(self):
        if self.player.is_playing:
            self.player.stop()

        if self._projects_panel is None:
            self._projects_panel = ProjectsPanel(self.project, parent=self._stack)
            self._projects_panel.closed.connect(self._close_projects_panel)
            self._projects_panel.project_opened.connect(self.window()._on_project_opened)
            self._stack.addWidget(self._projects_panel)

        self._projects_panel.set_active(self.project.id)
        self._stack.setCurrentWidget(self._projects_panel)

    def _close_projects_panel(self):
        self._stack.setCurrentWidget(self._display_page)
        self._show_play_button()
