"""MAKEVID Qt - Janela principal."""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QStackedWidget, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QBrush, QFont

from makevid.qt.theme import STYLESHEET, C
from makevid.qt.widgets import GlassPanel, GlassButton, TopbarButton, GlowDot
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
from makevid.qt.preview.glow_layer import PreviewGlowPanel


# ── Logo widget pintado via QPainter ──────────────────────────────────────────

class _LogoWidget(QWidget):
    """MAKE·VID em dourado/ciano com gradiente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(130, 40)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # "MAKE" — gradiente dourado
        grad = QLinearGradient(0, 0, 65, 0)
        grad.setColorAt(0.0, QColor(C["secondary"]))
        grad.setColorAt(1.0, QColor(C["primary"]))
        p.setPen(QColor(C["primary"]))
        p.setFont(QFont("Segoe UI", 15, QFont.Bold))
        p.drawText(0, 30, "MAKE")

        # "VID" — ciano
        p.setPen(QColor(C["accent"]))
        p.setFont(QFont("Segoe UI", 15, QFont.Bold))
        p.drawText(68, 30, "VID")
        p.end()


# ── Engine badge ───────────────────────────────────────────────────────────────

class _EngineBadge(QWidget):
    """Badge pequeno mostrando engine ativa."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._text = text
        self.setFixedHeight(22)
        self.setMinimumWidth(80)

    def set_text(self, text):
        self._text = text
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        from PySide6.QtGui import QFontMetrics, QPen
        font = QFont("Consolas", 8)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self._text) + 16
        self.setFixedWidth(max(tw, 80))

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)

        bg = QColor(C["glass"])
        bg.setAlpha(180)
        p.fillPath(path, bg)

        from PySide6.QtGui import QPen
        bc = QColor(C["glass_border"])
        bc.setAlpha(80)
        p.setPen(QPen(bc, 1))
        p.drawPath(path)

        p.setPen(QColor(C["text3"]))
        p.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self._text)
        p.end()


class _ProjectBadge(QWidget):
    """Badge destacado mostrando o projeto ativo."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._text = text
        self.setFixedHeight(30)
        self.setMinimumWidth(100)

    def set_text(self, text):
        self._text = text
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        from PySide6.QtGui import QFontMetrics, QPen
        font = QFont("Segoe UI", 11, QFont.Bold)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self._text) + 20
        self.setFixedWidth(max(tw, 80))

        p.setPen(QColor(C["primary"]))
        p.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, self._text)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
#  MakeVidWindow
# ══════════════════════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("AppRoot")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # ── Topbar ────────────────────────────────────────────────────────────
        self._topbar = self._build_topbar()
        main_layout.addWidget(self._topbar)

        # ── Workspace (splitters) ─────────────────────────────────────────────
        self._v_splitter = QSplitter(Qt.Vertical)
        self._v_splitter.setHandleWidth(10)
        self._v_splitter.setChildrenCollapsible(False)
        self._v_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        main_layout.addWidget(self._v_splitter)

        self._h_splitter = QSplitter(Qt.Horizontal)
        self._h_splitter.setHandleWidth(10)
        self._h_splitter.setChildrenCollapsible(False)
        self._h_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        # ── Left stack ────────────────────────────────────────────────────────
        self._left_stack = QStackedWidget()
        self._left_stack.setMinimumWidth(260)
        self._left_stack.setMinimumHeight(0)
        self._left_stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self._left_stack.setStyleSheet("background: transparent;")

        # ── Preview + Timeline ────────────────────────────────────────────────
        self.timeline = TimelineWidget(self.project)
        self.timeline.setMinimumHeight(100)
        self.preview  = PreviewWidget(self.project, self.timeline)

        self._build_panels()

        # ── GlassPanel wrappers ───────────────────────────────────────────────
        left_shell = GlassPanel(radius=20, shadow=True, shadow_radius=30, shadow_dy=8)
        self._left_layout = QVBoxLayout(left_shell)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(0)
        self._left_layout.addWidget(self._left_stack)

        preview_shell = PreviewGlowPanel(radius=20, shadow=True, shadow_radius=36, shadow_dy=10)
        self._preview_layout = QVBoxLayout(preview_shell)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        self._preview_layout.addWidget(self.preview)
        self._preview_shell = preview_shell
        self.preview._glow_layer = preview_shell

        timeline_shell = GlassPanel(radius=20, shadow=True, shadow_radius=28, shadow_dy=6)
        self._timeline_layout = QVBoxLayout(timeline_shell)
        self._timeline_layout.setContentsMargins(0, 0, 0, 0)
        self._timeline_layout.addWidget(self.timeline)

        # ── Montar splitters ──────────────────────────────────────────────────
        self._h_splitter.addWidget(left_shell)
        self._h_splitter.addWidget(preview_shell)

        self._v_splitter.addWidget(self._h_splitter)
        self._v_splitter.addWidget(timeline_shell)

        self._v_splitter.setSizes([560, 260])
        self._h_splitter.setSizes([300, 900])

        # Posicionar glow após layout estar montado
        QTimer.singleShot(0, self._update_glow_position)

        # ── Style panel (oculto) ──────────────────────────────────────────────
        self.style_panel = StylePanel(self.project)
        self.style_panel.hide()

    # ══════════════════════════════════════════════════════════════════════════
    # PANELS
    # ══════════════════════════════════════════════════════════════════════════

    def _build_panels(self):
        """Cria (ou recria) todos os paineis do left_stack."""
        while self._left_stack.count():
            w = self._left_stack.widget(0)
            self._left_stack.removeWidget(w)
            w.deleteLater()

        self.generator     = GeneratorPanel(self.project)
        self.mixer         = MixerPanel()
        self.fx_editor     = FxPanel()
        self.track_editor  = TrackEditorPanel()
        self.export_panel  = ExportPanel(self.project)
        self.recorder      = RecorderPanel()
        self.tts_panel     = TTSPanel()
        self.video_browser = VideoBrowserPanel(self.project)
        self.track_menu    = TrackMenuPanel()
        self.inpaint_panel = InpaintPanel()
        self.audio_browser = AudioBrowserPanel(self.project, self.timeline)

        for panel in (
            self.generator, self.mixer, self.fx_editor, self.track_editor,
            self.export_panel, self.recorder, self.tts_panel, self.video_browser,
            self.track_menu, self.inpaint_panel, self.audio_browser,
        ):
            self._left_stack.addWidget(panel)
        self._left_stack.setCurrentWidget(self.generator)

    # ══════════════════════════════════════════════════════════════════════════
    # TOPBAR
    # ══════════════════════════════════════════════════════════════════════════

    def _build_topbar(self) -> GlassPanel:
        tb = GlassPanel(radius=22, shadow=True, shadow_radius=24, shadow_dy=6)
        tb.setFixedHeight(58)

        h = QHBoxLayout(tb)
        h.setContentsMargins(18, 8, 18, 8)
        h.setSpacing(6)

        # Logo
        logo = _LogoWidget()
        h.addWidget(logo)

        # Divisor
        div = QWidget()
        div.setFixedSize(1, 22)
        div.setStyleSheet(f"background: {C['glass_border']};")
        h.addWidget(div)
        h.addSpacing(4)

        # Menu QSS compartilhado (apenas para QMenu — não para botões)
        mqss = (
            f"QMenu {{ background: {C['card']}; color: {C['text']}; "
            f"border: 1px solid {C['glass_border']}; border-radius: 12px; padding: 6px 4px; }}"
            f"QMenu::item {{ padding: 7px 22px; border-radius: 8px; margin: 1px 4px; }}"
            f"QMenu::item:selected {{ background: {C['glass_hover']}; color: {C['primary']}; }}"
            f"QMenu::item:pressed {{ background: {C['primary']}; color: {C['dark_text']}; }}"
            f"QMenu::separator {{ height: 1px; background: {C['border']}; margin: 4px 10px; }}"
            f"QMenu::indicator:checked {{ width: 8px; height: 8px; border-radius: 4px; "
            f"background: {C['primary']}; margin-left: 6px; }}"
        )

        def _menu_btn(label, icon):
            btn = TopbarButton(f"{icon}  {label}")
            btn.setFixedHeight(38)
            return btn, mqss

        # Arquivo
        btn_arq, _ = _menu_btn("Arquivo", "📁")
        m_arq = QMenu(btn_arq)
        m_arq.setStyleSheet(mqss)
        m_arq.addAction("Projetos", self._show_projects_panel)
        m_arq.addAction("Limpar Projeto", self._clear_project)
        m_arq.addSeparator()
        m_arq.addAction("Meus Videos", self._show_video_browser)
        m_arq.addAction("Meus Audios", self._show_audio_browser)
        btn_arq.setMenu(m_arq)
        h.addWidget(btn_arq)

        # Engine
        btn_eng, _ = _menu_btn("Engine", "⚙")
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

        # Tema
        btn_est, _ = _menu_btn("Tema", "🎨")
        m_est = QMenu(btn_est)
        m_est.setStyleSheet(mqss)
        m_est.addAction("Storyboard",   lambda: self._show_style_tab(0))
        m_est.addAction("Personagens",  lambda: self._show_style_tab(1))
        m_est.addAction("Ambientacao",  lambda: self._show_style_tab(2))
        btn_est.setMenu(m_est)
        h.addWidget(btn_est)

        # Audio IA
        btn_aia, _ = _menu_btn("Audio IA", "♫")
        m_aia = QMenu(btn_aia)
        m_aia.setStyleSheet(mqss)
        m_aia.addAction("Gerar Audio da Cena",          self._generate_scene_audio)
        m_aia.addAction("Gerar Audio de Todas as Cenas", self._generate_all_audio)
        btn_aia.setMenu(m_aia)
        h.addWidget(btn_aia)

        # Logs
        btn_log, _ = _menu_btn("Logs", "📋")
        m_log = QMenu(btn_log)
        m_log.setStyleSheet(mqss)
        m_log.addAction("Ver Logs", self._open_logs)
        btn_log.setMenu(m_log)
        h.addWidget(btn_log)

        h.addStretch()

        # GlowDot de status
        self._status_dot = GlowDot(color=C["track_sfx"])
        h.addWidget(self._status_dot)

        # Project badge
        self._project_badge = _ProjectBadge(self.project.name or self.project.id)
        h.addWidget(self._project_badge)

        # Divisor
        div2 = QWidget()
        div2.setFixedSize(1, 22)
        div2.setStyleSheet(f"background: {C['glass_border']};")
        h.addWidget(div2)

        # Engine badge
        self._engine_badge = _EngineBadge(self._engine)
        h.addWidget(self._engine_badge)

        return tb

    # ══════════════════════════════════════════════════════════════════════════
    # SIGNALS
    # ══════════════════════════════════════════════════════════════════════════

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

        # Propaga troca de projeto para todos os paineis
        self.project_changed.connect(self.generator._on_project_changed)
        self.project_changed.connect(self.export_panel._on_project_changed)
        self.project_changed.connect(self.video_browser._on_project_changed)
        self.project_changed.connect(self.audio_browser._on_project_changed)
        self.project_changed.connect(self.timeline._on_project_changed)
        self.project_changed.connect(self.preview._on_project_changed)
        self.project_changed.connect(self.style_panel._on_project_changed)

        self.timeline._scene._interaction.item_clicked        = self._on_item_clicked
        self.timeline._scene._interaction.clip_clicked        = self._on_clip_clicked
        self.timeline._scene._interaction.label_clicked       = self._on_label_clicked
        self.timeline._scene._interaction.track_empty_clicked = self._on_label_clicked
        self.timeline.export_requested.connect(self._do_export_direct)
        self.timeline.export_config_requested.connect(self._show_export)
        self.timeline.keyPressEvent = self._timeline_key_handler
        self._h_splitter.splitterMoved.connect(lambda *_: self._update_glow_position())
        self._v_splitter.splitterMoved.connect(lambda *_: self._update_glow_position())

    # ══════════════════════════════════════════════════════════════════════════
    # PANEL SWITCHING
    # ══════════════════════════════════════════════════════════════════════════

    def _show_generator(self):
        self._left_stack.setCurrentWidget(self.generator)

    def _return_to_prev(self):
        self.timeline.redraw()
        prev = getattr(self, '_prev_panel', self.generator)
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
        """Reabre o browser de audio do preview se estiver visivel."""
        if hasattr(self.preview, '_browser') and self.preview._browser:
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
        name = getattr(self.project, 'name', None) or getattr(self.project, 'id', '?')
        self._project_badge.set_text(name)

    def _set_engine(self, engine):
        self._engine = engine
        self._engine_badge.set_text(engine)
        for action in self._engine_menu.actions():
            if not action.isSeparator():
                action.setChecked(action.text() == engine)

    def _update_glow_position(self):
        pass  # glow é pintado diretamente no PreviewGlowPanel, sem reposicionamento

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # ══════════════════════════════════════════════════════════════════════════
    # KEYBOARD
    # ══════════════════════════════════════════════════════════════════════════

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
            self._engine_badge.set_text(f"{self._engine} | ERRO")
            QTimer.singleShot(3000, lambda: self._engine_badge.set_text(self._engine))

    # ══════════════════════════════════════════════════════════════════════════
    # HOT RELOAD  — troca conteúdo dentro dos GlassPanel, não o shell
    # ══════════════════════════════════════════════════════════════════════════

    def _hot_reload(self):
        import importlib, sys

        style_visible = self.style_panel.isVisible()
        style_tab     = self.style_panel._style_stack.currentIndex() if style_visible else 0

        # Recarregar módulos de UI
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

        self._build_panels()

        # Rebuild preview — troca dentro do GlassPanel, não o shell
        from makevid.qt.preview.preview_widget import PreviewWidget
        old_preview  = self.preview
        self.preview = PreviewWidget(self.project, self.timeline)
        self._preview_layout.replaceWidget(old_preview, self.preview)
        old_preview.deleteLater()
        self.preview._glow_layer = self._preview_shell
        QTimer.singleShot(0, self._update_glow_position)

        # Rebuild timeline — troca dentro do GlassPanel, não o shell
        from makevid.qt.timeline.timeline_widget import TimelineWidget
        old_timeline  = self.timeline
        self.timeline = TimelineWidget(self.project)
        self.timeline.setMinimumHeight(100)
        self._timeline_layout.replaceWidget(old_timeline, self.timeline)
        old_timeline.deleteLater()

        # Atualizar referência no preview
        self.preview.timeline = self.timeline

        self._connect_signals()

        self._engine_badge.set_text(f"{self._engine} | F5 OK")
        QTimer.singleShot(2000, lambda: self._engine_badge.set_text(self._engine))

    # ══════════════════════════════════════════════════════════════════════════
    # TIMELINE KEY HANDLER
    # ══════════════════════════════════════════════════════════════════════════

    def _timeline_key_handler(self, event):
        if event.key() == Qt.Key_F5:
            self._hot_reload()
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


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET + "\n#AppRoot { background: " + C["bg"] + "; }")
    app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
    window = MakeVidWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
