"""Layout principal — splitters, preview, timeline e left stack."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt

from makevid.qt.widgets import GlassPanel
from makevid.qt.preview.glow_layer import PreviewGlowPanel

from makevid.qt.timeline.timeline_widget import TimelineWidget
from makevid.qt.preview.preview_widget import PreviewWidget
from makevid.qt.panels.panel_manager import PanelManager
from makevid.qt.panels.style import StylePanel


def build_layout(window, main_layout):
    project = window.project

    # ── Splitters ─────────────────────────────────────────────────────────────
    window._v_splitter = QSplitter(Qt.Vertical)
    window._v_splitter.setHandleWidth(10)
    window._v_splitter.setChildrenCollapsible(True)
    window._v_splitter.setStyleSheet("QSplitter { background: transparent; } QSplitter::handle { background: transparent; }")

    window._h_splitter = QSplitter(Qt.Horizontal)
    window._h_splitter.setHandleWidth(10)
    window._h_splitter.setChildrenCollapsible(True)
    window._h_splitter.setStyleSheet("QSplitter { background: transparent; } QSplitter::handle { background: transparent; }")

    # ── Left stack ────────────────────────────────────────────────────────────
    window._left_stack = QStackedWidget()
    window._left_stack.setMinimumWidth(0)
    window._left_stack.setMinimumHeight(0)
    window._left_stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
    window._left_stack.setStyleSheet("background: transparent;")
    window._left_stack.setAttribute(Qt.WA_TranslucentBackground)

    # ── Panel Manager ─────────────────────────────────────────────────────────
    window.panels = PanelManager(window._left_stack, parent=window)
    _register_panels(window)

    # ── Widgets principais ────────────────────────────────────────────────────
    window.timeline = TimelineWidget(project)
    window.timeline.setMinimumHeight(100)
    window.preview  = PreviewWidget(project, window.timeline)

    # ── GlassPanel wrappers ───────────────────────────────────────────────────
    left_shell = GlassPanel(radius=20, shadow=False)
    left_shell.setAttribute(Qt.WA_TranslucentBackground)
    window._left_layout = QVBoxLayout(left_shell)
    window._left_layout.setContentsMargins(1, 1, 1, 1)
    window._left_layout.setSpacing(0)
    window._left_layout.addWidget(window._left_stack)
    # Recorta o conteúdo do stack nas quinas arredondadas do shell
    window._left_stack.setStyleSheet(
        "QStackedWidget { background: transparent; border-radius: 20px; }"
    )

    preview_shell = PreviewGlowPanel(radius=20, shadow=False)
    window._preview_layout = QVBoxLayout(preview_shell)
    window._preview_layout.setContentsMargins(0, 0, 0, 0)
    window._preview_layout.addWidget(window.preview)
    window._preview_shell = preview_shell
    window.preview._glow_layer = preview_shell
    preview_shell.set_preview(window.preview)
    window.preview._ambient_bg = None

    timeline_shell = GlassPanel(radius=20, shadow=False)
    timeline_shell.setAttribute(Qt.WA_TranslucentBackground)
    window._timeline_layout = QVBoxLayout(timeline_shell)
    window._timeline_layout.setContentsMargins(1, 1, 1, 1)
    window._timeline_layout.addWidget(window.timeline)

    # ── Montar splitters ──────────────────────────────────────────────────────
    window._h_splitter.addWidget(left_shell)
    window._h_splitter.addWidget(preview_shell)

    window._v_splitter.addWidget(window._h_splitter)
    window._v_splitter.addWidget(timeline_shell)

    window._v_splitter.setSizes([560, 260])
    window._h_splitter.setSizes([300, 900])
    window._h_splitter.setCollapsible(0, True)
    window._h_splitter.setCollapsible(1, True)
    window._v_splitter.setCollapsible(0, True)
    window._v_splitter.setCollapsible(1, True)
    window._h_splitter.setStretchFactor(0, 0)
    window._h_splitter.setStretchFactor(1, 1)

    main_layout.addWidget(window._v_splitter)

    # ── Style panel ───────────────────────────────────────────────────────────
    window.style_panel = StylePanel(project, parent=window)
    window.style_panel.hide()

    # ── Inicializa com generator (eager — é o painel padrão) ──────────────────
    window.panels.show("generator")


def _register_panels(window):
    """Registra factories — painéis são criados apenas no primeiro acesso."""
    project = window.project

    from makevid.qt.panels.generator_panel import GeneratorPanel
    from makevid.qt.panels.mixer_panel import MixerPanel
    from makevid.qt.panels.fx_panel import FxPanel
    from makevid.qt.panels.track_editor_panel import TrackEditorPanel
    from makevid.qt.panels.export_panel import ExportPanel
    from makevid.qt.panels.recorder_panel import RecorderPanel, TTSPanel
    from makevid.qt.panels.browser_panel import VideoBrowserPanel, AudioBrowserPanel
    from makevid.qt.panels.track_menu_panel import TrackMenuPanel
    from makevid.qt.panels.inpaint_panel import InpaintPanel

    pm = window.panels

    pm.register("generator",     lambda: GeneratorPanel(project))
    pm.register("mixer",         lambda: MixerPanel())
    pm.register("fx",            lambda: FxPanel())
    pm.register("track_editor",  lambda: TrackEditorPanel())
    pm.register("export",        lambda: ExportPanel(project))
    pm.register("recorder",      lambda: RecorderPanel())
    pm.register("tts",           lambda: TTSPanel())
    pm.register("video_browser", lambda: VideoBrowserPanel(project))
    pm.register("audio_browser", lambda: AudioBrowserPanel(project, window.timeline))
    pm.register("track_menu",    lambda: TrackMenuPanel())
    pm.register("inpaint",       lambda: InpaintPanel())
