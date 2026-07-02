"""makevid.qt.actions — pacote de mixins de ações."""

from PySide6.QtCore import Signal

from makevid.qt.actions.generation_actions import GenerationActionsMixin
from makevid.qt.actions.audio_actions import AudioActionsMixin
from makevid.qt.actions.timeline_actions import TimelineActionsMixin
from makevid.qt.actions.export_actions import ExportActionsMixin
from makevid.qt.actions.project_actions import ProjectActionsMixin


class ActionsMixin(
    GenerationActionsMixin,
    AudioActionsMixin,
    TimelineActionsMixin,
    ExportActionsMixin,
    ProjectActionsMixin,
):
    """Agrega todos os mixins de ação para MakeVidWindow."""

    project_changed = Signal(object)
