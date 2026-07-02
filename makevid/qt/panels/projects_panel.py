"""Projects Panel - CRUD de projetos."""

import time
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, OUTPUTS_DIR, AUDIO_DIR
from makevid.core.project import Project


class _ProjectCard(QFrame):
    open_requested   = Signal(str)
    delete_requested = Signal(str)
    renamed          = Signal(str, str)

    def __init__(self, project: Project, is_active: bool, editing: bool = False, parent=None):
        super().__init__(parent)
        self._id     = project.id
        self._name   = project.name
        self._active = is_active
        self.setObjectName("projCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        border = C["primary"] if is_active else C["border"]
        self.setStyleSheet(
            f"QFrame#projCard {{ background: {C['card']}; border: 1px solid {border}; border-radius: 8px; }}"
            f"QFrame#projCard:hover {{ border-color: {C['primary']}; background: {C['card_hover']}; }}"
            f"QFrame#projCard QLabel {{ background: transparent; border: none; }}"
        )
        self._build(project, is_active, editing)

    def _build(self, project: Project, is_active: bool, editing: bool):
        L = QVBoxLayout(self)
        L.setContentsMargins(10, 8, 10, 8)
        L.setSpacing(6)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)

        self._name_lbl = QLabel(project.name or project.id)
        self._name_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._name_lbl.setStyleSheet(f"color: {C['primary'] if is_active else C['text']}; background: transparent; border: none;")
        name_row.addWidget(self._name_lbl)

        if is_active:
            badge = QLabel("● ATIVO")
            badge.setStyleSheet(f"color: {C['primary']}; font-size: 7pt; font-weight: bold; background: transparent; border: none;")
            name_row.addWidget(badge)

        name_row.addStretch()

        self._name_edit = QLineEdit(project.name)
        self._name_edit.setFixedHeight(24)
        self._name_edit.setPlaceholderText("Nome do projeto...")
        self._name_edit.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; font-size: 10pt; font-weight: bold; "
            f"border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 6px;")
        self._name_edit.returnPressed.connect(self._confirm_rename)
        name_row.addWidget(self._name_edit)

        self._name_edit.setVisible(editing)
        self._name_lbl.setVisible(not editing)
        L.addLayout(name_row)

        n_clips = len(project.clips)
        n_audio = len([i for i in project.track_items if i.track in ("voice", "sfx", "music", "audio")])
        dur     = project.total_duration()
        created = time.strftime("%d/%m/%Y", time.localtime(project.created_at)) if project.created_at else "—"
        stats = QLabel(f"{n_clips} clips  •  {dur:.0f}s  •  {n_audio} áudios  •  {created}")
        stats.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt; background: transparent; border: none;")
        L.addWidget(stats)

        # Confirmação inline
        self._confirm_widget = QFrame()
        self._confirm_widget.setObjectName("confirmBox")
        self._confirm_widget.setAttribute(Qt.WA_StyledBackground, True)
        self._confirm_widget.setStyleSheet(
            f"QFrame#confirmBox {{ background: {C['danger_bg']}; border: none; border-radius: 4px; }}"
            f"QFrame#confirmBox QLabel {{ background: transparent; border: none; }}"
        )
        cw_l = QHBoxLayout(self._confirm_widget)
        cw_l.setContentsMargins(8, 6, 8, 6)
        cw_l.setSpacing(8)
        warn = QLabel("Tudo será perdido. Confirmar?")
        warn.setStyleSheet(f"color: {C['danger']}; font-size: 8pt; font-weight: bold;")
        cw_l.addWidget(warn)
        cw_l.addStretch()
        btn_confirm = QPushButton("Sim, deletar")
        btn_confirm.setFixedHeight(24)
        btn_confirm.setStyleSheet(
            f"QPushButton {{ background: {C['danger']}; color: {C['dark_text']}; font-size: 8pt; "
            f"font-weight: bold; border: none; border-radius: 4px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: #ff6666; }}")
        btn_confirm.clicked.connect(lambda: self.delete_requested.emit(self._id))
        cw_l.addWidget(btn_confirm)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(24)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
            f"border: 1px solid {C['border']}; border-radius: 4px; padding: 0 8px; }}"
            f"QPushButton:hover {{ color: {C['text']}; }}")
        btn_cancel.clicked.connect(self._hide_confirm)
        cw_l.addWidget(btn_cancel)
        self._confirm_widget.hide()
        L.addWidget(self._confirm_widget)

        btns = QHBoxLayout()
        btns.setSpacing(4)

        if not is_active:
            self._btn_open = QPushButton("Abrir")
            self._btn_open.setFixedHeight(26)
            self._btn_open.setStyleSheet(
                f"QPushButton {{ background: {C['primary']}; color: {C['dark_text']}; font-weight: bold; "
                f"font-size: 8pt; border: none; border-radius: 4px; padding: 0 12px; }}"
                f"QPushButton:hover {{ background: {C['secondary']}; }}")
            self._btn_open.clicked.connect(lambda: self.open_requested.emit(self._id))
            btns.addWidget(self._btn_open)

        self._btn_rename = QPushButton("Renomear")
        self._btn_rename.setFixedHeight(26)
        self._btn_rename.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['warning']}; font-size: 8pt; font-weight: bold; "
            f"border: 1px solid {C['warning']}; border-radius: 4px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: {C['warning']}; color: {C['dark']}; }}")
        self._btn_rename.clicked.connect(self._toggle_rename)
        btns.addWidget(self._btn_rename)

        self._btn_del = QPushButton("Deletar")
        self._btn_del.setFixedHeight(26)
        self._btn_del.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['danger']}; font-size: 8pt; font-weight: bold; "
            f"border: 1px solid {C['danger']}; border-radius: 4px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: {C['danger']}; color: {C['dark']}; }}")
        self._btn_del.clicked.connect(self._on_delete_clicked)
        btns.addWidget(self._btn_del)

        btns.addStretch()
        L.addLayout(btns)

        if editing:
            self._name_edit.setFocus()
            self._name_edit.selectAll()
            self._btn_rename.setText("Salvar")

    def _on_delete_clicked(self):
        if self._active:
            self._confirm_widget.show()
            self._btn_del.hide()
        else:
            self.delete_requested.emit(self._id)

    def _hide_confirm(self):
        self._confirm_widget.hide()
        self._btn_del.show()

    def _toggle_rename(self):
        if self._name_edit.isHidden():
            self._name_edit.setText(self._name)
            self._name_lbl.hide()
            self._name_edit.show()
            self._name_edit.setFocus()
            self._name_edit.selectAll()
            self._btn_rename.setText("Salvar")
        else:
            self._confirm_rename()

    def _confirm_rename(self):
        new_name = self._name_edit.text().strip() or self._name or self._id
        if new_name != self._name:
            try:
                proj = Project.load(PROJECTS_DIR / f"{self._id}.json")
                proj.name = new_name
                proj.save(PROJECTS_DIR)
                self._name = new_name
                self._name_lbl.setText(new_name)
                self.renamed.emit(self._id, new_name)
            except Exception as e:
                print(f"[ProjectCard] rename error: {e}")
        self._name_edit.hide()
        self._name_lbl.show()
        self._btn_rename.setText("Renomear")


class ProjectsPanel(QWidget):
    """CRUD de projetos."""

    closed         = Signal()
    project_opened = Signal(object)

    def __init__(self, active_project: Project, parent=None):
        super().__init__(parent)
        self._active_id   = active_project.id
        self._new_card_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header — mesmo padrão do ExportPanel e MixerPanel
        hdr = QHBoxLayout()
        title = QLabel("PROJETOS")
        title.setStyleSheet(f"color: {C['primary']}; font-size: 10pt; font-weight: bold; letter-spacing: 1px; background: transparent; border: none;")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_new = QPushButton("+ Novo")
        btn_new.setFixedHeight(24)
        btn_new.setStyleSheet(
            f"QPushButton {{ background: {C['primary']}; color: {C['dark_text']}; font-weight: bold; "
            f"font-size: 8pt; border: none; border-radius: 5px; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}")
        btn_new.clicked.connect(self._new_project)
        hdr.addWidget(btn_new)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("closeBtn")
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.closed.emit)
        hdr.addWidget(btn_close)
        layout.addLayout(hdr)

        # Lista
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._content)
        self._list_layout.setContentsMargins(0, 4, 0, 4)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

        self.refresh()

    def refresh(self):
        L = self._list_layout
        while L.count():
            item = L.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            empty = QLabel("Nenhum projeto. Clique em + Novo para começar.")
            empty.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; background: transparent; border: none;")
            L.addWidget(empty)
            L.addStretch()
            return

        for f in files:
            try:
                proj = Project.load(f)
            except Exception:
                continue
            is_active = proj.id == self._active_id
            editing   = proj.id == self._new_card_id
            card = _ProjectCard(proj, is_active=is_active, editing=editing)
            card.open_requested.connect(self._open_project)
            card.delete_requested.connect(self._delete_project)
            card.renamed.connect(self._on_renamed)
            L.addWidget(card)

        self._new_card_id = None
        L.addStretch()

    def set_active(self, project_id: str):
        self._active_id = project_id
        self.refresh()

    def _new_project(self):
        proj = Project.create("Novo Projeto")
        proj.save(PROJECTS_DIR)
        self._new_card_id = proj.id
        self.project_opened.emit(proj)
        self._active_id = proj.id
        self.refresh()

    def _open_project(self, project_id: str):
        try:
            proj = Project.load(PROJECTS_DIR / f"{project_id}.json")
            self._active_id = project_id
            self.project_opened.emit(proj)
            self.refresh()
        except Exception as e:
            print(f"[ProjectsPanel] open error: {e}")

    def _delete_project(self, project_id: str):
        proj_file = PROJECTS_DIR / f"{project_id}.json"
        print(f"[DELETE] Deletando projeto: {project_id} | arquivo existe: {proj_file.exists()}")
        proj_file.unlink(missing_ok=True)
        print(f"[DELETE] Apos delete, arquivo existe: {proj_file.exists()}")
        for d in (OUTPUTS_DIR / project_id, AUDIO_DIR / project_id):
            if d.exists():
                shutil.rmtree(str(d), ignore_errors=True)

        files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        print(f"[DELETE] Projetos restantes: {[f.stem for f in files]}")

        if project_id == self._active_id:
            if files:
                try:
                    next_proj = Project.load(files[0])
                    self._active_id = next_proj.id
                    self.project_opened.emit(next_proj)
                except Exception:
                    self._active_id = None
            else:
                self._active_id = None

        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.refresh)

    def _on_renamed(self, project_id: str, new_name: str):
        if project_id == self._active_id:
            try:
                proj = Project.load(PROJECTS_DIR / f"{project_id}.json")
                self.project_opened.emit(proj)
            except Exception:
                pass
