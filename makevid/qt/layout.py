"""Layout principal — splitters, preview, timeline e left stack."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from makevid.qt.widgets import GlassPanel
from makevid.qt.preview.glow_layer import PreviewGlowPanel, GlowOverlay
from makevid.qt.timeline.timeline_widget import TimelineWidget
from makevid.qt.preview.preview_widget import PreviewWidget
from makevid.qt.panels.generator_panel import GeneratorPanel
from makevid.qt.panels.mixer_panel import MixerPanel
from makevid.qt.panels.fx_panel import FxPanel
from makevid.qt.panels.track_editor_panel import TrackEditorPanel
from makevid.qt.panels.export_panel import ExportPanel
from makevid.qt.panels.style import StylePanel
from makevid.qt.panels.recorder_panel import RecorderPanel, TTSPanel
from makevid.qt.panels.browser_panel import VideoBrowserPanel, AudioBrowserPanel
from makevid.qt.panels.track_menu_panel import TrackMenuPanel
from makevid.qt.panels.inpaint_panel import InpaintPanel


def build_layout(window, main_layout):
    project = window.project

    # ── Splitters ─────────────────────────────────────────────────────────────
    window._v_splitter = QSplitter(Qt.Vertical)
    window._v_splitter.setHandleWidth(10)
    window._v_splitter.setChildrenCollapsible(False)
    window._v_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

    window._h_splitter = QSplitter(Qt.Horizontal)
    window._h_splitter.setHandleWidth(10)
    window._h_splitter.setChildrenCollapsible(False)
    window._h_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

    # ── Left stack ────────────────────────────────────────────────────────────
    window._left_stack = QStackedWidget()
    window._left_stack.setMinimumWidth(260)
    window._left_stack.setMinimumHeight(0)
    window._left_stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
    window._left_stack.setStyleSheet("background: transparent;")

    # ── Widgets principais ────────────────────────────────────────────────────
    window.timeline = TimelineWidget(project)
    window.timeline.setMinimumHeight(100)
    window.preview  = PreviewWidget(project, window.timeline)

    # ── Paineis do left stack ─────────────────────────────────────────────────
    _build_panels(window)

    # ── GlassPanel wrappers ───────────────────────────────────────────────────
    left_shell = GlassPanel(radius=20, shadow=True, shadow_radius=30, shadow_dy=8)
    window._left_layout = QVBoxLayout(left_shell)
    window._left_layout.setContentsMargins(0, 0, 0, 0)
    window._left_layout.setSpacing(0)
    window._left_layout.addWidget(window._left_stack)

    preview_shell = PreviewGlowPanel(radius=20, shadow=True, shadow_radius=36, shadow_dy=10)
    window._preview_layout = QVBoxLayout(preview_shell)
    window._preview_layout.setContentsMargins(0, 0, 0, 0)
    window._preview_layout.addWidget(window.preview)
    window._preview_shell = preview_shell
    window.preview._glow_layer = preview_shell
    window._preview_halo = None

    timeline_shell = GlassPanel(radius=20, shadow=True, shadow_radius=28, shadow_dy=6)
    window._timeline_layout = QVBoxLayout(timeline_shell)
    window._timeline_layout.setContentsMargins(0, 0, 0, 0)
    window._timeline_layout.addWidget(window.timeline)

    # ── Montar splitters ──────────────────────────────────────────────────────
    window._h_splitter.addWidget(left_shell)
    window._h_splitter.addWidget(preview_shell)

    window._v_splitter.addWidget(window._h_splitter)
    window._v_splitter.addWidget(timeline_shell)

    window._v_splitter.setSizes([560, 260])
    window._h_splitter.setSizes([300, 900])

    main_layout.addWidget(window._v_splitter)

    # ── GlowOverlay — filho do centralWidget, atrás de tudo ──────────────────
    def _install_overlay():
        central = window.centralWidget()
        overlay = GlowOverlay(central)
        overlay.track(preview_shell)
        preview_shell._halo = overlay
        window._preview_halo = overlay

        # atualiza quando splitter mover ou janela redimensionar
        def _update():
            overlay.track(preview_shell)

        window._h_splitter.splitterMoved.connect(lambda *_: _update())
        window._v_splitter.splitterMoved.connect(lambda *_: _update())
        window._glow_update = _update  # guarda ref para resizeEvent

    QTimer.singleShot(0, _install_overlay)

    # ── Style panel ───────────────────────────────────────────────────────────
    window.style_panel = StylePanel(project, parent=window)
    window.style_panel.hide()


def _build_panels(window):
    project = window.project

    window.generator     = GeneratorPanel(project)
    window.mixer         = MixerPanel()
    window.fx_editor     = FxPanel()
    window.track_editor  = TrackEditorPanel()
    window.export_panel  = ExportPanel(project)
    window.recorder      = RecorderPanel()
    window.tts_panel     = TTSPanel()
    window.video_browser = VideoBrowserPanel(project)
    window.track_menu    = TrackMenuPanel()
    window.inpaint_panel = InpaintPanel()
    window.audio_browser = AudioBrowserPanel(project, window.timeline)
    for panel in (
        window.generator, window.mixer, window.fx_editor, window.track_editor,
        window.export_panel, window.recorder, window.tts_panel, window.video_browser,
        window.track_menu, window.inpaint_panel, window.audio_browser,
    ):
        window._left_stack.addWidget(panel)
    window._left_stack.setCurrentWidget(window.generator)
