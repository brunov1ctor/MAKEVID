"""Browser Panel Qt - Meus Videos e Meus Audios."""

import time as _time
import shutil
import random
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen

from makevid.qt.theme import C
from makevid.config import OUTPUTS_DIR, AUDIO_DIR, PROJECTS_DIR


# ── Stylesheet dos cards — definido no QFrame para ter precedência sobre o tema global ──

BTN_ADD = (
    f"QPushButton {{ background: {C['primary']}; color: {C['text']}; "
    f"border: 1px solid {C['primary']}; border-radius: 5px; padding: 0 6px; "
    f"font-size: 8pt; font-weight: bold; }}"
    f"QPushButton:hover {{ background: {C['secondary']}; color: {C['dark']}; border-color: {C['secondary']}; }}"
)
BTN_PLAY = (
    f"QPushButton {{ background: {C['card']}; color: {C['accent']}; "
    f"border: 1px solid {C['accent']}; border-radius: 5px; "
    f"font-size: 12pt; font-weight: bold; font-family: 'Segoe UI Symbol', 'Arial Unicode MS', sans-serif; }}"
    f"QPushButton:hover {{ background: {C['accent']}; color: {C['dark']}; }}"
)
BTN_RENAME = (
    f"QPushButton {{ background: {C['card']}; color: {C['warning']}; "
    f"border: 1px solid {C['warning']}; border-radius: 5px; "
    f"font-size: 11pt; font-weight: bold; }}"
    f"QPushButton:hover {{ background: {C['warning']}; color: {C['dark']}; }}"
)
BTN_DELETE = (
    f"QPushButton {{ background: {C['danger_bg']}; color: {C['danger']}; "
    f"border: 1px solid {C['danger']}; border-radius: 5px; padding: 0 6px; "
    f"font-size: 8pt; font-weight: bold; }}"
    f"QPushButton:hover {{ background: {C['danger']}; color: {C['dark']}; }}"
)


def _card_ss(accent):
    return (
        f"#card {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 6px; }}"
        f"#card:hover {{ background: {C['card_hover']}; border-color: {accent}; }}"
        f"#card QLabel {{ background: transparent; border: none; color: {C['text']}; }}"
    )


# ── Cards ─────────────────────────────────────────────────────────────────────

class VideoCard(QWidget):
    add_requested    = Signal(Path)
    delete_requested = Signal()

    def __init__(self, vpath: Path, parent=None):
        super().__init__(parent)
        self._path = vpath
        self.setObjectName("card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(_card_ss(C['primary']))
        self.setCursor(Qt.ArrowCursor)
        self._build()

    def _build(self):
        cl = QHBoxLayout(self)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.setSpacing(8)

        # Thumbnail
        try:
            import cv2
            cap = cv2.VideoCapture(str(self._path))
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame_rgb = frame[:, :, ::-1].copy()
                h, w = frame_rgb.shape[:2]
                th, tw = 50, 90
                img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)
                pix = QPixmap.fromImage(img).scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                if pix.width() > tw or pix.height() > th:
                    pix = pix.copy((pix.width() - tw) // 2, (pix.height() - th) // 2, tw, th)
                thumb = QLabel()
                thumb.setPixmap(pix)
                thumb.setFixedSize(tw, th)
                cl.addWidget(thumb)
        except Exception:
            pass

        info = QVBoxLayout()
        info.setSpacing(2)

        name_row = QHBoxLayout()
        name_row.setSpacing(4)
        self._name_lbl = QLabel(self._path.stem[:28])
        self._name_lbl.setStyleSheet("font-size: 9pt; font-weight: bold;")
        self._name_edit = QLineEdit(self._path.stem)
        self._name_edit.setFixedHeight(20)
        self._name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 9pt; font-weight: bold; "
            f"border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 4px;")
        self._name_edit.hide()
        name_row.addWidget(self._name_lbl)
        name_row.addWidget(self._name_edit)
        name_row.addStretch()
        info.addLayout(name_row)

        size_mb = self._path.stat().st_size / 1e6
        mtime = _time.strftime("%d/%m %H:%M", _time.localtime(self._path.stat().st_mtime))
        meta = QLabel(f"{size_mb:.1f} MB | {mtime}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt;")
        info.addWidget(meta)

        btns = QHBoxLayout()
        btns.setSpacing(4)

        self._btn_add = QPushButton("+ Timeline")
        self._btn_add.setFixedHeight(22)
        self._btn_add.setStyleSheet(BTN_ADD)
        self._btn_add.clicked.connect(lambda: self.add_requested.emit(self._path))

        self._btn_rename = QPushButton("✏")
        self._btn_rename.setFixedSize(26, 22)
        self._btn_rename.setStyleSheet(BTN_RENAME)
        self._btn_rename.setToolTip("Renomear")

        self._btn_del = QPushButton("Deletar")
        self._btn_del.setFixedHeight(22)
        self._btn_del.setStyleSheet(BTN_DELETE)
        self._btn_del.clicked.connect(self.delete_requested.emit)

        btns.addWidget(self._btn_add)
        btns.addWidget(self._btn_rename)
        btns.addWidget(self._btn_del)
        btns.addStretch()
        info.addLayout(btns)
        cl.addLayout(info)

        self._btn_rename.clicked.connect(self._toggle_rename)
        self._name_edit.returnPressed.connect(self._confirm_rename)
        self._name_edit.editingFinished.connect(
            lambda: self._confirm_rename() if not self._name_edit.isHidden() else None)

    def _toggle_rename(self):
        if self._name_edit.isHidden():
            self._name_edit.setText(self._path.stem)
            self._name_lbl.hide()
            self._name_edit.show()
            self._name_edit.setFocus()
            self._name_edit.selectAll()
            self._btn_rename.setText("✔")
        else:
            self._confirm_rename()

    def _confirm_rename(self):
        new_name = self._name_edit.text().strip()
        if new_name and new_name != self._path.stem:
            new_path = self._path.with_name(new_name + self._path.suffix)
            try:
                self._path.rename(new_path)
                self._name_lbl.setText(new_name[:28])
                self._path = new_path
            except Exception as e:
                print(f"[VideoCard] rename error: {e}")
        self._name_edit.hide()
        self._name_lbl.show()
        self._btn_rename.setText("✏")

    @property
    def path(self):
        return self._path


# ── Waveform ──────────────────────────────────────────────────────────────────

class WaveformWidget(QWidget):
    """Faixa de onda + playhead animado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setMinimumWidth(10)
        self.setObjectName("waveformWidget")
        self._progress = 0.0
        random.seed(42)
        self._bars = [random.uniform(0.15, 1.0) for _ in range(60)]

    def set_progress(self, v: float):
        self._progress = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        bg = QColor(C['card'])
        p.fillRect(0, 0, w, h, bg)
        n = len(self._bars)
        gap = 1
        bar_w = max(1.0, (w / n) - gap)
        cx = w * self._progress
        accent = QColor(C['accent'])
        dim = QColor(C['border'])
        for i, amp in enumerate(self._bars):
            x = i * (w / n)
            bh = max(2.0, amp * (h - 6))
            y = (h - bh) / 2
            p.setPen(Qt.NoPen)
            p.setBrush(accent if x <= cx else dim)
            p.drawRoundedRect(int(x), int(y), max(1, int(bar_w)), int(bh), 1, 1)
        if self._progress > 0:
            p.setPen(QPen(QColor("white"), 1))
            p.drawLine(int(cx), 0, int(cx), h)
        p.end()


# ── AudioCard ─────────────────────────────────────────────────────────────────

class AudioCard(QWidget):
    add_requested    = Signal(Path, float)
    delete_requested = Signal()

    def __init__(self, apath: Path, parent=None):
        super().__init__(parent)
        self._path = apath
        self._dur  = 0.0
        self._player = None
        self._audio_out = None
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._update_playhead)
        self.setObjectName("card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(_card_ss(C['accent']))
        self.setCursor(Qt.ArrowCursor)
        self._build()

    def _build(self):
        cl = QVBoxLayout(self)
        cl.setContentsMargins(6, 6, 6, 6)
        cl.setSpacing(3)

        # Linha 1: nome + meta
        top = QHBoxLayout()
        top.setSpacing(4)
        self._name_lbl = QLabel(self._path.stem[:30])
        self._name_lbl.setStyleSheet("font-size: 9pt; font-weight: bold;")
        self._name_edit = QLineEdit(self._path.stem)
        self._name_edit.setFixedHeight(20)
        self._name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 9pt; font-weight: bold; "
            f"border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 4px;")
        self._name_edit.hide()
        top.addWidget(self._name_lbl)
        top.addWidget(self._name_edit)
        top.addStretch()

        try:
            from makevid.core.audio_utils import get_audio_duration
            self._dur = get_audio_duration(str(self._path)) or 0.0
        except Exception:
            pass

        size_kb = self._path.stat().st_size / 1024
        mtime = _time.strftime("%d/%m %H:%M", _time.localtime(self._path.stat().st_mtime))
        meta = QLabel(f"{self._dur:.1f}s | {size_kb:.0f}KB | {mtime}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt;")
        top.addWidget(meta)
        cl.addLayout(top)

        # Linha 2: waveform
        self._waveform = WaveformWidget()
        cl.addWidget(self._waveform)

        # Linha 3: botões
        btns = QHBoxLayout()
        btns.setSpacing(4)
        btns.setContentsMargins(0, 2, 0, 0)

        self._btn_play = QPushButton("▶")
        self._btn_play.setObjectName("btnPlay")
        self._btn_play.setFixedSize(30, 24)
        self._btn_play.setStyleSheet(BTN_PLAY)
        self._btn_play.setToolTip("Ouvir")
        self._btn_play.clicked.connect(self._toggle_play)

        self._btn_add = QPushButton("+ Timeline")
        self._btn_add.setFixedHeight(22)
        self._btn_add.setStyleSheet(BTN_ADD)
        self._btn_add.clicked.connect(lambda: self.add_requested.emit(self._path, self._dur))

        self._btn_rename = QPushButton("✏")
        self._btn_rename.setFixedSize(26, 22)
        self._btn_rename.setStyleSheet(BTN_RENAME)
        self._btn_rename.setToolTip("Renomear")

        self._btn_del = QPushButton("✕")
        self._btn_del.setFixedSize(26, 22)
        self._btn_del.setStyleSheet(BTN_DELETE)
        self._btn_del.clicked.connect(self.delete_requested.emit)

        btns.addWidget(self._btn_play)
        btns.addWidget(self._btn_add)
        btns.addWidget(self._btn_rename)
        btns.addWidget(self._btn_del)
        btns.addStretch()
        cl.addLayout(btns)

        self._btn_rename.clicked.connect(self._toggle_rename)
        self._name_edit.returnPressed.connect(self._confirm_rename)
        self._name_edit.editingFinished.connect(
            lambda: self._confirm_rename() if not self._name_edit.isHidden() else None)

    def _toggle_play(self):
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            if self._player is None:
                self._player = QMediaPlayer()
                self._audio_out = QAudioOutput()
                self._player.setAudioOutput(self._audio_out)
                self._audio_out.setVolume(1.0)
                self._player.playbackStateChanged.connect(self._on_state_changed)
            if self._player.playbackState() == QMediaPlayer.PlayingState:
                self._player.pause()
            else:
                if self._player.playbackState() != QMediaPlayer.PausedState:
                    self._player.setSource(QUrl.fromLocalFile(str(self._path)))
                self._player.play()
        except Exception as e:
            print(f"[AudioCard] play error: {e}")

    def _on_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlayingState:
            self._btn_play.setText("⏸")
            self._timer.start()
        else:
            self._btn_play.setText("▶")
            self._timer.stop()
            if state == QMediaPlayer.StoppedState:
                self._waveform.set_progress(0.0)

    def _update_playhead(self):
        if self._player and self._dur > 0:
            self._waveform.set_progress(self._player.position() / (self._dur * 1000))

    def _toggle_rename(self):
        if self._name_edit.isHidden():
            self._name_edit.setText(self._path.stem)
            self._name_lbl.hide()
            self._name_edit.show()
            self._name_edit.setFocus()
            self._name_edit.selectAll()
            self._btn_rename.setText("✔")
        else:
            self._confirm_rename()

    def _confirm_rename(self):
        new_name = self._name_edit.text().strip()
        if new_name and new_name != self._path.stem:
            new_path = self._path.with_name(new_name + self._path.suffix)
            try:
                self._path.rename(new_path)
                self._name_lbl.setText(new_name[:30])
                self._path = new_path
            except Exception as e:
                print(f"[AudioCard] rename error: {e}")
        self._name_edit.hide()
        self._name_lbl.show()
        self._btn_rename.setText("✏")

    def closeEvent(self, event):
        self._timer.stop()
        if self._player:
            self._player.stop()
        super().closeEvent(event)

    @property
    def path(self):
        return self._path


# ── Painéis ───────────────────────────────────────────────────────────────────

class VideoBrowserPanel(QWidget):
    closed      = Signal()
    video_added = Signal()

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background: {C['glass']}; border-bottom: 1px solid {C['border']};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 10, 0)
        hl.setSpacing(6)

        lbl = QLabel("MEUS VIDEOS")
        lbl.setStyleSheet(f"color: {C['primary']}; font-size: 11pt; font-weight: bold;")
        hl.addWidget(lbl)
        hl.addStretch()

        for text, slot in [("+ Importar", self._import_video), ("Limpar Inutilizados", self._remove_unused)]:
            b = QPushButton(text)
            b.setFixedHeight(22)
            b.clicked.connect(slot)
            hl.addWidget(b)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.closed.emit)
        hl.addWidget(close_btn)
        layout.addWidget(hdr)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none;")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(4)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self.refresh()

    def refresh(self):
        L = self._content_layout
        while L.count():
            child = L.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        videos = sorted(OUTPUTS_DIR.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not videos:
            L.addWidget(QLabel("Nenhum video encontrado."))
            return

        for vpath in videos:
            card = VideoCard(vpath)
            card.add_requested.connect(self._add_to_timeline)
            card.delete_requested.connect(lambda c=card: self._delete(c))
            L.addWidget(card)
        L.addStretch()

    def _add_to_timeline(self, vpath):
        from makevid.core.timeline import get_video_duration
        dur = get_video_duration(vpath) or 5.0
        clip = self.project.add_clip(prompt=vpath.stem, position=len(self.project.clips))
        clip.video_path = str(vpath)
        clip.duration = dur
        clip.status = "done"
        for c in self.project.clips:
            if c.video_path and Path(c.video_path).resolve() == vpath.resolve():
                c.video_path = str(vpath)
        self.project.save(PROJECTS_DIR)
        self.video_added.emit()

    def _delete(self, card):
        try:
            card.path.unlink()
        except Exception:
            pass
        card.deleteLater()

    def _import_video(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Importar Video", "", "Video (*.mp4 *.avi *.mov *.mkv *.webm)")
        if not paths:
            return
        for p in paths:
            src = Path(p)
            dest = OUTPUTS_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self.refresh()

    def _remove_unused(self):
        used = {str(Path(c.video_path).resolve()) for c in self.project.clips if c.video_path}
        current_output = OUTPUTS_DIR / self.project.id
        if current_output.exists():
            for f in current_output.rglob("*.mp4"):
                if str(f.resolve()) not in used:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        self.refresh()


class AudioBrowserPanel(QWidget):
    closed      = Signal()
    audio_added = Signal()

    def __init__(self, project, timeline, parent=None):
        super().__init__(parent)
        self.project  = project
        self.timeline = timeline
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background: {C['glass']}; border-bottom: 1px solid {C['border']};")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 10, 0)
        hl.setSpacing(6)

        lbl = QLabel("MEUS AUDIOS")
        lbl.setStyleSheet(f"color: {C['accent']}; font-size: 11pt; font-weight: bold;")
        hl.addWidget(lbl)
        hl.addStretch()

        for text, slot in [("+ Importar", self._import_audio), ("Limpar Inutilizados", self._remove_unused)]:
            b = QPushButton(text)
            b.setFixedHeight(22)
            b.clicked.connect(slot)
            hl.addWidget(b)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.closed.emit)
        hl.addWidget(close_btn)
        layout.addWidget(hdr)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none;")
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(4)
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self.refresh()

    def refresh(self):
        L = self._content_layout
        while L.count():
            child = L.takeAt(0)
            w = child.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        audios = sorted(
            [f for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac") for f in AUDIO_DIR.rglob(ext)],
            key=lambda p: p.stat().st_mtime, reverse=True)

        if not audios:
            L.addWidget(QLabel("Nenhum audio."))
            return

        for apath in audios:
            card = AudioCard(apath)
            card.add_requested.connect(self._add_to_timeline)
            card.delete_requested.connect(lambda c=card: self._delete(c))
            L.addWidget(card)
        L.addStretch()
        self._content.update()

    def _add_to_timeline(self, path, dur):
        existing = self.project.get_track_items("audio")
        if existing:
            last = max(existing, key=lambda i: i.start_time + i.duration)
            start = last.start_time + last.duration
        else:
            start = self.timeline.playhead_pos
        self.project.add_track_item(
            name=path.stem[:20], track="audio",
            start_time=start, duration=dur or 5.0, file_path=str(path))
        for item in self.project.track_items:
            if item.file_path and Path(item.file_path).resolve() == path.resolve():
                item.file_path = str(path)
        self.project.save(PROJECTS_DIR)
        self.audio_added.emit()

    def _delete(self, card):
        try:
            card.path.unlink()
        except Exception:
            pass
        card.deleteLater()

    def _import_audio(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Importar Audio", "", "Audio (*.wav *.mp3 *.ogg *.flac)")
        if not paths:
            return
        for p in paths:
            src = Path(p)
            dest = AUDIO_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self.refresh()

    def _remove_unused(self):
        used = {str(Path(item.file_path).resolve()) for item in self.project.track_items if item.file_path}
        audio_dir = AUDIO_DIR / self.project.id
        if audio_dir.exists():
            for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac"):
                for f in audio_dir.rglob(ext):
                    if str(f.resolve()) not in used:
                        try:
                            f.unlink()
                        except Exception:
                            pass
        self.refresh()
