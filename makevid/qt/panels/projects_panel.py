"""Projects Panel - CRUD de projetos."""

import time
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, OUTPUTS_DIR, AUDIO_DIR
from makevid.core.project import Project


def _btn_style(color, bg="transparent", hover_bg=None):
    hover_bg = hover_bg or color
    return (
        f"QPushButton {{ background: {bg}; color: {color}; font-weight: bold; "
        f"font-size: 8pt; border: 1px solid {color}; border-radius: 6px; padding: 0 10px; }}"
        f"QPushButton:hover {{ background: {hover_bg}; color: {C['dark']}; }}"
    )


def _btn_primary_style():
    return (
        f"QPushButton {{ background: {C['primary']}; color: {C['dark_text']}; font-weight: bold; "
        f"font-size: 8pt; border: none; border-radius: 6px; padding: 0 12px; }}"
        f"QPushButton:hover {{ background: {C['secondary']}; }}"
    )


class _ProjectCard(QWidget):
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
        self.setStyleSheet(
            f"QWidget#projCard {{ background: {C['glass']}; border: 1px solid "
            f"{'rgba(108,99,255,0.5)' if is_active else C['glass_border']}; border-radius: 10px; }}"
            f"QWidget#projCard:hover {{ background: {C['glass_hover']}; border-color: {C['primary']}; }}"
            f"QWidget#projCard QLabel {{ background: transparent; border: none; }}"
        )
        self._build(project, is_active, editing)

    def _build(self, project: Project, is_active: bool, editing: bool):  # noqa: C901
        L = QVBoxLayout(self)
        L.setContentsMargins(12, 10, 12, 10)
        L.setSpacing(4)

        # ── Nome ──────────────────────────────────────────────────────────────
        name_row = QHBoxLayout()
        name_row.setSpacing(6)

        self._name_lbl = QLabel(project.name or project.id)
        self._name_lbl.setStyleSheet(
            f"color: {C['primary'] if is_active else C['text']}; "
            f"font-size: 10pt; font-weight: bold;"
        )
        name_row.addWidget(self._name_lbl)

        if is_active:
            badge = QLabel("● ATIVO")
            badge.setStyleSheet(f"color: {C['primary']}; font-size: 7pt; font-weight: bold;")
            name_row.addWidget(badge)

        name_row.addStretch()

        self._name_edit = QLineEdit(project.name)
        self._name_edit.setFixedHeight(24)
        self._name_edit.setPlaceholderText("Nome do projeto...")
        self._name_edit.returnPressed.connect(self._confirm_rename)
        name_row.addWidget(self._name_edit)

        self._name_edit.setVisible(editing)
        self._name_lbl.setVisible(not editing)
        L.addLayout(name_row)

        # ── Stats ─────────────────────────────────────────────────────────────
        n_clips = len(project.clips)
        n_audio = len([i for i in project.track_items if i.track in ("voice", "sfx", "music", "audio")])
        dur     = project.total_duration()
        created = time.strftime("%d/%m/%Y", time.localtime(project.created_at)) if project.created_at else "—"
        stats = QLabel(f"{n_clips} clips  •  {dur:.0f}s  •  {n_audio} áudios  •  {created}")
        stats.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 8pt;")
        L.addWidget(stats)

        # ── Confirmação de delete ─────────────────────────────────────────────
        self._confirm_widget = QWidget(self)
        self._confirm_widget.setStyleSheet("background: transparent;")
        cw_l = QHBoxLayout(self._confirm_widget)
        cw_l.setContentsMargins(0, 2, 0, 0)
        cw_l.setSpacing(6)
        warn = QLabel("Tudo será perdido. Confirmar?")
        warn.setStyleSheet(f"color: {C['danger']}; font-size: 8pt; font-weight: bold;")
        cw_l.addWidget(warn)
        cw_l.addStretch()
        btn_confirm = QPushButton("Sim, deletar")
        btn_confirm.setFixedHeight(22)
        btn_confirm.setStyleSheet(_btn_style(C["danger"], bg=C["danger"], hover_bg="#ff6666"))
        btn_confirm.clicked.connect(lambda: self.delete_requested.emit(self._id))
        cw_l.addWidget(btn_confirm)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(22)
        btn_cancel.setStyleSheet(_btn_style(C["text3"]))
        btn_cancel.clicked.connect(self._hide_confirm)
        cw_l.addWidget(btn_cancel)
        self._confirm_widget.hide()
        L.addWidget(self._confirm_widget)

        # ── Botões ────────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.setContentsMargins(0, 4, 0, 0)
        btns.setSpacing(6)

        if not is_active:
            btn_open = QPushButton("Abrir")
            btn_open.setFixedHeight(26)
            btn_open.setStyleSheet(_btn_primary_style())
            btn_open.clicked.connect(lambda: self.open_requested.emit(self._id))
            btns.addWidget(btn_open)

        self._btn_rename = QPushButton("Renomear")
        self._btn_rename.setFixedHeight(26)
        self._btn_rename.setStyleSheet(_btn_style(C["warning"]))
        self._btn_rename.clicked.connect(self._toggle_rename)
        btns.addWidget(self._btn_rename)

        self._btn_del = QPushButton("Deletar")
        self._btn_del.setFixedHeight(26)
        self._btn_del.setStyleSheet(_btn_style(C["danger"]))
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
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: transparent;")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(0)

        # ── Header — padrão MixerPanel ────────────────────────────────────────
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(0, 6, 0, 4)
        hdr_l.setSpacing(6)

        title = QLabel("PROJETOS")
        title.setStyleSheet(
            f"color: {C['primary']}; font-size: 13pt; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        hdr_l.addWidget(title)
        hdr_l.addStretch()

        btn_new = QPushButton("+ Novo")
        btn_new.setFixedHeight(26)
        btn_new.setStyleSheet(_btn_primary_style())
        btn_new.clicked.connect(self._new_project)
        hdr_l.addWidget(btn_new)

        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)

        layout.addLayout(hdr_l)

        # ── Contagem ──────────────────────────────────────────────────────────
        self._count_lbl = QLabel()
        self._count_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 9pt; background: transparent; border: none;"
        )
        layout.addWidget(self._count_lbl)

        # ── Separador ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['glass_border']}; border: none;")
        layout.addWidget(sep)

        # ── Lista ─────────────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content.setAttribute(Qt.WA_TranslucentBackground)
        self._list_layout = QVBoxLayout(self._content)
        self._list_layout.setContentsMargins(0, 8, 0, 8)
        self._list_layout.setSpacing(6)
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_loaded', False):
            self._loaded = True
            self.refresh()

    def refresh(self):
        self.setUpdatesEnabled(False)
        L = self._list_layout

        # Remove widgets de forma síncrona (sem deleteLater) para evitar flash
        while L.count():
            item = L.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        n = len(files)
        self._count_lbl.setText(f"  {n} projeto{'s' if n != 1 else ''}")

        if not files:
            empty = QLabel("Nenhum projeto. Clique em + Novo para começar.", self._content)
            empty.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; background: transparent; border: none;")
            L.addWidget(empty)
            L.addStretch()
            self.setUpdatesEnabled(True)
            return

        for f in files:
            try:
                proj = Project.load(f)
            except Exception:
                continue
            is_active = proj.id == self._active_id
            editing   = proj.id == self._new_card_id
            card = _ProjectCard(proj, is_active=is_active, editing=editing, parent=self._content)
            card.open_requested.connect(self._open_project)
            card.delete_requested.connect(self._delete_project)
            card.renamed.connect(self._on_renamed)
            L.addWidget(card)

        self._new_card_id = None
        L.addStretch()
        self.setUpdatesEnabled(True)

    def set_active(self, project_id: str):
        self._active_id = project_id
        self.refresh()

    def _new_project(self):
        from PySide6.QtCore import QTimer
        proj = Project.create("Novo Projeto")
        proj.save(PROJECTS_DIR)
        self._new_card_id = proj.id
        self._active_id = proj.id
        self.refresh()
        QTimer.singleShot(0, lambda: self.project_opened.emit(proj))

    def _open_project(self, project_id: str):
        from PySide6.QtCore import QTimer
        try:
            proj = Project.load(PROJECTS_DIR / f"{project_id}.json")
            self._active_id = project_id
            self.refresh()
            QTimer.singleShot(0, lambda: self.project_opened.emit(proj))
        except Exception as e:
            print(f"[ProjectsPanel] open error: {e}")

    def _delete_project(self, project_id: str):
        (PROJECTS_DIR / f"{project_id}.json").unlink(missing_ok=True)
        for d in (OUTPUTS_DIR / project_id, AUDIO_DIR / project_id):
            if d.exists():
                shutil.rmtree(str(d), ignore_errors=True)

        files = sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

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
