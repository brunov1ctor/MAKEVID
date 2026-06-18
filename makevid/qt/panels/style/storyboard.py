"""Storyboard tab do Style Panel."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QGridLayout, QFileDialog, QApplication
)
from PySide6.QtCore import Qt
from pathlib import Path

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR
from makevid.qt.panels.style.widgets import DraggableDivider, AutoResizeTextEdit


class StoryboardMixin:
    """Metodos de storyboard do StylePanel."""

    def _build_storyboard_tab(self):
        w = QWidget()
        L = QVBoxLayout(w)
        L.setContentsMargins(10, 10, 10, 10)
        L.setSpacing(6)

        top = QHBoxLayout()
        top.addWidget(self._gold_label("\U0001f3ac STORYBOARD"))
        top.addStretch()
        btn_import = QPushButton("\u2913 Importar TXT")
        btn_import.setStyleSheet(self._btn_style("#44cc88"))
        btn_import.clicked.connect(self._import_storyboard_txt)
        top.addWidget(btn_import)
        btn_add = QPushButton("+ NOVA CENA")
        btn_add.setStyleSheet(self._btn_style("#44cc88"))
        btn_add.clicked.connect(self._add_scene)
        top.addWidget(btn_add)
        L.addLayout(top)

        self._sheet_scroll = QScrollArea()
        self._sheet_scroll.setWidgetResizable(True)
        self._sheet_scroll.setStyleSheet(f"QScrollArea {{ border: none; background: #0a0c18; }}")
        self._sheet_content = QWidget()
        self._sheet_content.setStyleSheet("background: #0a0c18;")
        self._sheet_layout = QVBoxLayout(self._sheet_content)
        self._sheet_layout.setContentsMargins(0, 0, 0, 0)
        self._sheet_layout.setSpacing(0)
        self._sheet_scroll.setWidget(self._sheet_content)
        L.addWidget(self._sheet_scroll)

        self._build_storyboard_grid()

        btns = QHBoxLayout()
        btn_save = QPushButton("\u25b6 SALVAR E GERAR TIMELINE")
        btn_save.setStyleSheet(f"background: {C['cyan']}; color: #0a0a0f; font-weight: bold; font-size: 10pt; padding: 6px 12px; border-radius: 4px;")
        btn_save.clicked.connect(self._save_storyboard_to_timeline)
        btns.addWidget(btn_save)
        btn_copy = QPushButton("\u2398 COPIAR CENAS")
        btn_copy.setStyleSheet(self._btn_style(C["gold"]))
        btn_copy.clicked.connect(self._copy_scenes)
        btns.addWidget(btn_copy)
        btns.addStretch()
        btn_clear = QPushButton("LIMPAR TODOS")
        btn_clear.setFixedHeight(30)
        btn_clear.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; border: 1px solid #ff4444; border-radius: 4px; padding: 4px 10px;")
        btn_clear.clicked.connect(self._clear_scenes)
        btns.addWidget(btn_clear)
        L.addLayout(btns)
        return w

    def _build_storyboard_grid(self):
        saved_widths = None
        if hasattr(self, '_grid_ref') and self._grid_ref:
            data_cols = self._data_cols
            saved_widths = []
            for dc in data_cols:
                w = self._grid_ref.cellRect(0, dc).width()
                saved_widths.append(w if w > 0 else 0)

        while self._sheet_layout.count():
            child = self._sheet_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: #0a0c18;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(4, 4, 4, 0)
        grid.setHorizontalSpacing(3)
        grid.setVerticalSpacing(3)
        grid.setRowMinimumHeight(0, 28)

        scenes = self.project.world.scenes
        self._scene_editors = []
        total_rows = max(3, len(scenes) + 2)

        data_cols = [2, 4, 6, 8, 10]
        div_cols = [1, 3, 5, 7, 9, 11]
        col_widths = {0: 30, 2: 200, 4: 120, 6: 120, 8: 150, 10: 100, 12: 50, 13: 28}

        grid.setColumnMinimumWidth(0, col_widths[0])
        for i, dc in enumerate(data_cols):
            if saved_widths and i < len(saved_widths) and saved_widths[i] > 0:
                grid.setColumnMinimumWidth(dc, saved_widths[i])
            else:
                grid.setColumnMinimumWidth(dc, col_widths[dc])
            grid.setColumnStretch(dc, 1)
        for dv in div_cols:
            grid.setColumnMinimumWidth(dv, 6)
        grid.setColumnMinimumWidth(12, col_widths[12])
        grid.setColumnMinimumWidth(13, col_widths[13])

        hdr_data = [
            (0, "#", C["gold"]), (2, "VISUAL", "#0ac8b9"), (4, "CÂMERA", "#3399ff"),
            (6, "SFX", "#44cc88"), (8, "DIÁLOGO", "#ff9944"), (10, "EMOÇÃO", "#cc44aa"),
            (12, "TEMPO", C["cyan"]), (13, "", "#ff4444"),
        ]
        for col, text, color in hdr_data:
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedHeight(24)
            lbl.setStyleSheet(f"color: {color}; font-family: Consolas; font-size: 10pt; font-weight: bold; border: none; background: none;")
            grid.addWidget(lbl, 0, col)

        self._grid_ref = grid
        self._data_cols = data_cols

        # Divisórias no header + dados (não no separador dourado)
        # Row 0 = header, Row 1 = separador, Row 2+ = dados
        for i, dv in enumerate(div_cols):
            div = DraggableDivider(i, self)
            if scenes:
                # Header + dados
                grid.addWidget(div, 0, dv, len(scenes) + 2, 1)
            else:
                # Só no header
                grid.addWidget(div, 0, dv, 1, 1)

        gold_sep = QFrame()
        gold_sep.setFixedHeight(2)
        gold_sep.setStyleSheet(f"background: {C['gold']};")
        grid.addWidget(gold_sep, 1, 0, 1, 14)

        if not scenes:
            grid.setRowStretch(2, 1)
            self._sheet_layout.addWidget(grid_widget)
            # Mensagem fora do grid
            empty_lbl = QLabel("Clique NOVA CENA para adicionar.")
            empty_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; background: none; border: none; padding: 12px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self._sheet_layout.addWidget(empty_lbl)
            self._sheet_layout.addStretch()
            return

        field_keys = ["visual", "camera", "sfx", "dialogue", "emotion"]
        field_colors = ["#0ac8b9", "#3399ff", "#44cc88", "#ff9944", "#cc44aa"]
        field_borders = ["#1a3a3a", "#1a2a3a", "#1a3a2a", "#3a2a1a", "#3a1a3a"]

        for idx, scene in enumerate(scenes):
            row = idx + 2
            bg = "#0d0f1a" if idx % 2 == 0 else "#0b0d16"
            num_lbl = QLabel(f"{idx+1}")
            num_lbl.setAlignment(Qt.AlignCenter)
            num_lbl.setStyleSheet(f"background: {bg}; color: {C['gold']}; font-family: Consolas; font-size: 9pt; font-weight: bold; padding: 4px;")
            grid.addWidget(num_lbl, row, 0)

            fields = {}
            for i, key in enumerate(field_keys):
                cell = AutoResizeTextEdit(scene.get(key, ""), field_colors[i], field_borders[i])
                grid.addWidget(cell, row, data_cols[i])
                fields[key] = cell

            dur_entry = QLineEdit(scene.get("duration", "5"))
            dur_entry.setAlignment(Qt.AlignCenter)
            dur_entry.setStyleSheet(f"background: #080a14; color: {C['cyan']}; border: 1px solid {C['border']}; border-radius: 4px; font-family: Consolas; font-size: 9pt; font-weight: bold; padding: 2px;")
            grid.addWidget(dur_entry, row, 12)
            fields["duration"] = dur_entry

            btn_x = QPushButton("X")
            btn_x.setObjectName("closeBtn")
            btn_x.setFixedSize(24, 24)
            btn_x.setToolTip("Remover cena")
            btn_x.clicked.connect(lambda ck=False, i=idx: self._remove_scene(i))
            grid.addWidget(btn_x, row, 13, 1, 1, Qt.AlignCenter)
            self._scene_editors.append(fields)

        grid.setRowStretch(total_rows, 1)
        self._sheet_layout.addWidget(grid_widget)

    def _load_storyboard_table(self):
        self._build_storyboard_grid()

    def _add_scene(self):
        self._collect_scenes()
        self.project.world.scenes.append({"visual": "", "camera": "", "dialogue": "", "emotion": "", "sfx": "", "duration": "5"})
        self._build_storyboard_grid()

    def _remove_scene(self, idx):
        self._collect_scenes()
        if idx < len(self.project.world.scenes):
            self.project.world.scenes.pop(idx)
            self.project.save(PROJECTS_DIR)
            self._build_storyboard_grid()

    def _collect_scenes(self):
        if not hasattr(self, '_scene_editors'):
            return
        scenes = []
        for fields in self._scene_editors:
            scene = {}
            for key in ("visual", "camera", "sfx", "dialogue", "emotion"):
                if key in fields:
                    widget = fields[key]
                    if hasattr(widget, 'toPlainText'):
                        scene[key] = widget.toPlainText().strip()
                    elif hasattr(widget, 'get_text'):
                        scene[key] = widget.get_text()
                    else:
                        scene[key] = widget.text().strip()
            scene["duration"] = fields.get("duration").text().strip() if fields.get("duration") else "5"
            scenes.append(scene)
        self.project.world.scenes = scenes

    def _save_storyboard_to_timeline(self):
        self._collect_scenes()
        self.project._storyboard_applied = True
        scenes = self.project.world.scenes
        clips = sorted(self.project.clips, key=lambda c: c.position)
        for i, scene in enumerate(scenes):
            dur = float(scene.get("duration", 5) or 5)
            prompt = scene.get("visual", "")
            camera = scene.get("camera", "")
            if camera:
                prompt = f"{prompt}, {camera}"
            if i >= len(clips):
                clip = self.project.add_clip(prompt=prompt)
                clip.duration = dur
            else:
                clips[i].prompt = prompt
                clips[i].duration = dur
        self.project.save(PROJECTS_DIR)

    def _import_storyboard_txt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Storyboard", "", "Text (*.txt)")
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.startswith("|--")]
        for line in lines:
            if line.startswith("|"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 2 and not parts[0].startswith("#"):
                    scene = {"visual": parts[1] if len(parts) > 1 else "",
                             "camera": parts[2] if len(parts) > 2 else "",
                             "dialogue": parts[3] if len(parts) > 3 else "",
                             "duration": parts[4] if len(parts) > 4 else "5"}
                    self.project.world.scenes.append(scene)
            else:
                self.project.world.scenes.append({"visual": line, "duration": "5"})
        self._load_storyboard_table()

    def _copy_scenes(self):
        self._collect_scenes()
        scenes = self.project.world.scenes
        if not scenes:
            return
        text = ""
        for i, scene in enumerate(scenes):
            row = [str(i+1)]
            for key in ("visual", "camera", "sfx", "dialogue", "emotion", "duration"):
                row.append(scene.get(key, "") or "-")
            text += " | ".join(row) + "\n"
        QApplication.clipboard().setText(text)

    def _clear_scenes(self):
        self.project.world.scenes = []
        self._build_storyboard_grid()
        self.project.save(PROJECTS_DIR)
