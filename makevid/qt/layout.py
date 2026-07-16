"""Layout principal — splitters, preview, timeline e left stack."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt

from makevid.qt.widgets import GlassPanel
from makevid.qt.preview.glow_layer import PreviewGlowPanel
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

    # ── Widgets principais ────────────────────────────────────────────────────
    window.timeline = TimelineWidget(project)
    window.timeline.setMinimumHeight(100)
    window.preview  = PreviewWidget(project, window.timeline)

    # ── Paineis do left stack ─────────────────────────────────────────────────
    _build_panels(window)

    # ── GlassPanel wrappers ───────────────────────────────────────────────────
    left_shell = GlassPanel(radius=20, shadow=False)
    left_shell.setAttribute(Qt.WA_TranslucentBackground)
    window._left_layout = QVBoxLayout(left_shell)
    window._left_layout.setContentsMargins(0, 0, 0, 0)
    window._left_layout.setSpacing(0)
    window._left_layout.addWidget(window._left_stack)

    preview_shell = PreviewGlowPanel(radius=20, shadow=False)
    window._preview_layout = QVBoxLayout(preview_shell)
    window._preview_layout.setContentsMargins(0, 0, 0, 0)
    window._preview_layout.addWidget(window.preview)
    window._preview_shell = preview_shell
    window.preview._glow_layer = preview_shell
    preview_shell.set_preview(window.preview)
    # glow global no AmbientBackground
    window.preview._ambient_bg = None  # será setado pelo app.py via set_ambient_bg

    timeline_shell = GlassPanel(radius=20, shadow=False)
    timeline_shell.setAttribute(Qt.WA_TranslucentBackground)
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

    # Paineis que gerenciam seu proprio visual — nao aplicar _make_transparent
    _opaque_panels = {window.track_editor, window.mixer, window.fx_editor}

    panels = (
        window.generator, window.mixer, window.fx_editor, window.track_editor,
        window.export_panel, window.recorder, window.tts_panel, window.video_browser,
        window.track_menu, window.inpaint_panel, window.audio_browser,
    )
    for panel in panels:
        if panel not in _opaque_panels:
            _make_transparent(panel)
        window._left_stack.addWidget(panel)
    window._left_stack.setCurrentWidget(window.generator)


def _make_transparent(widget):
    """Torna o widget e todos os filhos QFrame/QWidget/QScrollArea transparentes."""
    from PySide6.QtWidgets import QScrollArea, QFrame
    widget.setAttribute(Qt.WA_TranslucentBackground)
    widget.setAutoFillBackground(False)
    for child in widget.findChildren(QScrollArea):
        child.setStyleSheet("background: transparent; border: none;")
        child.viewport().setStyleSheet("background: transparent;")
        child.viewport().setAttribute(Qt.WA_TranslucentBackground)
        if child.widget():
            child.widget().setStyleSheet("background: transparent;")
            child.widget().setAttribute(Qt.WA_TranslucentBackground)
    for child in widget.findChildren(QFrame):
        child.setAttribute(Qt.WA_TranslucentBackground)
        child.setAttribute(Qt.WA_StyledBackground, False)
        child.setAutoFillBackground(False)
        ss = child.styleSheet()
        if ss and 'background' in ss:
            import re
            ss = re.sub(r'background(-color)?\s*:[^;]+;?', 'background: transparent;', ss)
            child.setStyleSheet(ss)
    for child in widget.findChildren(QWidget):
        if type(child).__name__ not in ('QScrollBar', 'QSlider', 'QProgressBar',
                                        'QLineEdit', 'QTextEdit', 'QPlainTextEdit',
                                        'QComboBox', 'QCheckBox', 'QRadioButton',
                                        'QPushButton', 'QLabel'):
            child.setAttribute(Qt.WA_TranslucentBackground)
            child.setAutoFillBackground(False)
