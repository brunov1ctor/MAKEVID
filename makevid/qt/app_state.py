"""AppState — estado global do aplicativo."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppState:
    project:        object = None   # makevid.core.project.Project
    selected_clip:  object = None   # Clip
    selected_track: str    = ""
    engine:         str    = "Local (CPU)"
    active_panel:   str    = "generator"
