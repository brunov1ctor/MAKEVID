"""projects_view — painel de projetos embutido no preview."""

from makevid.qt.panels.projects_panel import ProjectsPanel


class ProjectsViewMixin:
    """Mixin para PreviewWidget: exibe ProjectsPanel no lugar do display."""

    def show_projects_panel(self):
        if self.player.is_playing:
            self.player.stop()

        self._display.hide()
        self._progress_container.hide()
        self._info.hide()

        if self._projects_panel is None:
            self._projects_panel = ProjectsPanel(self.project, parent=self)
            self._projects_panel.hide()
            self._projects_panel.closed.connect(self._close_projects_panel)
            self._projects_panel.project_opened.connect(self.window()._on_project_opened)
            self.layout().addWidget(self._projects_panel, stretch=1)

        self._projects_panel.set_active(self.project.id)
        self._projects_panel.show()

    def _close_projects_panel(self):
        if self._projects_panel is not None:
            self._projects_panel.hide()
        self._display.show()
        self._info.show()
        self._show_play_button()
