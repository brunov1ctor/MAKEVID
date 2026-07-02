"""export_actions — exportação e logs."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QDialogButtonBox, QFormLayout,
)
from PySide6.QtCore import QTimer

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR


class ExportActionsMixin:

    def _export_game_engine(self):
        from makevid.core.export import PRESETS, RESOLUTIONS, FPS_OPTIONS, export_video

        dlg = QDialog(self)
        dlg.setWindowTitle("Export Game Engine")
        dlg.setStyleSheet(f"background: {C['panel']}; color: {C['text']};")
        form = QFormLayout(dlg)

        preset_cb = QComboBox()
        preset_cb.addItems([p["label"] for p in PRESETS.values()])
        form.addRow("Preset:", preset_cb)

        res_cb = QComboBox()
        res_cb.addItems(list(RESOLUTIONS.keys()))
        res_cb.setCurrentText("1080p")
        form.addRow("Resolucao:", res_cb)

        fps_cb = QComboBox()
        fps_cb.addItems([str(f) for f in FPS_OPTIONS])
        fps_cb.setCurrentText("30")
        form.addRow("FPS:", fps_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() != QDialog.Accepted:
            return

        from makevid.core.export import get_preset_key
        resolution = RESOLUTIONS.get(res_cb.currentText(), (1920, 1080)) or (1920, 1080)
        clips = sorted(self.project.clips, key=lambda c: c.position)
        source = next((c.video_path for c in clips if c.video_path and Path(c.video_path).exists()), None)
        if not source:
            return
        try:
            result = export_video(
                source, Path.home() / "Downloads", self.project.name or "export",
                preset=get_preset_key(preset_cb.currentText()),
                resolution=resolution, fps=int(fps_cb.currentText()),
            )
            self.generator._status.setText(f"Exportado: {result.name}")
        except Exception as e:
            self.generator._status.setText(f"Erro export: {str(e)[:40]}")

    def _open_logs(self):
        from makevid.core.logger import get_log_content, clear_logs

        dlg = QDialog(self)
        dlg.setWindowTitle("Logs - MAKEVID")
        dlg.resize(750, 450)
        dlg.setStyleSheet(f"background: {C['panel']}; color: {C['text']};")
        layout = QVBoxLayout(dlg)

        hdr = QHBoxLayout()
        lbl = QLabel("LOGS")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        filter_cb = QComboBox()
        filter_cb.addItems(["Todos", "Erros", "Audio", "Export", "Clip", "Geracao"])
        filter_cb.setStyleSheet(
            f"background: {C['card']}; color: {C['text']}; border: 1px solid {C['purple']};"
            " border-radius: 3px; padding: 2px 8px;"
        )
        hdr.addWidget(filter_cb)
        layout.addLayout(hdr)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet(
            f"background: #0a0c14; color: #88cc88; font-family: Consolas;"
            f" font-size: 9pt; border: 1px solid {C['border']};"
        )
        layout.addWidget(txt)

        _filters = {
            "Erros":   lambda l: "ERROR" in l or "FALHA" in l or "Erro" in l,
            "Audio":   lambda l: any(k in l.lower() for k in ("audio", "sound", "tts")),
            "Export":  lambda l: "export" in l.lower(),
            "Clip":    lambda l: "clip" in l.lower(),
            "Geracao": lambda l: "gen" in l.lower() or "INICIO" in l or "OK [" in l,
        }

        def refresh():
            content = get_log_content(500)
            f = filter_cb.currentText()
            if f in _filters:
                content = "\n".join(l for l in content.split("\n") if _filters[f](l))
            txt.setPlainText(content or "(nenhum log para este filtro)")

        refresh()
        filter_cb.currentTextChanged.connect(lambda _: refresh())

        btn_row = QHBoxLayout()
        btn_r = QPushButton("Atualizar")
        btn_r.setStyleSheet(
            f"background: {C['card']}; color: {C['text2']}; border: 1px solid {C['border']};"
            " border-radius: 4px; padding: 4px 10px;"
        )
        btn_r.clicked.connect(refresh)
        btn_row.addWidget(btn_r)
        btn_c = QPushButton("Limpar Logs")
        btn_c.setStyleSheet(
            "background: #2a0808; color: #ff4444; font-weight: bold;"
            " border: 1px solid #ff4444; border-radius: 4px; padding: 4px 10px;"
        )
        btn_c.clicked.connect(lambda: [clear_logs(), refresh()])
        btn_row.addWidget(btn_c)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        dlg.exec()
