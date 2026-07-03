"""project_actions — limpar projeto, abrir logs."""

import logging
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from makevid.config import PROJECTS_DIR
from makevid.core.logger import log_clip_action, clear_logs, get_log_content

_log = logging.getLogger("clip")


class ProjectActionsMixin:

    def _clear_project(self):
        n_clips = len(self.project.clips)
        n_items = len(self.project.track_items)
        self.project.clips.clear()
        self.project.track_items.clear()
        self.project.save(PROJECTS_DIR)
        self.timeline.redraw()
        _log.info(f"Projeto limpo: {n_clips} clips e {n_items} track items removidos")

    def _open_logs(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Logs")
        dlg.resize(800, 500)
        layout = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("background: #0d0f1a; color: #c8c8c8; font-family: Consolas; font-size: 9pt;")
        txt.setPlainText(get_log_content(500))
        layout.addWidget(txt)
        btns = QHBoxLayout()
        btn_clear = QPushButton("Limpar")
        btn_clear.clicked.connect(lambda: (clear_logs(), txt.setPlainText("")))
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(dlg.close)
        btns.addWidget(btn_clear)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)
        dlg.exec()

    def _clear_logs(self):
        clear_logs()
