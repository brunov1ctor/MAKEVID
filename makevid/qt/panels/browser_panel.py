"""Browser Panel Qt - Meus Videos e Meus Audios."""

import time as _time
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage

from makevid.qt.theme import C
from makevid.config import OUTPUTS_DIR, AUDIO_DIR, PROJECTS_DIR


class VideoBrowserPanel(QWidget):
    """Browser de videos gerados."""

    closed = Signal()
    video_added = Signal()  # emite quando video é adicionado na timeline

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setStyleSheet(f"background: {C['panel']};")
        self._thumb_refs = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background: {C['card']};")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("MEUS VIDEOS")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 11pt; font-weight: bold;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()

        btn_import = QPushButton("+ Importar")
        btn_import.setFixedHeight(22)
        btn_import.setStyleSheet(f"background: {C['card']}; color: {C['gold']}; font-size: 8pt; font-weight: bold; border: 1px solid {C['gold']}; border-radius: 3px; padding: 0 8px;")
        btn_import.clicked.connect(self._import_video)
        hdr_l.addWidget(btn_import)

        btn_clean = QPushButton("Limpar")
        btn_clean.setFixedHeight(22)
        btn_clean.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 8px;")
        btn_clean.clicked.connect(self._remove_unused)
        hdr_l.addWidget(btn_clean)

        close_btn = QPushButton("X")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        layout.addWidget(hdr)

        # Scroll
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
        """Recarrega lista de vídeos."""
        L = self._content_layout
        while L.count():
            child = L.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._thumb_refs = []

        videos = sorted(OUTPUTS_DIR.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not videos:
            L.addWidget(QLabel("Nenhum video encontrado."))
            return

        for vpath in videos:
            self._build_card(L, vpath)
        L.addStretch()

    def _build_card(self, layout, vpath):
        card = QFrame()
        card.setStyleSheet(f"background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(6, 6, 6, 6)

        # Thumbnail
        try:
            import cv2
            cap = cv2.VideoCapture(str(vpath))
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame_rgb = frame[:, :, ::-1].copy()
                h, w = frame_rgb.shape[:2]
                # Resize thumbnail
                th, tw = 50, 90
                img = QImage(frame_rgb.data, w, h, w * 3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img).scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumb_lbl = QLabel()
                thumb_lbl.setPixmap(pixmap)
                thumb_lbl.setFixedSize(tw, th)
                cl.addWidget(thumb_lbl)
        except Exception:
            pass

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(vpath.stem[:25])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none;")
        info.addWidget(name_lbl)

        size_mb = vpath.stat().st_size / 1e6
        mtime = _time.strftime("%d/%m %H:%M", _time.localtime(vpath.stat().st_mtime))
        meta = QLabel(f"{size_mb:.1f} MB | {mtime}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        info.addWidget(meta)

        # Botões
        btns = QHBoxLayout()
        btn_add = QPushButton("+ Timeline")
        btn_add.setFixedHeight(20)
        btn_add.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 6px;")
        btn_add.clicked.connect(lambda checked=False, p=vpath: self._add_to_timeline(p))
        btns.addWidget(btn_add)

        btn_del = QPushButton("Deletar")
        btn_del.setFixedHeight(20)
        btn_del.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 6px;")
        btn_del.clicked.connect(lambda checked=False, p=vpath, c=card: self._delete_video(p, c))
        btns.addWidget(btn_del)
        btns.addStretch()
        info.addLayout(btns)

        cl.addLayout(info)
        layout.addWidget(card)

    def _add_to_timeline(self, vpath):
        from makevid.core.timeline import get_video_duration
        dur = get_video_duration(vpath) or 5.0
        clip = self.project.add_clip(prompt=vpath.stem, position=len(self.project.clips))
        clip.video_path = str(vpath)
        clip.duration = dur
        clip.status = "done"
        self.project.save(PROJECTS_DIR)
        self.video_added.emit()

    def _delete_video(self, vpath, card):
        try:
            vpath.unlink()
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
        used = set()
        for c in self.project.clips:
            if c.video_path:
                used.add(str(Path(c.video_path).resolve()))

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
    """Browser de áudios gravados/importados."""

    closed = Signal()
    audio_added = Signal()

    def __init__(self, project, timeline, parent=None):
        super().__init__(parent)
        self.project = project
        self.timeline = timeline
        self.setStyleSheet(f"background: {C['panel']};")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet(f"background: {C['card']};")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("MEUS AUDIOS")
        lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 11pt; font-weight: bold;")
        hdr_l.addWidget(lbl)
        hdr_l.addStretch()

        btn_import = QPushButton("+ Importar")
        btn_import.setFixedHeight(22)
        btn_import.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-size: 8pt; font-weight: bold; border: 1px solid {C['cyan']}; border-radius: 3px; padding: 0 8px;")
        btn_import.clicked.connect(self._import_audio)
        hdr_l.addWidget(btn_import)

        btn_clean = QPushButton("Limpar")
        btn_clean.setFixedHeight(22)
        btn_clean.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 8px;")
        btn_clean.clicked.connect(self._remove_unused)
        hdr_l.addWidget(btn_clean)

        close_btn = QPushButton("X")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        layout.addWidget(hdr)

        # Scroll
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

        audios = sorted(
            [f for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac") for f in AUDIO_DIR.rglob(ext)],
            key=lambda p: p.stat().st_mtime, reverse=True)

        if not audios:
            L.addWidget(QLabel("Nenhum audio."))
            return

        for apath in audios:
            self._build_card(L, apath)
        L.addStretch()

    def _build_card(self, layout, apath):
        card = QFrame()
        card.setStyleSheet(f"background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(6, 6, 6, 6)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(apath.stem[:25])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none;")
        info.addWidget(name_lbl)

        # Duração
        dur = 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            dur = get_audio_duration(str(apath)) or 0
        except Exception:
            pass

        size_kb = apath.stat().st_size / 1024
        mtime = _time.strftime("%d/%m %H:%M", _time.localtime(apath.stat().st_mtime))
        meta = QLabel(f"{dur:.1f}s | {size_kb:.0f}KB | {mtime}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        info.addWidget(meta)
        cl.addLayout(info)

        cl.addStretch()

        # Botões
        btn_play = QPushButton("\u25b6")
        btn_play.setFixedSize(28, 24)
        btn_play.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-size: 10pt; border: 1px solid {C['cyan']}; border-radius: 3px;")
        btn_play.clicked.connect(lambda checked=False, p=apath: self._play(p))
        cl.addWidget(btn_play)

        btn_add = QPushButton("+ TL")
        btn_add.setFixedSize(40, 24)
        btn_add.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px;")
        btn_add.clicked.connect(lambda checked=False, p=apath, d=dur: self._add_to_timeline(p, d))
        cl.addWidget(btn_add)

        btn_del = QPushButton("X")
        btn_del.setFixedSize(24, 24)
        btn_del.setStyleSheet(f"background: #2a0808; color: #ff4444; font-size: 9pt; font-weight: bold; border-radius: 3px;")
        btn_del.clicked.connect(lambda checked=False, p=apath, c=card: self._delete(p, c))
        cl.addWidget(btn_del)

        layout.addWidget(card)

    def _play(self, path):
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
            data, sr = sf.read(str(path), dtype="float32")
            sd.stop()
            sd.play(np.ascontiguousarray(data), samplerate=sr)
        except Exception:
            pass

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
        self.project.save(PROJECTS_DIR)
        self.audio_added.emit()

    def _delete(self, path, card):
        try:
            path.unlink()
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
        used = set()
        for item in self.project.track_items:
            if item.file_path:
                used.add(str(Path(item.file_path).resolve()))

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
