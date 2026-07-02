"""media_browser — navegador de vídeos e áudios dentro do preview."""

import shutil
import time as _time
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QImage, QPixmap

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, OUTPUTS_DIR, AUDIO_DIR


class MediaBrowserMixin:
    """Mixin para PreviewWidget: browsers de vídeo e áudio."""

    # ── helpers ──────────────────────────────────────────────────────────────

    def _hide_display(self):
        if self.player.is_playing:
            self.player.stop()
        self._display.hide()
        self._progress_container.hide()
        self._info.hide()
        if getattr(self, "_browser", None):
            self._browser.hide()
            self._browser.deleteLater()
            self._browser = None

    def _close_browser(self):
        if getattr(self, "_browser", None):
            self._browser.hide()
            self._browser.deleteLater()
            self._browser = None
        self._display.show()
        self._progress_container.show()
        self._info.show()
        self._show_play_button()

    def _show_browser(self, title, accent, files, build_card_fn, import_fn, clean_fn):
        self._hide_display()

        browser = QFrame(self)
        browser.setObjectName("browserFrame")
        browser.setStyleSheet(
            f"QFrame#browserFrame {{ background: {C['panel']}; border: 1px solid {accent}; border-radius: 4px; }}"
        )
        bl = QVBoxLayout(browser)
        bl.setContentsMargins(1, 1, 1, 1); bl.setSpacing(0)

        hdr = QFrame(); hdr.setFixedHeight(36)
        hdr.setStyleSheet(f"background: {C['card']}; border: none;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(12, 0, 8, 0); hl.setSpacing(6)
        lbl = QLabel(f"{title}  #{len(files)}")
        lbl.setStyleSheet(f"color: {accent}; font-size: 11pt; font-weight: bold; border: none;")
        hl.addWidget(lbl); hl.addStretch()
        btn_imp = QPushButton("+ Importar"); btn_imp.setFixedHeight(22)
        btn_imp.setStyleSheet(
            f"background: {C['card']}; color: {accent}; font-size: 8pt; font-weight: bold;"
            f" border: 1px solid {accent}; border-radius: 3px; padding: 0 8px;"
        )
        btn_imp.clicked.connect(import_fn); hl.addWidget(btn_imp)
        btn_clean = QPushButton("Limpar Inutilizados"); btn_clean.setFixedHeight(22)
        btn_clean.setStyleSheet(
            "background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold;"
            " border: 1px solid #ff4444; border-radius: 3px; padding: 0 8px;"
        )
        btn_clean.clicked.connect(clean_fn); hl.addWidget(btn_clean)
        btn_x = QPushButton("\u2715"); btn_x.setFixedSize(28, 22)
        btn_x.setObjectName("closeBtn"); btn_x.clicked.connect(self._close_browser)
        hl.addWidget(btn_x)
        bl.addWidget(hdr)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C['panel']}; border: none; }}")
        sc = QWidget(); sc.setStyleSheet(f"background: {C['panel']};")
        self._browser_layout = QVBoxLayout(sc)
        self._browser_layout.setContentsMargins(8, 8, 8, 8); self._browser_layout.setSpacing(6)
        scroll.setWidget(sc); bl.addWidget(scroll)

        if not files:
            empty = QLabel("Nenhum arquivo encontrado.")
            empty.setStyleSheet(f"color: {C['text3']}; font-size: 10pt; padding: 12px;")
            self._browser_layout.addWidget(empty)
        else:
            for f in files:
                build_card_fn(f)
        self._browser_layout.addStretch()
        self.layout().insertWidget(0, browser, stretch=1)
        browser.show()
        self._browser = browser

    # ── video browser ─────────────────────────────────────────────────────────

    def show_video_browser(self):
        proj_dir = OUTPUTS_DIR / self.project.id
        files = sorted(proj_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True) if proj_dir.exists() else []
        self._show_browser(
            title="MEUS VIDEOS", accent=C["gold"], files=files,
            build_card_fn=self._build_browser_video_card,
            import_fn=self._browser_import_video,
            clean_fn=self._browser_clean_videos,
        )

    def _build_browser_video_card(self, vpath):
        _path = [vpath]
        card = QFrame()
        card.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = QHBoxLayout(card); cl.setContentsMargins(6, 6, 6, 6); cl.setSpacing(8)

        try:
            import cv2
            cap = cv2.VideoCapture(str(vpath))
            ret, frame = cap.read(); cap.release()
            if ret:
                rgb = frame[:, :, ::-1].copy()
                h, w = rgb.shape[:2]
                img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
                pm = QPixmap.fromImage(img).scaled(120, 68, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                if pm.width() > 120 or pm.height() > 68:
                    pm = pm.copy((pm.width() - 120) // 2, (pm.height() - 68) // 2, 120, 68)
                th = QLabel(); th.setPixmap(pm); th.setFixedSize(120, 68)
                cl.addWidget(th)
        except Exception:
            pass

        info = QVBoxLayout(); info.setSpacing(2)
        name_row = QHBoxLayout(); name_row.setSpacing(4)
        name_lbl = QLabel(vpath.stem[:30])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none;")
        name_edit = QLineEdit(vpath.stem); name_edit.setFixedHeight(20)
        name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 9pt; font-weight: bold;"
            f" border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 4px;"
        )
        name_edit.hide()
        name_row.addWidget(name_lbl); name_row.addWidget(name_edit); name_row.addStretch()
        info.addLayout(name_row)

        sz = vpath.stat().st_size / 1e6
        mt = _time.strftime("%d/%m %H:%M", _time.localtime(vpath.stat().st_mtime))
        meta = QLabel(f"{sz:.1f} MB | {mt}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 9pt; border: none;")
        info.addWidget(meta)

        btns = QHBoxLayout(); btns.setSpacing(4)
        br = QPushButton("Renomear"); br.setFixedHeight(22)
        br.setStyleSheet(
            f"background: {C['card']}; color: {C['warning']}; border: 1px solid {C['warning']};"
            " border-radius: 3px; font-size: 8pt; font-weight: bold; padding: 0 6px;"
        )

        def _toggle_rename():
            if name_edit.isHidden():
                name_edit.setText(_path[0].stem); name_lbl.hide(); name_edit.show()
                name_edit.setFocus(); name_edit.selectAll(); br.setText("OK")
            else:
                _confirm_rename()

        def _confirm_rename():
            new_name = name_edit.text().strip()
            if new_name and new_name != _path[0].stem:
                new_p = _path[0].with_name(new_name + _path[0].suffix)
                try:
                    _path[0].rename(new_p)
                    for c in self.project.clips:
                        if c.video_path == str(_path[0]):
                            c.video_path = str(new_p)
                    self.project.save(PROJECTS_DIR)
                    _path[0] = new_p; name_lbl.setText(new_name[:30])
                except Exception:
                    pass
            name_edit.hide(); name_lbl.show(); br.setText("Renomear")

        br.clicked.connect(_toggle_rename); name_edit.returnPressed.connect(_confirm_rename)
        btns.addWidget(br)
        ba = QPushButton("+ Timeline"); ba.setFixedHeight(22)
        ba.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 6px;")
        ba.clicked.connect(lambda: self._add_video_to_tl(_path[0])); btns.addWidget(ba)
        bd = QPushButton("Deletar"); bd.setFixedHeight(22)
        bd.setStyleSheet("background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border: 1px solid #ff4444; border-radius: 3px; padding: 0 6px;")
        bd.clicked.connect(lambda: [_path[0].unlink(missing_ok=True), card.hide(), card.deleteLater()])
        btns.addWidget(bd); btns.addStretch()
        info.addLayout(btns); cl.addLayout(info)
        self._browser_layout.addWidget(card)

    def _browser_import_video(self):
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Video", "", "Video (*.mp4 *.avi *.mov *.mkv)")
        for p in paths:
            src = Path(p); dest = OUTPUTS_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self._close_browser(); self.show_video_browser()

    def _browser_clean_videos(self):
        used = {str(Path(c.video_path).resolve()) for c in self.project.clips if c.video_path}
        out_dir = OUTPUTS_DIR / self.project.id
        if out_dir.exists():
            for f in out_dir.rglob("*.mp4"):
                if str(f.resolve()) not in used:
                    f.unlink(missing_ok=True)
        self._close_browser(); self.show_video_browser()

    def _add_video_to_tl(self, vpath):
        from makevid.core.timeline import get_video_duration
        dur = get_video_duration(str(vpath)) or 5.0
        clip = self.project.add_clip(prompt=vpath.stem, position=len(self.project.clips))
        clip.video_path = str(vpath); clip.duration = dur; clip.status = "done"
        self.project.save(PROJECTS_DIR); self.timeline.redraw()

    # ── audio browser ─────────────────────────────────────────────────────────

    def show_audio_browser(self):
        proj_audio = AUDIO_DIR / self.project.id
        files = sorted(
            [f for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac") for f in proj_audio.rglob(ext)],
            key=lambda p: p.stat().st_mtime, reverse=True,
        ) if proj_audio.exists() else []
        self._show_browser(
            title="MEUS AUDIOS", accent=C["cyan"], files=files,
            build_card_fn=self._build_browser_audio_card,
            import_fn=self._browser_import_audio,
            clean_fn=self._browser_clean_audios,
        )

    def _build_browser_audio_card(self, apath):
        from PySide6.QtGui import QPainter as _QP, QColor as _QC, QPen as _QPen

        _path = [apath]
        dur = 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            dur = get_audio_duration(str(apath)) or 0
        except Exception:
            pass

        N_BARS = 200
        _wdata = np.zeros(N_BARS, dtype=np.float32)
        try:
            import soundfile as sf
            samples, _ = sf.read(str(apath), dtype="float32")
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            chunk = max(1, len(samples) // N_BARS)
            env = np.array([float(np.abs(samples[i:i+chunk]).max()) for i in range(0, len(samples), chunk)])[:N_BARS]
            peak = max(float(env.max()), 1e-6)
            _wdata[:len(env)] = env / peak
        except Exception:
            pass

        class _Wave(QWidget):
            def __init__(self_, data):
                super().__init__(); self_.setFixedHeight(48)
                self_._data = data; self_._prog = 0.0
            def set_progress(self_, v):
                self_._prog = max(0.0, min(1.0, v)); self_.update()
            def paintEvent(self_, ev):
                p = _QP(self_); p.setRenderHint(_QP.Antialiasing, False)
                w, h = self_.width(), self_.height()
                p.fillRect(0, 0, w, h, _QC(C["dark"]))
                mid = h / 2; bar_w = max(1.0, (w - 4) / len(self_._data))
                cx = w * self_._prog
                peak = max(float(np.max(self_._data)), 0.01)
                if peak < 0.001:
                    p.setPen(_QPen(_QC(C["text3"]), 1, Qt.DashLine))
                    p.drawLine(4, int(mid), w - 4, int(mid)); p.end(); return
                cp = _QC(C["accent"]); cp.setAlpha(210)
                ci = _QC(C["text3"]); ci.setAlpha(160)
                p.setPen(Qt.NoPen)
                for i, amp in enumerate(self_._data):
                    x = int(4 + i * bar_w); bh = max(1, int((amp / peak) * (mid - 4)))
                    p.setBrush(cp if x <= cx else ci)
                    p.drawRect(x, int(mid - bh), max(1, int(bar_w) - 1), bh * 2)
                if self_._prog > 0:
                    p.setPen(_QPen(_QC("white"), 1)); p.drawLine(int(cx), 0, int(cx), h)
                p.end()

        card = QFrame()
        card.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        cl = QHBoxLayout(card); cl.setContentsMargins(6, 6, 6, 6); cl.setSpacing(6)
        info = QVBoxLayout(); info.setSpacing(2)

        name_row = QHBoxLayout(); name_row.setSpacing(4)
        name_lbl = QLabel(apath.stem[:28])
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none;")
        name_edit = QLineEdit(apath.stem); name_edit.setFixedHeight(20)
        name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 9pt; font-weight: bold;"
            f" border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 4px;"
        )
        name_edit.hide()
        name_row.addWidget(name_lbl); name_row.addWidget(name_edit); name_row.addStretch()
        info.addLayout(name_row)

        sz = apath.stat().st_size / 1024
        mt = _time.strftime("%d/%m %H:%M", _time.localtime(apath.stat().st_mtime))
        meta = QLabel(f"{dur:.1f}s | {sz:.0f}KB | {mt}")
        meta.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; border: none;")
        info.addWidget(meta)

        wave = _Wave(_wdata); info.addWidget(wave)

        btns = QHBoxLayout(); btns.setSpacing(4); btns.setContentsMargins(0, 2, 0, 0)
        _st = {"player": None, "ao": None, "timer": None}

        bp = QPushButton("▶"); bp.setFixedSize(30, 24)
        bp.setStyleSheet(
            f"background: {C['card']}; color: {C['cyan']}; border: 1px solid {C['cyan']};"
            " border-radius: 3px; font-size: 12pt; font-weight: bold;"
            " font-family: 'Segoe UI Symbol', 'Arial Unicode MS', sans-serif; padding: 0;"
        )

        def _toggle(ck=False, _bp=bp, _wave=wave, _dur=dur):
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            if _st["player"] is None:
                pl = QMediaPlayer(card); ao = QAudioOutput(card)
                pl.setAudioOutput(ao); ao.setVolume(1.0)
                t = QTimer(card); t.setInterval(80)
                _st["player"] = pl; _st["ao"] = ao; _st["timer"] = t
                def _state(s, __bp=_bp, __wave=_wave, __t=t):
                    if s == QMediaPlayer.PlayingState:
                        __bp.setText("⏸"); __t.start()
                    else:
                        __bp.setText("▶"); __t.stop()
                        if s == QMediaPlayer.StoppedState:
                            __wave.set_progress(0.0)
                pl.playbackStateChanged.connect(_state)
                t.timeout.connect(lambda __pl=pl, __w=_wave, __d=_dur:
                    __w.set_progress(__pl.position() / (__d * 1000) if __d > 0 else 0))
            pl = _st["player"]
            if pl.playbackState() == QMediaPlayer.PlayingState:
                pl.pause()
            else:
                if pl.playbackState() != QMediaPlayer.PausedState:
                    pl.setSource(QUrl.fromLocalFile(str(_path[0])))
                pl.play()

        bp.clicked.connect(_toggle); btns.addWidget(bp)

        br = QPushButton("Renomear"); br.setFixedHeight(22)
        br.setStyleSheet(
            f"background: {C['card']}; color: {C['warning']}; border: 1px solid {C['warning']};"
            " border-radius: 3px; font-size: 8pt; font-weight: bold; padding: 0 6px;"
        )

        def _toggle_rename():
            if name_edit.isHidden():
                name_edit.setText(_path[0].stem); name_lbl.hide(); name_edit.show()
                name_edit.setFocus(); name_edit.selectAll(); br.setText("OK")
            else:
                _confirm_rename()

        def _confirm_rename():
            new_name = name_edit.text().strip()
            if new_name and new_name != _path[0].stem:
                new_p = _path[0].with_name(new_name + _path[0].suffix)
                try:
                    _path[0].rename(new_p); _path[0] = new_p; name_lbl.setText(new_name[:28])
                except Exception:
                    pass
            name_edit.hide(); name_lbl.show(); br.setText("Renomear")

        br.clicked.connect(_toggle_rename); name_edit.returnPressed.connect(_confirm_rename)
        btns.addWidget(br)

        ba = QPushButton("+ Timeline"); ba.setFixedHeight(22)
        ba.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 8px;")
        ba.clicked.connect(lambda ck=False, d=dur: self._add_audio_to_tl(_path[0], d)); btns.addWidget(ba)

        def _delete_audio():
            pl = _st.get("player")
            if pl:
                pl.stop(); pl.setSource(QUrl())
            t = _st.get("timer")
            if t:
                t.stop()
            _path[0].unlink(missing_ok=True)
            card.hide(); card.deleteLater()

        bd = QPushButton("Deletar"); bd.setFixedHeight(22)
        bd.setStyleSheet("background: #2a0808; color: #ff4444; font-size: 8pt; font-weight: bold; border-radius: 3px; padding: 0 8px;")
        bd.clicked.connect(_delete_audio); btns.addWidget(bd); btns.addStretch()
        info.addLayout(btns); cl.addLayout(info)
        self._browser_layout.addWidget(card)

    def _browser_import_audio(self):
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(self, "Importar Audio", "", "Audio (*.wav *.mp3 *.ogg *.flac)")
        for p in paths:
            src = Path(p); dest = AUDIO_DIR / self.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(str(src), str(dest))
        self._close_browser(); self.show_audio_browser()

    def _browser_clean_audios(self):
        if getattr(self, "_browser", None):
            from PySide6.QtMultimedia import QMediaPlayer
            for pl in self._browser.findChildren(QMediaPlayer):
                pl.stop(); pl.setSource(QUrl())
        used = {str(Path(i.file_path).resolve()) for i in self.project.track_items if i.file_path}
        proj_audio = AUDIO_DIR / self.project.id
        if proj_audio.exists():
            for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac"):
                for f in proj_audio.rglob(ext):
                    if str(f.resolve()) not in used:
                        f.unlink(missing_ok=True)
        self._close_browser(); self.show_audio_browser()

    def _add_audio_to_tl(self, path, dur):
        existing = self.project.get_track_items("audio")
        start = max((i.start_time + i.duration for i in existing), default=self.timeline.playhead_pos)
        self.project.add_track_item(name=path.stem[:20], track="audio", start_time=start, duration=dur or 5.0, file_path=str(path))
        self.project.save(PROJECTS_DIR); self.timeline.redraw()
