"""clip_properties — painel flutuante de propriedades do clip."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QTextEdit, QGridLayout, QFrame,
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QPainterPath, QLinearGradient, QBrush, QPen, QColor,
)

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR


class _GlassProps(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 14, 14)
        grad = QLinearGradient(0, 0, 0, self.height())
        base = QColor(28, 46, 74, 155)
        top  = QColor(42, 62, 90, 180)
        grad.setColorAt(0.0, top); grad.setColorAt(1.0, base)
        p.fillPath(path, QBrush(grad))
        hl = QPainterPath()
        hl.addRoundedRect(QRectF(8, 1, self.width() - 16, 18), 8, 8)
        hg = QLinearGradient(0, 0, 0, 18)
        hg.setColorAt(0.0, QColor(255, 255, 255, 12))
        hg.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen); p.fillPath(hl, QBrush(hg))
        bc = QColor(255, 255, 255, 55)
        p.setPen(QPen(bc, 1.0)); p.drawPath(path); p.end()


class ClipPropertiesMixin:
    """Mixin para PreviewWidget: painel de propriedades do clip."""

    def show_clip_properties(self, clip):
        self._hide_clip_properties()
        self._current_clip = clip

        panel = _GlassProps(self._display)
        panel.setFixedWidth(230)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.addStretch()
        btn_x = QPushButton("\u2715")
        btn_x.setFixedSize(22, 22)
        btn_x.setObjectName("closeBtn")
        btn_x.clicked.connect(self._hide_clip_properties)
        hdr.addWidget(btn_x)
        pl.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")
        sc = QWidget(); sc.setStyleSheet("background: transparent;")
        sl = QVBoxLayout(sc)
        sl.setContentsMargins(0, 4, 0, 4); sl.setSpacing(4)

        sl.addWidget(self._prop_lbl("DESCRICAO"))
        self._props_desc = QTextEdit()
        self._props_desc.setPlainText(clip.prompt or "")
        self._props_desc.setFixedHeight(56)
        self._props_desc.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['glass_border']};"
            " border-radius: 6px; padding: 3px; font-size: 9pt;"
        )
        self._props_desc.textChanged.connect(self._save_clip_desc)
        sl.addWidget(self._props_desc)
        sl.addWidget(self._prop_sep())

        def prop_row(label, value, color=C["text"]):
            r = QHBoxLayout()
            la = QLabel(label); la.setFixedWidth(60)
            la.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; font-weight: bold; border: none; background: transparent;")
            r.addWidget(la)
            va = QLabel(str(value))
            va.setStyleSheet(f"color: {color}; font-family: Consolas; font-size: 10pt; font-weight: bold; border: none; background: transparent;")
            r.addWidget(va); r.addStretch(); sl.addLayout(r)

        prop_row("Duracao", f"{clip.duration:.1f}s", C["accent"])
        prop_row("Status", clip.status.upper(), C["success"] if clip.status == "done" else C["primary"])
        prop_row("Seed", clip.seed or "random")
        if clip.video_path:
            vp = Path(clip.video_path)
            if vp.exists():
                prop_row("Tamanho", f"{vp.stat().st_size / 1e6:.1f} MB")
        sl.addWidget(self._prop_sep())

        sl.addWidget(self._prop_lbl("TITULO"))
        self._props_title = QLineEdit(clip.prompt or "")
        self._props_title.setStyleSheet(
            f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['glass_border']};"
            " border-radius: 6px; padding: 3px; font-size: 9pt; font-weight: bold;"
        )
        self._props_title.returnPressed.connect(self._save_clip_title)
        sl.addWidget(self._props_title)
        sl.addWidget(self._prop_sep())

        sl.addWidget(self._prop_lbl("ACOES"))
        gl = QGridLayout(); gl.setContentsMargins(0, 2, 0, 0); gl.setSpacing(3)

        def bstyle(c2):
            return (
                f"QPushButton {{ background: {C['card']}; color: {c2}; font-weight: bold; font-size: 8pt;"
                f" border: 1px solid {c2}; border-radius: 6px; padding: 4px; }}"
                f"QPushButton:hover {{ background: {C['card_hover']}; }}"
            )

        b1 = QPushButton("\u27f3 REGERAR")
        b1.setStyleSheet(
            f"QPushButton {{ background: {C['primary']}; color: {C['dark_text']}; font-weight: bold;"
            f" font-size: 8pt; border-radius: 6px; padding: 4px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}"
        )
        b1.clicked.connect(lambda: self._clip_action("regenerate")); gl.addWidget(b1, 0, 0)
        b2 = QPushButton("\u29c9 DUPLICAR"); b2.setStyleSheet(bstyle(C["accent"]))
        b2.clicked.connect(lambda: self._clip_action("duplicate")); gl.addWidget(b2, 0, 1)
        b3 = QPushButton("\u2702 DIVIDIR"); b3.setStyleSheet(bstyle(C["purple"]))
        b3.clicked.connect(lambda: self._clip_action("split")); gl.addWidget(b3, 1, 0)
        b4 = QPushButton("\u2715 REMOVER")
        b4.setStyleSheet(
            f"QPushButton {{ background: {C['danger_bg']}; color: {C['danger']}; font-weight: bold;"
            f" font-size: 8pt; border: 1px solid {C['danger']}; border-radius: 6px; padding: 4px; }}"
            f"QPushButton:hover {{ background: {C['danger']}; color: {C['dark_text']}; }}"
        )
        b4.clicked.connect(lambda: self._clip_action("delete")); gl.addWidget(b4, 1, 1)
        b5 = QPushButton("\u2b06 REFINAR"); b5.setStyleSheet(bstyle(C["success"]))
        b5.clicked.connect(lambda: self._clip_action("upscale")); gl.addWidget(b5, 2, 0)
        b6 = QPushButton("\U0001f464 FACE"); b6.setStyleSheet(bstyle(C["warning"]))
        b6.clicked.connect(lambda: self._clip_action("faceswap")); gl.addWidget(b6, 2, 1)
        b7 = QPushButton("\u270f EDITAR"); b7.setStyleSheet(bstyle(C["info"]))
        b7.clicked.connect(lambda: self._clip_action("inpaint")); gl.addWidget(b7, 3, 0, 1, 2)

        sl.addLayout(gl); sl.addStretch()
        scroll.setWidget(sc); pl.addWidget(scroll)

        panel_h = int(self._display.height() * 0.95)
        panel.setFixedHeight(max(200, panel_h))
        panel.move(max(0, self._display.width() - 235), 5)
        panel.show()
        self._props_panel = panel

    def _prop_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        return l

    def _prop_sep(self):
        s = QFrame(); s.setFixedHeight(1)
        s.setStyleSheet(f"background: {C['border']}; border: none;")
        return s

    def _save_clip_title(self):
        clip = getattr(self, "_current_clip", None)
        if clip and hasattr(self, "_props_title"):
            new = self._props_title.text().strip()
            if new and new != clip.prompt:
                clip.prompt = new
                self.project.save(PROJECTS_DIR)
                self.timeline.redraw()

    def _save_clip_desc(self):
        clip = getattr(self, "_current_clip", None)
        if clip and hasattr(self, "_props_desc"):
            new = self._props_desc.toPlainText().strip()
            if new != clip.prompt:
                clip.prompt = new
                self.project.save(PROJECTS_DIR)

    def _hide_clip_properties(self):
        panel = getattr(self, "_props_panel", None)
        if panel:
            panel.hide()
            panel.deleteLater()
            self._props_panel = None

    def _clip_action(self, action):
        clip = getattr(self, "_current_clip", None)
        if not clip:
            return
        app = self.window()
        app.state.selected_clip = clip
        if action == "regenerate":
            app._regenerate_clip()
        elif action == "duplicate":
            app._duplicate_clip()
        elif action == "split":
            app._split_clip_at_playhead()
        elif action == "delete":
            app.project.remove_clip(clip.id)
            app.project.save(PROJECTS_DIR)
            app.timeline.redraw()
        elif action == "inpaint":
            app._show_inpaint()
        self._hide_clip_properties()
