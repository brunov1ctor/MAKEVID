"""MAKEVID Qt - Janela principal."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QStackedWidget, QMenu
)
from PySide6.QtCore import Qt, QTimer

from makevid.qt.theme import STYLESHEET, C
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
from makevid.services.generation_service import GenerationService
from makevid.config import PROJECTS_DIR
from makevid.qt.actions import ActionsMixin


class MakeVidWindow(ActionsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAKEVID")
        self.setMinimumSize(1200, 700)
        self.resize(1450, 850)

        self.project = self._load_project()
        self._gen_service = GenerationService()
        self._engine = "Local (CPU)"

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    # ============================================================
    # UI BUILD
    # ============================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._topbar = self._build_topbar()
        main_layout.addWidget(self._topbar)

        # Linha separadora continua
        from PySide6.QtWidgets import QFrame
        topbar_sep = QFrame()
        topbar_sep.setFixedHeight(1)
        topbar_sep.setStyleSheet(f"background: {C['border']};")
        main_layout.addWidget(topbar_sep)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(6, 4, 6, 6)
        body_layout.setSpacing(0)
        main_layout.addWidget(body)

        self._v_splitter = QSplitter(Qt.Vertical)
        self._v_splitter.setHandleWidth(4)
        self._v_splitter.setChildrenCollapsible(True)
        body_layout.addWidget(self._v_splitter)

        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setHandleWidth(4)
        self._h_splitter.setChildrenCollapsible(True)
        self._v_splitter.addWidget(self._h_splitter)

        # Left panel stack
        self._left_stack = QStackedWidget()
        self._left_stack.setMinimumWidth(260)
        self._left_stack.setMinimumHeight(0)
        from PySide6.QtWidgets import QSizePolicy
        self._left_stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        self.generator = GeneratorPanel(self.project)
        self.mixer = MixerPanel()
        self.fx_editor = FxPanel()
        self.track_editor = TrackEditorPanel()
        self.export_panel = ExportPanel(self.project)
        self.recorder = RecorderPanel()
        self.tts_panel = TTSPanel()
        self.video_browser = VideoBrowserPanel(self.project)

        self._left_stack.addWidget(self.generator)       # 0
        self._left_stack.addWidget(self.mixer)           # 1
        self._left_stack.addWidget(self.fx_editor)       # 2
        self._left_stack.addWidget(self.track_editor)    # 3
        self._left_stack.addWidget(self.export_panel)    # 4
        self._left_stack.addWidget(self.recorder)        # 5
        self._left_stack.addWidget(self.tts_panel)       # 6
        self._left_stack.addWidget(self.video_browser)   # 7
        self.track_menu = TrackMenuPanel()
        self._left_stack.addWidget(self.track_menu)      # 8
        self.inpaint_panel = InpaintPanel()
        self._left_stack.addWidget(self.inpaint_panel)   # 9

        self._left_stack.setCurrentIndex(0)
        self._h_splitter.addWidget(self._left_stack)

        # Timeline + Preview
        self.timeline = TimelineWidget(self.project)
        self.timeline.setMinimumHeight(100)
        self.preview = PreviewWidget(self.project, self.timeline)
        self._h_splitter.addWidget(self.preview)

        self.audio_browser = AudioBrowserPanel(self.project, self.timeline)
        self._left_stack.addWidget(self.audio_browser)   # 10

        self._v_splitter.addWidget(self.timeline)

        # Style panel
        self.style_panel = StylePanel(self.project)
        self.style_panel.hide()

        self._v_splitter.setSizes([550, 250])
        self._h_splitter.setSizes([300, 900])

        # Splitter handles
        if self._h_splitter.count() >= 2:
            h_handle = self._h_splitter.handle(1)
            h_handle.setStyleSheet("background: #c89b3c;")
            h_handle.installEventFilter(self)
        if self._v_splitter.count() >= 2:
            v_handle = self._v_splitter.handle(1)
            v_handle.setStyleSheet("background: #c89b3c;")
            v_handle.installEventFilter(self)

    def _build_topbar(self) -> QWidget:
        tb = QWidget()
        tb.setFixedHeight(42)
        tb.setStyleSheet(f"background: {C['panel']};")
        h = QHBoxLayout(tb)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(2)

        lbl_make = QLabel("MAKE")
        lbl_make.setStyleSheet(f"color: {C['gold']}; font-size: 17pt; font-weight: bold; border: none;")
        h.addWidget(lbl_make)
        lbl_vid = QLabel("VID")
        lbl_vid.setStyleSheet(f"color: {C['cyan']}; font-size: 17pt; font-weight: bold; border: none;")
        h.addWidget(lbl_vid)

        sep = QLabel()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background: {C['border']};")
        h.addWidget(sep)
        h.addSpacing(6)

        mbs = (f"QPushButton {{ background: transparent; color: {C['text2']}; font-size: 10pt; "
               f"font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 4px 8px; }}"
               f"QPushButton:hover {{ border-color: {C['gold']}; background: #1a2a3a; }}"
               f"QPushButton::menu-indicator {{ width: 0; }}")

        mqss = (f"QMenu {{ background: {C['card']}; color: {C['text']}; border: 1px solid {C['gold']}; "
                f"border-radius: 4px; padding: 4px; }}"
                f"QMenu::item {{ padding: 6px 20px; border-radius: 3px; }}"
                f"QMenu::item:selected {{ background: {C['card_hover']}; }}"
                f"QMenu::separator {{ height: 1px; background: {C['border']}; margin: 4px 8px; }}")

        # Arquivo
        btn_arq = QPushButton("\U0001f4c1 Arquivo")
        btn_arq.setStyleSheet(mbs)
        m_arq = QMenu(btn_arq)
        m_arq.setStyleSheet(mqss)
        m_arq.addAction("Novo Projeto", self._new_project)
        m_arq.addSeparator()
        m_arq.addAction("Regerar Clip", self._regenerate_clip)
        m_arq.addAction("Duplicar Clip", self._duplicate_clip)
        m_arq.addAction("Dividir Clip", self._split_clip_at_playhead)
        m_arq.addSeparator()
        m_arq.addAction("Inpaint (Editar Regiao)", self._show_inpaint)
        m_arq.addAction("Export Game Engine", self._export_game_engine)
        m_arq.addSeparator()
        m_arq.addAction("Meus Videos", self._show_video_browser)
        m_arq.addAction("Meus Audios", self._show_audio_browser)
        m_arq.addAction("+ Importar Audio", self._import_audio)
        btn_arq.setMenu(m_arq)
        h.addWidget(btn_arq)

        # Engine
        btn_eng = QPushButton("\u2699 Engine")
        btn_eng.setStyleSheet(mbs)
        self._engine_menu = QMenu(btn_eng)
        self._engine_menu.setStyleSheet(mqss)
        for eng in ["Local (GPU)", "Local (CPU)", "Wan 2.2 TI2V", None,
                    "VACE (Referencia)", "V2V (Refinar)", None, "HuggingFace API"]:
            if eng is None:
                self._engine_menu.addSeparator()
            else:
                a = self._engine_menu.addAction(eng, lambda e=eng: self._set_engine(e))
                a.setCheckable(True)
                a.setChecked(eng == self._engine)
        btn_eng.setMenu(self._engine_menu)
        h.addWidget(btn_eng)

        # Estilo
        btn_est = QPushButton("\U0001f3a5 Projeto")
        btn_est.setStyleSheet(mbs)
        m_est = QMenu(btn_est)
        m_est.setStyleSheet(mqss)
        m_est.addAction("Storyboard", lambda: self._show_style_tab(0))
        m_est.addAction("Personagens", lambda: self._show_style_tab(1))
        m_est.addAction("Ambientacao", lambda: self._show_style_tab(2))
        btn_est.setMenu(m_est)
        h.addWidget(btn_est)

        # Audio IA
        btn_aia = QPushButton("\u266b Audio IA")
        btn_aia.setStyleSheet(mbs)
        m_aia = QMenu(btn_aia)
        m_aia.setStyleSheet(mqss)
        m_aia.addAction("Gerar Audio da Cena", self._generate_scene_audio)
        m_aia.addAction("Gerar Audio de Todas as Cenas", self._generate_all_audio)
        btn_aia.setMenu(m_aia)
        h.addWidget(btn_aia)

        # Logs
        btn_log = QPushButton("\U0001f4cb Logs")
        btn_log.setStyleSheet(mbs)
        m_log = QMenu(btn_log)
        m_log.setStyleSheet(mqss)
        m_log.addAction("Ver Logs", self._open_logs)
        btn_log.setMenu(m_log)
        h.addWidget(btn_log)

        h.addStretch()
        self._engine_label = QLabel(self._engine)
        self._engine_label.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 9pt; border: none;")
        h.addWidget(self._engine_label)
        return tb

    # ============================================================
    # SIGNALS
    # ============================================================

    def _connect_signals(self):
        self.generator.generation_requested.connect(self._on_generation_requested)
        self.mixer.closed.connect(self._show_generator)
        self.fx_editor.closed.connect(self._show_generator)
        self.track_editor.closed.connect(self._show_generator)
        self.export_panel.closed.connect(self._show_generator)
        self.style_panel.closed.connect(self._hide_style_panel)
        self.recorder.closed.connect(self._show_generator)
        self.recorder.recorded.connect(lambda: self.timeline.redraw())
        self.tts_panel.closed.connect(self._show_generator)
        self.tts_panel.generated.connect(lambda: self.timeline.redraw())
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

        self.timeline._scene._interaction.item_clicked = self._on_item_clicked
        self.timeline._scene._interaction.clip_clicked = self._on_clip_clicked
        self.timeline._scene._interaction.label_clicked = self._on_label_clicked
        self.timeline._scene._interaction.track_empty_clicked = self._on_label_clicked
        self.timeline.export_requested.connect(self._do_export_direct)
        self.timeline.export_config_requested.connect(self._show_export)
        self.timeline.keyPressEvent = self._timeline_key_handler

    # ============================================================
    # PANEL SWITCHING
    # ============================================================

    def _show_generator(self):
        self._left_stack.setCurrentIndex(0)

    def _show_mixer(self, item):
        self.mixer.show_item(item)
        self._left_stack.setCurrentIndex(1)

    def _show_fx_editor(self, item):
        self.fx_editor.show_item(item, self.project)
        self._left_stack.setCurrentIndex(2)

    def _show_track_editor(self, item):
        self.track_editor.show_item(item, self.project)
        self._left_stack.setCurrentIndex(3)

    def _show_export(self):
        self._left_stack.setCurrentIndex(4)

    def _do_export_direct(self):
        self._left_stack.setCurrentIndex(4)
        self.export_panel._do_export()

    def _show_recorder(self, track="voice"):
        self.recorder.set_context(self.project, self.timeline, track)
        self._left_stack.setCurrentIndex(5)

    def _show_tts(self):
        self.tts_panel.set_context(self.project, self.timeline)
        self._left_stack.setCurrentIndex(6)

    def _show_video_browser(self):
        self.preview.show_video_browser()

    def _show_audio_browser(self):
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
        if track_name == "fx":
            self._left_stack.setCurrentIndex(2)
        else:
            self.track_menu.show_track(track_name, self.project)
            self._left_stack.setCurrentIndex(8)

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

    def _set_engine(self, engine):
        self._engine = engine
        self._engine_label.setText(engine)
        for action in self._engine_menu.actions():
            if not action.isSeparator():
                action.setChecked(action.text() == engine)

    # ============================================================
    # SPLITTER HOVER + KEYBOARD
    # ============================================================

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Enter:
            parent = obj.parent()
            if isinstance(parent, QSplitter):
                parent.setHandleWidth(7)
                obj.setStyleSheet("background: #ffd700;")
        elif event.type() == QEvent.Leave:
            parent = obj.parent()
            if isinstance(parent, QSplitter):
                parent.setHandleWidth(4)
                obj.setStyleSheet("background: #c89b3c;")
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self._hot_reload()
        else:
            super().keyPressEvent(event)

    def _setup_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        sc = QShortcut(QKeySequence(Qt.Key_F5), self)
        sc.setContext(Qt.ApplicationShortcut)
        sc.activated.connect(self._safe_hot_reload)

    def _safe_hot_reload(self):
        print("[F5] Hot reload iniciado...")
        try:
            self._hot_reload()
            print("[F5] Hot reload OK")
        except Exception as e:
            print(f"[F5] Hot reload ERRO: {e}")
            import traceback
            traceback.print_exc()
            self._engine_label.setText(f"{self._engine} | F5 ERRO")
            QTimer.singleShot(3000, lambda: self._engine_label.setText(self._engine))

    def _hot_reload(self):
        """Reconstroi TODOS os paineis sem fechar o app."""
        import importlib, sys

        # Guardar estado
        style_visible = self.style_panel.isVisible()
        style_tab = self.style_panel._style_stack.currentIndex() if style_visible else 0
        left_idx = self._left_stack.currentIndex()

        # Recarregar todos os modulos de UI
        reload_prefixes = [
            "makevid.qt.panels.style.",
            "makevid.qt.panels.",
            "makevid.qt.preview.",
            "makevid.qt.timeline.",
        ]
        reload_mods = [
            m for m in list(sys.modules.keys())
            if any(m.startswith(p) for p in reload_prefixes)
        ]
        # Ordenar: dependencias primeiro (mais profundos primeiro)
        reload_mods.sort(key=lambda x: -x.count("."))
        for m in reload_mods:
            if m in sys.modules:
                try:
                    importlib.reload(sys.modules[m])
                except Exception as e:
                    print(f"Reload error {m}: {e}")

        # Rebuild style panel
        self.style_panel.hide()
        self.style_panel.setParent(None)
        self.style_panel.deleteLater()
        from makevid.qt.panels.style.panel import StylePanel as _SP
        self.style_panel = _SP(self.project)
        self.style_panel.closed.connect(self._hide_style_panel)
        self.style_panel.hide()
        if style_visible:
            self._show_style_tab(style_tab)

        # Rebuild left stack panels
        old_widgets = []
        for i in range(self._left_stack.count()):
            old_widgets.append(self._left_stack.widget(i))

        # Recriar paineis
        from makevid.qt.panels.generator_panel import GeneratorPanel
        from makevid.qt.panels.mixer_panel import MixerPanel
        from makevid.qt.panels.fx_panel import FxPanel
        from makevid.qt.panels.track_editor_panel import TrackEditorPanel
        from makevid.qt.panels.export_panel import ExportPanel
        from makevid.qt.panels.recorder_panel import RecorderPanel, TTSPanel
        from makevid.qt.panels.browser_panel import VideoBrowserPanel, AudioBrowserPanel
        from makevid.qt.panels.track_menu_panel import TrackMenuPanel
        from makevid.qt.panels.inpaint_panel import InpaintPanel

        # Remover todos os widgets antigos
        while self._left_stack.count():
            w = self._left_stack.widget(0)
            self._left_stack.removeWidget(w)
            w.deleteLater()

        self.generator = GeneratorPanel(self.project)
        self.mixer = MixerPanel()
        self.fx_editor = FxPanel()
        self.track_editor = TrackEditorPanel()
        self.export_panel = ExportPanel(self.project)
        self.recorder = RecorderPanel()
        self.tts_panel = TTSPanel()
        self.video_browser = VideoBrowserPanel(self.project)
        self.track_menu = TrackMenuPanel()
        self.inpaint_panel = InpaintPanel()
        self.audio_browser = AudioBrowserPanel(self.project, self.timeline)

        self._left_stack.addWidget(self.generator)       # 0
        self._left_stack.addWidget(self.mixer)           # 1
        self._left_stack.addWidget(self.fx_editor)       # 2
        self._left_stack.addWidget(self.track_editor)    # 3
        self._left_stack.addWidget(self.export_panel)    # 4
        self._left_stack.addWidget(self.recorder)        # 5
        self._left_stack.addWidget(self.tts_panel)       # 6
        self._left_stack.addWidget(self.video_browser)   # 7
        self._left_stack.addWidget(self.track_menu)      # 8
        self._left_stack.addWidget(self.inpaint_panel)   # 9
        self._left_stack.addWidget(self.audio_browser)   # 10

        self._left_stack.setCurrentIndex(left_idx)

        # Rebuild preview
        from makevid.qt.preview.preview_widget import PreviewWidget
        old_preview = self.preview
        self.preview = PreviewWidget(self.project, self.timeline)
        self._h_splitter.replaceWidget(1, self.preview)
        old_preview.deleteLater()

        # Rebuild timeline
        from makevid.qt.timeline.timeline_widget import TimelineWidget
        old_timeline = self.timeline
        self.timeline = TimelineWidget(self.project)
        self.timeline.setMinimumHeight(100)
        self._v_splitter.replaceWidget(1, self.timeline)
        old_timeline.deleteLater()
        # Atualizar referencia no preview
        self.preview.timeline = self.timeline

        # Reconectar signals
        self._connect_signals()

        self._engine_label.setText(f"{self._engine} | F5 reload OK")
        QTimer.singleShot(2000, lambda: self._engine_label.setText(self._engine))

    def _timeline_key_handler(self, event):
        if event.key() == Qt.Key_F5:
            self._hot_reload()
        elif event.key() == Qt.Key_Space:
            if self.preview.player.is_playing:
                self.preview.player.pause()
                self.preview._is_playing = False
                self.preview._show_play_button()
            elif self.preview.player.is_paused:
                self.preview.player.play()
                self.preview._is_playing = True
                self.preview._display.setText("")
            else:
                self.preview.player.play_from(self.timeline.playhead_pos, self.timeline.playback_speed)
                self.preview._is_playing = True
                self.preview._display.setText("")
        elif event.key() == Qt.Key_Escape:
            self.timeline._exit_split_mode()
        elif event.key() == Qt.Key_Delete:
            self.timeline._on_delete()
        else:
            QWidget.keyPressEvent(self.timeline, event)


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
    window = MakeVidWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
