"""Ambience tab do Style Panel - Imagens de referencia visual."""

import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, AMBIENCE_REFS_DIR


class AmbienceMixin:
    """Metodos de ambientacao do StylePanel."""

    def _build_ambience_tab(self):
        # Scroll principal para todo o conteudo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['panel']}; }}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {C['panel']};")
        L = QVBoxLayout(content)
        L.setContentsMargins(10, 10, 10, 10)
        L.setSpacing(6)

        # === HEADER ===
        top = QHBoxLayout()
        title = QLabel("\U0001f5bc AMBIENTAÇÃO VISUAL")
        title.setStyleSheet(f"color: #44cc88; font-size: 13pt; font-weight: bold;")
        title.setToolTip(
            "COMO FUNCIONA\n\n"
            "1. Jogue imagens de referência aqui\n"
            "   (vilas, castelos, florestas, interiores, etc.)\n\n"
            "2. Ao gerar vídeo, o sistema AUTOMATICAMENTE\n"
            "   seleciona a imagem que mais combina com o prompt\n"
            "   e usa como referência visual.\n\n"
            "3. Resultado: vídeos com estética visual consistente.")
        top.addWidget(title)
        top.addStretch()

        btn_folder = QPushButton("\U0001f4c2")
        btn_folder.setFixedSize(28, 26)
        btn_folder.setToolTip("Abrir pasta no Explorer")
        btn_folder.setStyleSheet(f"background: {C['card']}; color: {C['text2']}; border: 1px solid {C['border']}; border-radius: 4px; font-size: 12pt; padding: 0;")
        btn_folder.clicked.connect(self._amb_open_folder)
        top.addWidget(btn_folder)

        btn_add_folder = QPushButton("+ PASTA")
        btn_add_folder.setFixedHeight(26)
        btn_add_folder.setToolTip("Importar TODAS as imagens de uma pasta")
        btn_add_folder.setStyleSheet(f"background: {C['card']}; color: #44cc88; font-weight: bold; font-size: 9pt; border: 1px solid #44cc88; border-radius: 4px; padding: 0 8px;")
        btn_add_folder.clicked.connect(self._amb_add_folder)
        top.addWidget(btn_add_folder)

        btn_add_imgs = QPushButton("+ IMAGENS")
        btn_add_imgs.setFixedHeight(26)
        btn_add_imgs.setToolTip("Selecionar imagens individuais (PNG, JPG, WEBP)")
        btn_add_imgs.setStyleSheet(f"background: #44cc88; color: #0a0a0f; font-weight: bold; font-size: 9pt; border-radius: 4px; padding: 0 10px;")
        btn_add_imgs.clicked.connect(self._amb_add_images)
        top.addWidget(btn_add_imgs)

        L.addLayout(top)

        # === INFO BOX ===
        info_frame = QFrame()
        info_frame.setObjectName("ambInfoFrame")
        info_frame.setStyleSheet(
            f"QFrame#ambInfoFrame {{ background: {C['card']}; border: 1px solid #44cc88; border-radius: 4px; }}"
            f"QFrame#ambInfoFrame QLabel {{ border: none; background: none; }}")
        info_l = QVBoxLayout(info_frame)
        info_l.setContentsMargins(10, 8, 10, 8)
        info_text = QLabel(
            "✓ AUTOMÁTICO: ao gerar vídeo, o sistema analisa o prompt e seleciona "
            "a imagem mais parecida como referência visual.\n"
            "✓ Quanto mais imagens variadas, melhor a cobertura de cenários.\n"
            "✓ Funciona com Storyboard (todas as cenas) e gerador individual.")
        info_text.setWordWrap(True)
        info_text.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        info_l.addWidget(info_text)
        L.addWidget(info_frame)

        # === STATUS ===
        status_row = QHBoxLayout()
        self._amb_count_label = QLabel("")
        self._amb_count_label.setStyleSheet(f"color: #44cc88; font-size: 10pt; font-weight: bold;")
        status_row.addWidget(self._amb_count_label)
        self._amb_status_label = QLabel("")
        self._amb_status_label.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")
        status_row.addWidget(self._amb_status_label)
        status_row.addStretch()
        L.addLayout(status_row)

        # === GRID DE IMAGENS ===
        self._amb_grid_scroll = QScrollArea()
        self._amb_grid_scroll.setWidgetResizable(True)
        self._amb_grid_scroll.setMinimumHeight(140)
        self._amb_grid_scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {C['border']}; border-radius: 4px; background: #0a0c18; }}")
        self._amb_grid_widget = QWidget()
        self._amb_grid_widget.setStyleSheet("background: #0a0c18;")
        self._amb_grid_layout = QVBoxLayout(self._amb_grid_widget)
        self._amb_grid_layout.setContentsMargins(6, 6, 6, 6)
        self._amb_grid_scroll.setWidget(self._amb_grid_widget)
        L.addWidget(self._amb_grid_scroll)

        # Botao limpar imagens
        img_btns = QHBoxLayout()
        img_btns.addStretch()
        btn_clear_imgs = QPushButton("LIMPAR TUDO")
        btn_clear_imgs.setFixedHeight(28)
        btn_clear_imgs.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; border: 1px solid #ff4444; border-radius: 4px; padding: 0 10px;")
        btn_clear_imgs.clicked.connect(self._amb_clear_all)
        img_btns.addWidget(btn_clear_imgs)
        L.addLayout(img_btns)

        # === CAMPOS DE MUNDO ===
        world_frame = QFrame()
        world_frame.setObjectName("ambWorldFrame")
        world_frame.setStyleSheet(
            f"QFrame#ambWorldFrame {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px; }}"
            f"QFrame#ambWorldFrame QLabel {{ border: none; background: none; }}")
        wl = QVBoxLayout(world_frame)
        wl.setContentsMargins(10, 8, 10, 8)
        wl.setSpacing(4)

        world_title = QLabel("MUNDO / ATMOSFERA")
        world_title.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; font-weight: bold;")
        wl.addWidget(world_title)

        self._amb_world_fields = {}
        world_defs = [
            ("location", "Locação"), ("style", "Estilo Visual"),
            ("lighting", "Iluminação"), ("weather", "Clima"),
            ("time_of_day", "Hora do Dia"), ("mood", "Mood/Atmosfera"),
            ("camera_style", "Estilo de Câmera"),
        ]
        for key, label in world_defs:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold;")
            wl.addWidget(lbl)
            entry = QLineEdit(str(getattr(self.project.world, key, "") or ""))
            entry.setStyleSheet(self._input_qss())
            wl.addWidget(entry)
            self._amb_world_fields[key] = entry

        L.addWidget(world_frame)

        # === SALVAR ===
        btn_save = QPushButton("SALVAR")
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 11pt; font-weight: bold; border-radius: 4px;")
        btn_save.clicked.connect(self._save_ambience)
        L.addWidget(btn_save)

        L.addStretch()
        scroll.setWidget(content)

        # Render inicial
        self._amb_selected_path = None
        self._amb_refresh()

        return scroll

    # === GRID RENDER ===

    def _amb_refresh(self):
        images = self._amb_get_images()
        self._amb_count_label.setText(f"{len(images)} imagens")
        if images:
            self._amb_status_label.setText(" | ⚡ Ativo (auto-match ligado)")
            self._amb_status_label.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")
        else:
            self._amb_status_label.setText(" | Inativo (adicione imagens para ativar)")
            self._amb_status_label.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        self._amb_render_grid(images)

    def _amb_render_grid(self, images):
        old = self._amb_grid_scroll.widget()
        if old:
            old.setParent(None)
            old.deleteLater()

        container = QWidget()
        container.setStyleSheet("background: #0a0c18;")
        grid = QGridLayout(container)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(6)

        self._amb_selected_path = None

        if not images:
            lbl = QLabel("Nenhuma imagem.\nClique + IMAGENS ou + PASTA para adicionar.")
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 10pt; border: none;")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, 0)
        else:
            cols = 5
            for i, img_path in enumerate(images):
                cell = QFrame()
                cell.setObjectName("ambCell")
                cell.setFixedSize(110, 120)
                cell.setCursor(Qt.PointingHandCursor)
                cell.setStyleSheet(
                    f"QFrame#ambCell {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px; }}"
                    f"QFrame#ambCell:hover {{ border: 2px solid #44cc88; }}")
                cl = QVBoxLayout(cell)
                cl.setContentsMargins(4, 4, 4, 2)
                cl.setSpacing(2)

                # Thumbnail
                thumb_lbl = QLabel()
                thumb_lbl.setFixedSize(100, 90)
                thumb_lbl.setAlignment(Qt.AlignCenter)
                thumb_lbl.setStyleSheet("border: none; background: none;")
                if img_path.exists():
                    pixmap = QPixmap(str(img_path))
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(100, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb_lbl.setPixmap(pixmap)
                    else:
                        thumb_lbl.setText("?")
                else:
                    thumb_lbl.setText("?")
                cl.addWidget(thumb_lbl)

                # Nome curto
                name_lbl = QLabel(img_path.stem[:14])
                name_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; border: none; background: none;")
                name_lbl.setAlignment(Qt.AlignCenter)
                cl.addWidget(name_lbl)

                # Click para selecionar
                cell.mousePressEvent = lambda e, p=img_path, c=cell: self._amb_select(p, c)

                # Botão X para remover
                btn_rm = QPushButton("X")
                btn_rm.setObjectName("closeBtn")
                btn_rm.setFixedSize(16, 16)
                btn_rm.clicked.connect(lambda checked=False, p=img_path: self._amb_remove(p))
                btn_rm.setParent(cell)
                btn_rm.move(92, 2)

                grid.addWidget(cell, i // cols, i % cols)

        self._amb_grid_scroll.setWidget(container)

    # === ACTIONS ===

    def _amb_get_images(self):
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        imgs = []
        if AMBIENCE_REFS_DIR.exists():
            for f in sorted(AMBIENCE_REFS_DIR.iterdir()):
                if f.suffix.lower() in exts:
                    imgs.append(f)
        return imgs

    def _amb_select(self, path, cell):
        if hasattr(self, '_amb_sel_cell') and self._amb_sel_cell:
            try:
                self._amb_sel_cell.setStyleSheet(
                    f"QFrame#ambCell {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px; }}"
                    f"QFrame#ambCell:hover {{ border: 2px solid #44cc88; }}")
            except Exception:
                pass
        self._amb_selected_path = path
        self._amb_sel_cell = cell
        cell.setStyleSheet(
            f"QFrame#ambCell {{ background: {C['card']}; border: 2px solid #44cc88; border-radius: 4px; }}")

    def _amb_add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Importar Imagens de Ambientação", "",
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not paths:
            return
        for p in paths:
            src = Path(p)
            dst = AMBIENCE_REFS_DIR / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
        self._amb_refresh()

    def _amb_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta com Imagens")
        if not folder:
            return
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        for f in Path(folder).iterdir():
            if f.suffix.lower() in exts:
                dst = AMBIENCE_REFS_DIR / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
        self._amb_refresh()

    def _amb_remove(self, path):
        try:
            Path(path).unlink()
        except Exception:
            pass
        self._amb_refresh()

    def _amb_clear_all(self):
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if AMBIENCE_REFS_DIR.exists():
            for f in AMBIENCE_REFS_DIR.iterdir():
                if f.suffix.lower() in exts:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        self._amb_refresh()

    def _amb_open_folder(self):
        AMBIENCE_REFS_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer "{AMBIENCE_REFS_DIR}"')


    def _save_ambience(self):
        w = self.project.world
        for key, entry in self._amb_world_fields.items():
            setattr(w, key, entry.text())
        self.project.save(PROJECTS_DIR)
