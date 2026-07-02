"""Hot reload — apenas para desenvolvimento (F5)."""

import importlib
import sys

from PySide6.QtCore import QTimer

from makevid.qt.preview.preview_widget import PreviewWidget
from makevid.qt.timeline.timeline_widget import TimelineWidget


_RELOAD_PREFIXES = [
    "makevid.qt.panels.style.",
    "makevid.qt.panels.",
    "makevid.qt.preview.",
    "makevid.qt.timeline.",
]


def hot_reload(window):
    style_visible = window.style_panel.isVisible()
    style_tab     = window.style_panel._style_stack.currentIndex() if style_visible else 0

    mods = [m for m in list(sys.modules) if any(m.startswith(p) for p in _RELOAD_PREFIXES)]
    mods.sort(key=lambda x: -x.count("."))
    for m in mods:
        if m in sys.modules:
            try:
                importlib.reload(sys.modules[m])
            except Exception as e:
                print(f"[hot_reload] {m}: {e}")

    # Rebuild style panel
    window.style_panel.hide()
    window.style_panel.setParent(None)
    window.style_panel.deleteLater()
    from makevid.qt.panels.style.panel import StylePanel
    window.style_panel = StylePanel(window.project)
    window.style_panel.closed.connect(window._hide_style_panel)
    window.style_panel.hide()
    if style_visible:
        window._show_style_tab(style_tab)

    # Rebuild panels (left stack)
    stack = window._left_stack
    while stack.count():
        w = stack.widget(0)
        stack.removeWidget(w)
        w.deleteLater()

    from makevid.qt.layout import _build_panels
    _build_panels(window)
    window._connect_signals()

    # Rebuild preview
    from makevid.qt.preview.preview_widget import PreviewWidget as PW
    old_preview  = window.preview
    window.preview = PW(window.project, window.timeline)
    window._preview_layout.replaceWidget(old_preview, window.preview)
    old_preview.deleteLater()
    window.preview._glow_layer = window._preview_shell

    # Rebuild timeline
    from makevid.qt.timeline.timeline_widget import TimelineWidget as TW
    old_timeline  = window.timeline
    window.timeline = TW(window.project)
    window.timeline.setMinimumHeight(100)
    window._timeline_layout.replaceWidget(old_timeline, window.timeline)
    old_timeline.deleteLater()
    window.preview.timeline = window.timeline

    window._connect_signals()

    window._engine_badge.set_text(f"{window._engine} | F5 OK")
    QTimer.singleShot(2000, lambda: window._engine_badge.set_text(window._engine))
