"""Preview Widget Qt - Display de video com play/pause e progress bar."""

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont, QCursor

from makevid.qt.theme import C
from makevid.qt.preview.player import TimelinePlayerQt


class PreviewWidget(QWidget):
    """Display de video com controles de playback."""

    def __init__(self, project, timeline_widget, parent=None):
        super().__init__(parent)
        self.project = project
        self.timeline = timeline_widget
        self._is_playing = False

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Display principal
        self._display = QLabel()
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setMinimumSize(200, 80)
        self._display.setStyleSheet(
            f"background: #050508; border: 1px solid {C['border']}; border-radius: 4px;")
        self._display.setCursor(QCursor(Qt.PointingHandCursor))
        self._display.mousePressEvent = self._on_display_click
        layout.addWidget(self._display, stretch=1)

        # Progress bar (estilo YouTube) - escondida quando nao em uso
        self._progress_container = QWidget()
        self._progress_container.setFixedHeight(36)
        self._progress_container.setStyleSheet("background: transparent;")
        pc_layout = QVBoxLayout(self._progress_container)
        pc_layout.setContentsMargins(0, 14, 0, 14)
        pc_layout.setSpacing(0)
        self._progress = QProgressBar()
        self._progress.setFixedHeight(4)
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 2px; }")
        self._progress.setCursor(QCursor(Qt.PointingHandCursor))
        self._progress.setMouseTracking(True)
        self._progress_container.enterEvent = self._on_progress_enter
        self._progress_container.leaveEvent = self._on_progress_leave
        self._progress.mousePressEvent = self._on_progress_click
        pc_layout.addWidget(self._progress)
        self._progress_container.hide()
        layout.addWidget(self._progress_container)

        # Info label
        self._info = QLabel()
        self._info.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        layout.addWidget(self._info)

        # Player
        self.player = TimelinePlayerQt(self)
        self.player.set_project(self.project)

        # Play button overlay (texto no display)
        self._show_play_button()

    def _connect_signals(self):
        self.player.frame_ready.connect(self._on_frame)
        self.player.playback_ended.connect(self._on_ended)
        self.player.time_updated.connect(self._on_time_update)
        self.timeline.playhead_moved.connect(self._on_playhead_moved)

    # ============================================================
    # DISPLAY
    # ============================================================

    def _on_frame(self, frame_bgr):
        """Recebe frame BGR do player e mostra no display."""
        h, w, ch = frame_bgr.shape
        # Converter BGR para RGB
        frame_rgb = frame_bgr[:, :, ::-1].copy()
        img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)

        # Escalar para caber no display mantendo aspect ratio
        display_size = self._display.size()
        pixmap = QPixmap.fromImage(img).scaled(
            display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._display.setPixmap(pixmap)

    def _show_play_button(self):
        """Mostra ▶ grande estilo YouTube no display."""
        self._display.setPixmap(QPixmap())  # limpa frame
        self._display.setText("")
        self._display.setStyleSheet(
            f"background: #050508; border: 1px solid {C['border']}; border-radius: 4px;")
        # Remover overlay anterior se existir
        if hasattr(self, '_play_overlay') and self._play_overlay:
            self._play_overlay.deleteLater()
            self._play_overlay = None
        # Usar texto centralizado direto no QLabel display
        self._display.setText("▶")
        self._display.setStyleSheet(
            f"background: #050508; border: 1px solid {C['border']}; border-radius: 4px; "
            f"color: rgba(255,255,255,150); font-size: 52pt;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposicionar props panel se visivel
        if hasattr(self, '_props_panel') and self._props_panel and self._props_panel.isVisible():
            panel_h = int(self._display.height() * 0.95)
            self._props_panel.setFixedHeight(max(200, panel_h))
            self._props_panel.move(max(0, self._display.width() - 235), 5)

    # ============================================================
    # CONTROLES
    # ============================================================

    def _on_display_click(self, event):
        """Click no display = play/pause."""
        if self.player.is_playing:
            self.player.pause()
            self._is_playing = False
            self._show_play_button()
        elif self.player.is_paused:
            self.player.play()
            self._is_playing = True
            self._display.setText("")
            self._display.setStyleSheet(
                f"background: #050508; border: 1px solid {C['border']}; border-radius: 4px;")
            self._progress_container.show()
        else:
            speed = self.timeline.playback_speed
            pos = self.timeline.playhead_pos
            self.player.play_from(pos, speed)
            self._is_playing = True
            self._display.setText("")
            self._display.setStyleSheet(
                f"background: #050508; border: 1px solid {C['border']}; border-radius: 4px;")
            self._progress_container.show()

    def _on_progress_click(self, event):
        """Click na barra de progresso = seek."""
        w = self._progress.width()
        if w <= 0:
            return
        ratio = max(0, min(1.0, event.position().x() / w))
        total_dur = self.project.total_duration()
        target = ratio * total_dur
        self.player.seek_to_time(target)
        self.timeline.set_playhead(target)

    def _on_progress_enter(self, event):
        """Hover na barra: cresce e mostra ponteira."""
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(
            "QProgressBar { background: #1a1a2a; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 3px; }")
        if not hasattr(self, '_progress_dot') or not self._progress_dot:
            self._progress_dot = QLabel(self._progress_container)
            self._progress_dot.setFixedSize(30, 30)
            self._progress_dot.setText("\u2734")
            self._progress_dot.setAlignment(Qt.AlignCenter)
            self._progress_dot.setStyleSheet(
                "QLabel { background: transparent; color: #ffffff; font-size: 18pt; "
                "border: none; }")

        val = self._progress.value()
        max_val = self._progress.maximum() or 1
        x_pos = int((val / max_val) * self._progress.width())
        self._progress_dot.move(max(0, x_pos - 15), 3)
        self._progress_dot.show()

    def _on_progress_leave(self, event):
        """Sai do hover: volta fino, esconde ponteira."""
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: #ff0000; border-radius: 2px; }")
        if hasattr(self, '_progress_dot') and self._progress_dot:
            self._progress_dot.hide()

    # ============================================================
    # SIGNALS
    # ============================================================

    def _on_time_update(self, time_pos):
        """Player atualiza posição."""
        total = self.project.total_duration()
        if total > 0:
            self._progress.setValue(int(time_pos / total * 1000))
            # Atualizar ponteira + sparks se visiveis
            if hasattr(self, '_progress_dot') and self._progress_dot and self._progress_dot.isVisible():
                x_pos = int((time_pos / total) * self._progress.width())
                self._progress_dot.move(max(0, x_pos - 15), 3)
        # Atualizar playhead na timeline
        self.timeline.playhead_pos = time_pos
        self.timeline._scene.update_playhead(time_pos, self.timeline.zoom)
        # Info
        m = int(time_pos) // 60
        s = time_pos % 60
        tm = int(total) // 60
        ts = total % 60
        self._info.setText(f"{m}:{s:04.1f} / {tm}:{ts:04.1f}")

    def _on_ended(self):
        """Playback terminou."""
        self._is_playing = False
        self._progress.setValue(0)
        if hasattr(self, '_progress_dot') and self._progress_dot:
            self._progress_dot.hide()
        self._progress_container.hide()
        self._show_play_button()
        self._info.setText("")
        # Reset playhead na timeline
        self.timeline.playhead_pos = 0
        self.timeline._scene.update_playhead(0, self.timeline.zoom)

    def _on_playhead_moved(self, time_pos):
        """Timeline moveu playhead (scrub manual)."""
        if self.player.is_playing:
            # Seek sem parar o playback
            self.player.seek_to_time(time_pos)
        else:
            # Scrub: mostrar frame na posição
            self._scrub_frame(time_pos)

    def _scrub_frame(self, time_pos):
        """Mostra frame na posição sem tocar."""
        from pathlib import Path
        try:
            import cv2
        except ImportError:
            return

        clips = sorted(self.project.clips, key=lambda c: c.position)
        if not clips:
            return

        # Encontrar clip na posição
        current = 0.0
        for clip in clips:
            if current + clip.duration > time_pos:
                if clip.status == "done" and clip.video_path and Path(clip.video_path).exists():
                    cap = cv2.VideoCapture(str(clip.video_path))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 16
                    local_time = time_pos - current
                    target_frame = int(local_time * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target_frame))
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        # Aplicar FX
                        fx_items = self.project.get_track_items("fx")
                        if fx_items:
                            from makevid.core.fx_processor import apply_fx_to_frame
                            frame_rgb = frame[:, :, ::-1]
                            total_dur = self.project.total_duration()
                            frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, time_pos, total_dur)
                            frame = frame_rgb[:, :, ::-1]
                        self._on_frame(frame)
                        self._info.setText(f"{time_pos:.1f}s | Clip {clip.position+1}")
                return
            current += clip.duration


    # ============================================================
    # BROWSER (abre dentro do preview substituindo o display)
    # ============================================================

    def show_video_browser(self):
        """Abre browser de videos no lugar do display."""
        import time as _time
        from makevid.config import OUTPUTS_DIR
        from PySide6.QtWidgets import QScrollArea, QFrame, QPushButton, QLineEdit, QFileDialog
        import shutil

        if self.player.is_playing:
            self.player.stop()
        self._display.hide()
        self._progress.hide()
        self._info.hide()
        if hasattr(self, '_browser') and self._browser:
            self._browser.deleteLater()

        self._browser = QFrame(self)
        self._browser.setStyleSheet("background: #050508;")
        bl = QVBoxLayout(self._browser)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background: {C['card']};")
        from PySide6.QtWidgets import QHBoxLayout as HL
        hl = HL(hdr)
        hl.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("MEUS VIDEOS")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 11pt; font-weight: bold;")
        hl.addWidget(lbl)
        hl.addStretch()
        btn_imp = QPushButton("+ Importar")
        btn_imp.setFixedHeight(22)
        btn_imp.setStyleSheet(f"background: {C['card']}; color: {C['gold']}; font-size: 8pt; font-weight: bold; border: 1px solid {C['gold']}; border-radius: 3px; padding: 0 8px;")
        btn_imp.clicked.connect(self._browser_import_video)
        hl.addWidget(btn_imp)
        btn_clean = QPushButton("Remover Inutilizados")
        btn_clean.setFixedHeight(22)
        btn_clean.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 8px;")
        btn_clean.clicked.connect(self._browser_clean_videos)
        hl.addWidget(btn_clean)
        btn_x = QPushButton("X")
        btn_x.setFixedSize(28, 22)
        btn_x.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        btn_x.clicked.connect(self._close_browser)
        hl.addWidget(btn_x)
        bl.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        sc = QWidget()
        self._browser_layout = QVBoxLayout(sc)
        self._browser_layout.setContentsMargins(6, 6, 6, 6)
        self._browser_layout.setSpacing(4)
        scroll.setWidget(sc)
        bl.addWidget(scroll)

        from pathlib import Path
        videos = sorted(OUTPUTS_DIR.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not videos:
            self._browser_layout.addWidget(QLabel("Nenhum video encontrado."))
        else:
            for vpath in videos:
                self._build_browser_video_card(vpath)
        self._browser_layout.addStretch()
        self.layout().insertWidget(0, self._browser, stretch=1)
        self._browser.show()

    def show_audio_browser(self):
        """Abre browser de audios no lugar do display."""
        import time as _time
        from makevid.config import AUDIO_DIR
        from PySide6.QtWidgets import QScrollArea, QFrame, QPushButton
        from PySide6.QtWidgets import QHBoxLayout as HL

        if self.player.is_playing:
            self.player.stop()
        self._display.hide()
        self._progress.hide()
        self._info.hide()
        if hasattr(self, '_browser') and self._browser:
            self._browser.deleteLater()

        self._browser = QFrame(self)
        self._browser.setStyleSheet("background: #050508;")
        bl = QVBoxLayout(self._browser)
        bl.setContentsMargins(0, 0, 0, 0)

        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background: {C['card']};")
        hl = HL(hdr)
        hl.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("MEUS AUDIOS")
        lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 11pt; font-weight: bold;")
        hl.addWidget(lbl)
        hl.addStretch()
        btn_clean = QPushButton("Remover Inutilizados")
        btn_clean.setFixedHeight(22)
        btn_clean.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 8px;")
        btn_clean.clicked.connect(self._browser_clean_audios)
        hl.addWidget(btn_clean)
        btn_x = QPushButton("X")
        btn_x.setFixedSize(28, 22)
        btn_x.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        btn_x.clicked.connect(self._close_browser)
        hl.addWidget(btn_x)
        bl.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        sc = QWidget()
        self._browser_layout = QVBoxLayout(sc)
        self._browser_layout.setContentsMargins(6, 6, 6, 6)
        self._browser_layout.setSpacing(4)
        scroll.setWidget(sc)
        bl.addWidget(scroll)

        from pathlib import Path
        audios = sorted([f for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac") for f in AUDIO_DIR.rglob(ext)],
                        key=lambda p: p.stat().st_mtime, reverse=True)
        if not audios:
            self._browser_layout.addWidget(QLabel("Nenhum audio."))
        else:
            for ap in audios:
                self._build_browser_audio_card(ap)
        self._browser_layout.addStretch()
        self.layout().insertWidget(0, self._browser, stretch=1)
        self._browser.show()

    def _build_browser_video_card(self, vpath):
        import time as _time
        from PySide6.QtWidgets import QFrame, QPushButton, QLineEdit
        from PySide6.QtWidgets import QHBoxLayout as HL, QVBoxLayout as VL
        card = QFrame()
        card.setStyleSheet(f"background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = HL(card)
        cl.setContentsMargins(6, 6, 6, 6)
        try:
            import cv2
            cap = cv2.VideoCapture(str(vpath))
            ret, frame = cap.read()
            cap.release()
            if ret:
                rgb = frame[:, :, ::-1].copy()
                h, w = rgb.shape[:2]
                img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
                pm = QPixmap.fromImage(img).scaled(120, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                th = QLabel()
                th.setPixmap(pm)
                th.setFixedSize(120, 68)
                cl.addWidget(th)
        except Exception:
            pass
        info = VL()
        info.setSpacing(2)
        ne = QLineEdit(vpath.stem[:30])
        ne.setStyleSheet(f"background: transparent; color: {C['text']}; font-weight: bold; font-size: 10pt; border: none;")
        ne.returnPressed.connect(lambda p=vpath, e=ne: self._rename_video(p, e.text()))
        info.addWidget(ne)
        sz = vpath.stat().st_size / 1e6
        mt = _time.strftime("%d/%m %H:%M", _time.localtime(vpath.stat().st_mtime))
        info.addWidget(QLabel(f"{sz:.1f} MB | {mt}"))
        btns = HL()
        ba = QPushButton("+ Timeline")
        ba.setFixedHeight(22)
        ba.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 6px;")
        ba.clicked.connect(lambda ck=False, p=vpath: self._add_video_to_tl(p))
        btns.addWidget(ba)
        bd = QPushButton("Deletar")
        bd.setFixedHeight(22)
        bd.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 6px;")
        bd.clicked.connect(lambda ck=False, p=vpath, c=card: [p.unlink(missing_ok=True), c.deleteLater()])
        btns.addWidget(bd)
        btns.addStretch()
        info.addLayout(btns)
        cl.addLayout(info)
        self._browser_layout.addWidget(card)

    def _build_browser_audio_card(self, apath):
        import time as _time
        from PySide6.QtWidgets import QFrame, QPushButton
        from PySide6.QtWidgets import QHBoxLayout as HL, QVBoxLayout as VL
        card = QFrame()
        card.setStyleSheet(f"background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = HL(card)
        cl.setContentsMargins(6, 6, 6, 6)
        info = VL()
        info.setSpacing(2)
        info.addWidget(QLabel(apath.stem[:25]))
        dur = 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            dur = get_audio_duration(str(apath)) or 0
        except Exception:
            pass
        sz = apath.stat().st_size / 1024
        mt = _time.strftime("%d/%m %H:%M", _time.localtime(apath.stat().st_mtime))
        info.addWidget(QLabel(f"{dur:.1f}s | {sz:.0f}KB | {mt}"))
        cl.addLayout(info)
        cl.addStretch()
        bp = QPushButton("\u25b6")
        bp.setFixedSize(28, 24)
        bp.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; border: 1px solid {C['cyan']}; border-radius: 3px;")
        bp.clicked.connect(lambda ck=False, p=apath: self._play_audio_file(p))
        cl.addWidget(bp)
        ba = QPushButton("+ TL")
        ba.setFixedSize(40, 24)
        ba.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px;")
        ba.clicked.connect(lambda ck=False, p=apath, d=dur: self._add_audio_to_tl(p, d))
        cl.addWidget(ba)
        bd = QPushButton("X")
        bd.setFixedSize(24, 24)
        bd.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; border-radius: 3px;")
        bd.clicked.connect(lambda ck=False, p=apath, c=card: [p.unlink(missing_ok=True), c.deleteLater()])
        cl.addWidget(bd)
        self._browser_layout.addWidget(card)

    def _close_browser(self):
        if hasattr(self, '_browser') and self._browser:
            self._browser.deleteLater()
            self._browser = None
        self._display.show()
        self._progress_container.show()
        self._info.show()
        self._show_play_button()

    def _add_video_to_tl(self, vpath):
        from makevid.core.timeline import get_video_duration
        from makevid.config import PROJECTS_DIR
        dur = get_video_duration(str(vpath)) or 5.0
        clip = self.project.add_clip(prompt=vpath.stem, position=len(self.project.clips))
        clip.video_path = str(vpath)
        clip.duration = dur
        clip.status = "done"
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

    def _add_audio_to_tl(self, path, dur):
        from makevid.config import PROJECTS_DIR
        existing = self.project.get_track_items("audio")
        start = max((i.start_time + i.duration for i in existing), default=self.timeline.playhead_pos)
        self.project.add_track_item(name=path.stem[:20], track="audio", start_time=start, duration=dur or 5.0, file_path=str(path))
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()

    def _play_audio_file(self, path):
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
            data, sr = sf.read(str(path), dtype="float32")
            sd.stop()
            sd.play(np.ascontiguousarray(data), samplerate=sr)
        except Exception:
            pass

    def _rename_video(self, vpath, new_name):
        from makevid.config import PROJECTS_DIR
        new_name = new_name.strip()
        if not new_name or new_name == vpath.stem:
            return
        new_path = vpath.parent / f"{new_name}{vpath.suffix}"
        if not new_path.exists():
            vpath.rename(new_path)
            for clip in self.project.clips:
                if clip.video_path == str(vpath):
                    clip.video_path = str(new_path)
            self.project.save(PROJECTS_DIR)

    def _browser_import_video(self):
        from PySide6.QtWidgets import QFileDialog
        from makevid.config import OUTPUTS_DIR
        import shutil
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Video", "", "Video (*.mp4 *.avi *.mov *.mkv)")
        for p in paths:
            src = Path(p)
            dest = OUTPUTS_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self._close_browser()
        self.show_video_browser()

    def _browser_clean_videos(self):
        from makevid.config import OUTPUTS_DIR
        used = {str(Path(c.video_path).resolve()) for c in self.project.clips if c.video_path}
        out_dir = OUTPUTS_DIR / self.project.id
        if out_dir.exists():
            for f in out_dir.rglob("*.mp4"):
                if str(f.resolve()) not in used:
                    f.unlink(missing_ok=True)
        self._close_browser()
        self.show_video_browser()

    def _browser_clean_audios(self):
        from makevid.config import AUDIO_DIR
        used = {str(Path(i.file_path).resolve()) for i in self.project.track_items if i.file_path}
        audio_dir = AUDIO_DIR / self.project.id
        if audio_dir.exists():
            for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac"):
                for f in audio_dir.rglob(ext):
                    if str(f.resolve()) not in used:
                        f.unlink(missing_ok=True)
        self._close_browser()
        self.show_audio_browser()

    def show_clip_properties(self, clip):
        """Mostra painel lateral de propriedades sobre o display (replica do tkinter ClipProperties)."""
        self._hide_clip_properties()
        self._current_clip = clip
        from PySide6.QtWidgets import (
            QFrame, QPushButton, QGridLayout, QScrollArea, QLineEdit,
            QVBoxLayout as VL, QHBoxLayout as HL
        )
        from PySide6.QtCore import Qt as QtC
        from pathlib import Path as P

        self._props_panel = QFrame(self._display)
        self._props_panel.setFixedWidth(230)
        self._props_panel.setStyleSheet(
            f"background: {C['panel']}; border: 1px solid {C['gold']}; border-radius: 6px;")
        pl = VL(self._props_panel)
        pl.setContentsMargins(6, 6, 6, 6)
        pl.setSpacing(0)

        # Header
        hdr = HL()
        lbl = QLabel(f"CLIP #{clip.position+1}")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 11pt; font-weight: bold; border: none;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        btn_x = QPushButton("X")
        btn_x.setFixedSize(20, 18)
        btn_x.setStyleSheet(f"background: transparent; color: {C['text3']}; border: none;")
        btn_x.clicked.connect(self._hide_clip_properties)
        hdr.addWidget(btn_x)
        pl.addLayout(hdr)

        # Separador gold
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background: {C['gold']}; border: none;")
        pl.addWidget(sep)

        # Scroll com conteudo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtC.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        sc = QWidget()
        sl = VL(sc)
        sl.setContentsMargins(6, 6, 6, 6)
        sl.setSpacing(4)

        # DESCRICAO (editavel)
        sl.addWidget(self._prop_lbl("DESCRICAO"))
        from PySide6.QtWidgets import QTextEdit
        self._props_desc = QTextEdit()
        self._props_desc.setPlainText(clip.prompt or "")
        self._props_desc.setFixedHeight(60)
        self._props_desc.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['gold']}; "
            f"border-radius: 4px; padding: 3px; font-size: 9pt;")
        self._props_desc.textChanged.connect(self._save_clip_desc)
        sl.addWidget(self._props_desc)

        sl.addWidget(self._prop_sep())

        # PROPRIEDADES
        def prop_row(label, value, color=C['text']):
            r = HL()
            la = QLabel(label)
            la.setFixedWidth(60)
            la.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; font-weight: bold; border: none;")
            r.addWidget(la)
            va = QLabel(str(value))
            va.setStyleSheet(f"color: {color}; font-family: Consolas; font-size: 10pt; font-weight: bold; border: none;")
            r.addWidget(va)
            r.addStretch()
            sl.addLayout(r)

        prop_row("Duracao", f"{clip.duration:.1f}s", C['cyan'])
        prop_row("Status", clip.status.upper(), C['cyan'] if clip.status == 'done' else C['gold'])
        prop_row("Seed", clip.seed or "random")
        if clip.video_path:
            vp = P(clip.video_path)
            if vp.exists():
                prop_row("Tamanho", f"{vp.stat().st_size / 1e6:.1f} MB")

        sl.addWidget(self._prop_sep())

        # TITULO editavel
        sl.addWidget(self._prop_lbl("TITULO"))
        self._props_title = QLineEdit(clip.prompt or "")
        self._props_title.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['gold']}; "
            f"border-radius: 4px; padding: 3px; font-size: 10pt; font-weight: bold;")
        self._props_title.returnPressed.connect(self._save_clip_title)
        sl.addWidget(self._props_title)

        sl.addWidget(self._prop_sep())

        # ACOES
        sl.addWidget(self._prop_lbl("ACOES"))
        grid = QFrame()
        grid.setStyleSheet("border: none;")
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 4, 0, 0)
        gl.setSpacing(3)

        def bstyle(c2):
            return (f"background: {C['card']}; color: {c2}; font-weight: bold; font-size: 9pt; "
                    f"border: 1px solid {c2}; border-radius: 4px; padding: 4px;")

        b1 = QPushButton("\u27f3 REGERAR")
        b1.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-weight: bold; font-size: 9pt; border-radius: 4px; padding: 4px;")
        b1.clicked.connect(lambda: self._clip_action("regenerate"))
        gl.addWidget(b1, 0, 0)

        b2 = QPushButton("\u29c9 DUPLICAR")
        b2.setStyleSheet(bstyle(C['cyan']))
        b2.clicked.connect(lambda: self._clip_action("duplicate"))
        gl.addWidget(b2, 0, 1)

        b3 = QPushButton("\u2702 DIVIDIR")
        b3.setStyleSheet(bstyle(C['purple']))
        b3.clicked.connect(lambda: self._clip_action("split"))
        gl.addWidget(b3, 1, 0)

        b4 = QPushButton("\u2715 REMOVER")
        b4.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; font-size: 9pt; border: 1px solid #ff4444; border-radius: 4px; padding: 4px;")
        b4.clicked.connect(lambda: self._clip_action("delete"))
        gl.addWidget(b4, 1, 1)

        b5 = QPushButton("\u2b06 REFINAR")
        b5.setStyleSheet(bstyle("#44cc88"))
        b5.clicked.connect(lambda: self._clip_action("upscale"))
        gl.addWidget(b5, 2, 0)

        b6 = QPushButton("\U0001f464 FACE SWAP")
        b6.setStyleSheet(bstyle("#ff9944"))
        b6.clicked.connect(lambda: self._clip_action("faceswap"))
        gl.addWidget(b6, 2, 1)

        b7 = QPushButton("\u270f EDITAR")
        b7.setStyleSheet(bstyle(C['cyan']))
        b7.clicked.connect(lambda: self._clip_action("inpaint"))
        gl.addWidget(b7, 3, 0, 1, 2)

        sl.addWidget(grid)
        sl.addStretch()
        scroll.setWidget(sc)
        pl.addWidget(scroll)

        # Posicionar: lateral direita, 95% da altura (igual tkinter relheight=0.95)
        panel_h = int(self._display.height() * 0.95)
        self._props_panel.setFixedHeight(max(200, panel_h))
        self._props_panel.move(max(0, self._display.width() - 235), 5)
        self._props_panel.show()

    def _prop_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        return l

    def _prop_sep(self):
        from PySide6.QtWidgets import QFrame
        s = QFrame()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background: {C['border']}; border: none;")
        return s

    def _save_clip_title(self):
        clip = getattr(self, '_current_clip', None)
        if clip and hasattr(self, '_props_title'):
            new = self._props_title.text().strip()
            if new and new != clip.prompt:
                clip.prompt = new
                from makevid.config import PROJECTS_DIR
                self.project.save(PROJECTS_DIR)
                self.timeline.redraw()

    def _save_clip_desc(self):
        clip = getattr(self, '_current_clip', None)
        if clip and hasattr(self, '_props_desc'):
            new = self._props_desc.toPlainText().strip()
            if new != clip.prompt:
                clip.prompt = new
                from makevid.config import PROJECTS_DIR
                self.project.save(PROJECTS_DIR)

    def _hide_clip_properties(self):
        if hasattr(self, '_props_panel') and self._props_panel:
            self._props_panel.deleteLater()
            self._props_panel = None

    def _clip_action(self, action):
        clip = getattr(self, '_current_clip', None)
        if not clip:
            return
        app = self.window()
        app._selected_clip = clip
        if action == "regenerate":
            app._regenerate_clip()
        elif action == "duplicate":
            app._duplicate_clip()
        elif action == "split":
            app._split_clip_at_playhead()
        elif action == "delete":
            from makevid.config import PROJECTS_DIR
            app.project.remove_clip(clip.id)
            app.project.save(PROJECTS_DIR)
            app.timeline.redraw()
        elif action == "upscale":
            pass  # TODO: integrar UpscaleService
        elif action == "faceswap":
            pass  # TODO: integrar FaceSwapService
        elif action == "inpaint":
            app._show_inpaint()
        self._hide_clip_properties()
