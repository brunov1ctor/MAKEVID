"""MAKEVID Qt — Janela principal."""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer

from makevid.qt.theme import STYLESHEET, C
from makevid.qt.topbar import build_topbar
from makevid.qt.layout import build_layout
from makevid.qt.project_controller import ProjectController, load_last_project
from makevid.qt.actions import ActionsMixin
from makevid.qt.app_state import AppState
from makevid.services.generation_service import GenerationService


class MakeVidWindow(ActionsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAKEVID")
        self.setMinimumSize(1200, 700)
        self.resize(1450, 850)

        self.project      = load_last_project()
        self._gen_service = GenerationService()
        self.state        = AppState(engine="Local (CPU)")
        self.state.project = self.project
        self._ctrl        = ProjectController(self)

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    @property
    def _engine(self):
        return self.state.engine

    @_engine.setter
    def _engine(self, v):
        self.state.engine = v

    @property
    def _selected_clip(self):
        return self.state.selected_clip

    @_selected_clip.setter
    def _selected_clip(self, v):
        self.state.selected_clip = v

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("AppRoot")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        self._topbar = build_topbar(self)
        main_layout.addWidget(self._topbar)

        build_layout(self, main_layout)

    # ── Signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.generator.generation_requested.connect(self._on_generation_requested)
        self.mixer.closed.connect(self._show_generator)
        self.fx_editor.closed.connect(self._show_generator)
        self.track_editor.closed.connect(self._show_generator)
        self.export_panel.closed.connect(self._show_generator)
        self.style_panel.closed.connect(self._hide_style_panel)
        self.recorder.closed.connect(self._return_to_prev)
        self.recorder.recorded.connect(self._return_to_prev)
        self.recorder.recorded.connect(self._refresh_preview_audio_browser)
        self.tts_panel.closed.connect(self._return_to_prev)
        self.tts_panel.generated.connect(self._return_to_prev)
        self.video_browser.closed.connect(self._show_generator)
        self.video_browser.video_added.connect(lambda: self.timeline.redraw())
        self.audio_browser.closed.connect(self._show_generator)
        self.audio_browser.audio_added.connect(lambda: self.timeline.redraw())
        self.track_menu.closed.connect(self._show_generator)
        self.track_menu.action_import.connect(self._import_audio_to_track)
        self.track_menu.action_record.connect(self._show_recorder)
        self.track_menu.action_tts.connect(self._show_tts)
        self.track_menu.action_clear.connect(self._clear_track)
        self.track_menu.action_add_fx.connect(self._add_fx_to_timeline)
        self.inpaint_panel.closed.connect(self._show_generator)
        self.inpaint_panel.inpaint_requested.connect(self._do_inpaint)

        self.project_changed.connect(self.generator._on_project_changed)
        self.project_changed.connect(self.export_panel._on_project_changed)
        self.project_changed.connect(self.video_browser._on_project_changed)
        self.project_changed.connect(self.audio_browser._on_project_changed)
        self.project_changed.connect(self.timeline._on_project_changed)
        self.project_changed.connect(self.preview._on_project_changed)
        self.project_changed.connect(self._sync_style_panel_if_visible)

        self.timeline._scene._interaction.item_clicked        = self._on_item_clicked
        self.timeline._scene._interaction.clip_clicked        = self._on_clip_clicked
        self.timeline._scene._interaction.label_clicked       = self._on_label_clicked
        self.timeline._scene._interaction.track_empty_clicked = self._on_label_clicked
        self.timeline.export_requested.connect(self._do_export_direct)
        self.timeline.export_config_requested.connect(self._show_export)
        self.timeline.keyPressEvent = self._timeline_key_handler
        self._h_splitter.splitterMoved.connect(lambda *_: None)
        self._v_splitter.splitterMoved.connect(lambda *_: None)

    def _sync_style_panel_if_visible(self, proj):
        if self.style_panel.isVisible():
            self.style_panel._on_project_changed(proj)

    # ── Panel switching ───────────────────────────────────────────────────────

    def _show_generator(self):
        self._left_stack.setCurrentWidget(self.generator)

    def _return_to_prev(self):
        self.timeline.redraw()
        prev = getattr(self, "_prev_panel", self.generator)
        self._left_stack.setCurrentWidget(prev)
        if prev is self.audio_browser:
            self.audio_browser.refresh()

    def _show_mixer(self, item):
        self.mixer.show_item(item)
        self._left_stack.setCurrentWidget(self.mixer)

    def _show_fx_editor(self, item):
        self.fx_editor.show_item(item, self.project)
        self._left_stack.setCurrentWidget(self.fx_editor)

    def _show_track_editor(self, item):
        self.track_editor.show_item(item, self.project)
        self._left_stack.setCurrentWidget(self.track_editor)

    def _show_export(self):
        self._left_stack.setCurrentWidget(self.export_panel)

    def _do_export_direct(self):
        self._left_stack.setCurrentWidget(self.export_panel)
        self.export_panel._do_export()

    def _show_recorder(self, track="voice"):
        self._prev_panel = self._left_stack.currentWidget()
        self.recorder.set_context(self.project, self.timeline, track)
        self._left_stack.setCurrentWidget(self.recorder)

    def _show_tts(self):
        self._prev_panel = self._left_stack.currentWidget()
        self.tts_panel.set_context(self.project, self.timeline)
        self._left_stack.setCurrentWidget(self.tts_panel)

    def _show_video_browser(self):
        self.preview.show_video_browser()

    def _show_audio_browser(self):
        self.preview.show_audio_browser()

    def _refresh_preview_audio_browser(self):
        if hasattr(self.preview, "_browser") and self.preview._browser:
            self.preview.show_audio_browser()

    def _on_item_clicked(self, track_item):
        if track_item.track == "fx":
            self._show_fx_editor(track_item)
        else:
            self._show_track_editor(track_item)

    def _on_clip_clicked(self, clip):
        self.generator.set_clip_data(clip)
        self._selected_clip = clip
        self._show_generator()
        self.preview.show_clip_properties(clip)

    def _on_label_clicked(self, track_name):
        self.timeline._selected_track_item_id = None
        self.timeline._selected_clip_id = None
        self.track_menu.show_track(track_name, self.project)
        self._left_stack.setCurrentWidget(self.track_menu)

    def _show_style_tab(self, tab_index):
        if not self.style_panel.isVisible():
            self._h_splitter.hide()
            self._v_splitter.insertWidget(0, self.style_panel)
            self.style_panel.show()
        self.style_panel._switch_style_tab(tab_index)

    def _hide_style_panel(self):
        self.style_panel.hide()
        self._v_splitter.insertWidget(0, self._h_splitter)
        self._h_splitter.show()

    def _update_project_badge(self):
        name = getattr(self.project, "name", None) or getattr(self.project, "id", "?")
        self._project_badge.set_text(name)

    def _set_engine(self, engine):
        self._engine = engine
        self._engine_badge.set_text(engine)
        for action in self._engine_menu.actions():
            if not action.isSeparator():
                action.setChecked(action.text() == engine)

    def _show_projects_panel(self):
        self.preview.show_projects_panel()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        sc = QShortcut(QKeySequence(Qt.Key_F5), self)
        sc.setContext(Qt.ApplicationShortcut)
        sc.activated.connect(self._safe_hot_reload)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self._safe_hot_reload()
        else:
            super().keyPressEvent(event)

    def _safe_hot_reload(self):
        print("[F5] Hot reload iniciado...")
        try:
            from makevid.qt.hot_reload import hot_reload
            hot_reload(self)
            print("[F5] Hot reload OK")
        except Exception as e:
            print(f"[F5] Hot reload ERRO: {e}")
            import traceback
            traceback.print_exc()
            self._engine_badge.set_text(f"{self._engine} | ERRO")
            QTimer.singleShot(3000, lambda: self._engine_badge.set_text(self._engine))

    def _timeline_key_handler(self, event):
        from PySide6.QtWidgets import QWidget
        if event.key() == Qt.Key_F5:
            self._safe_hot_reload()
        elif event.key() == Qt.Key_Space:
            if self.preview.player.is_playing:
                self.preview._pause()
            else:
                self.preview._play()
        elif event.key() == Qt.Key_Escape:
            self.timeline._exit_split_mode()
        elif event.key() == Qt.Key_Delete:
            self.timeline._on_delete()
        else:
            QWidget.keyPressEvent(self.timeline, event)

    # ── Project ───────────────────────────────────────────────────────────────

    def _on_project_opened(self, proj):
        self._ctrl.open(proj)


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET + "\n#AppRoot { background: " + C["bg"] + "; }")
    app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
    app.setEffectEnabled(Qt.UI_AnimateMenu, False)
    app.setEffectEnabled(Qt.UI_FadeMenu, False)
    app.setEffectEnabled(Qt.UI_AnimateCombo, False)
    window = MakeVidWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
