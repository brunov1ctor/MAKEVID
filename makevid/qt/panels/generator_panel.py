"""Generator Panel Qt - Painel esquerdo para gerar clips e imagens."""

import os
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QProgressBar, QScrollArea, QFrame, QFileDialog,
    QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QObject, QRect, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR


class _GoldTabBar(QWidget):
    """Tab bar custom com bordas douradas estilo Excel (replica do antigo tkinter)."""

    tab_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = 0
        self._tabs = ["GERAR CLIP", "GERAR IMAGEM"]
        self._hover = -1
        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w = self.width()
        h = self.height()
        tw = w // 2
        gold = QColor(C["gold"])
        panel = QColor(C["panel"])
        card = QColor(C["card"])
        text3 = QColor(C["text3"])
        cyan = QColor(C["cyan"])

        pen = QPen(gold, 2)
        p.setPen(pen)

        if self._active == 0:
            # Aba CLIP ativa: fundo panel, bordas gold L/T/R
            p.fillRect(QRect(0, 0, tw, h), panel)
            p.fillRect(QRect(tw, 4, tw, h - 4), card)
            # Bordas da aba ativa
            p.drawLine(0, h - 1, 0, 0)       # esquerda
            p.drawLine(0, 0, tw, 0)           # topo
            p.drawLine(tw, 0, tw, h - 1)      # direita
            # Linha base sob aba inativa
            p.drawLine(tw, h - 1, w, h - 1)
            p.drawLine(w - 1, h - 1, w - 1, h - 1)
            # Texto aba ativa
            p.setPen(QPen(gold))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(QRect(0, 0, tw, h), Qt.AlignCenter, self._tabs[0])
            # Texto aba inativa (hover = mais claro)
            color_inactive = QColor("#a09b8c") if self._hover == 1 else text3
            p.setPen(QPen(color_inactive))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(QRect(tw, 0, tw, h), Qt.AlignCenter, self._tabs[1])
        else:
            # Aba IMAGEM ativa
            p.fillRect(QRect(0, 4, tw, h - 4), card)
            p.fillRect(QRect(tw, 0, tw, h), panel)
            # Linha base sob aba inativa
            p.drawLine(0, h - 1, tw, h - 1)
            p.drawLine(0, h - 1, 0, h - 1)
            # Bordas da aba ativa
            p.drawLine(tw, h - 1, tw, 0)      # esquerda
            p.drawLine(tw, 0, w - 1, 0)       # topo
            p.drawLine(w - 1, 0, w - 1, h - 1) # direita
            # Texto aba inativa
            color_inactive = QColor("#a09b8c") if self._hover == 0 else text3
            p.setPen(QPen(color_inactive))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(QRect(0, 0, tw, h), Qt.AlignCenter, self._tabs[0])
            # Texto aba ativa
            p.setPen(QPen(cyan))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(QRect(tw, 0, tw, h), Qt.AlignCenter, self._tabs[1])

    def mousePressEvent(self, event):
        tw = self.width() // 2
        idx = 0 if event.position().x() < tw else 1
        if idx != self._active:
            self._active = idx
            self.tab_clicked.emit(idx)
            self.update()

    def mouseMoveEvent(self, event):
        tw = self.width() // 2
        new_hover = 0 if event.position().x() < tw else 1
        if new_hover != self._hover:
            self._hover = new_hover
            self.update()

    def leaveEvent(self, event):
        self._hover = -1
        self.update()


class GeneratorPanel(QWidget):
    """Painel de geração de clips (modo texto/imagem/motion)."""

    generation_requested = Signal(dict)  # emite params de geração

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self._ref_images = []
        self.setMinimumWidth(250)
        self.setStyleSheet(f"background: {C['panel']};")

        self._build_ui()
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Tab bar custom (bordas douradas estilo Excel)
        self._tab_bar = _GoldTabBar(self)
        self._tab_bar.tab_clicked.connect(self._switch_tab)
        outer.addWidget(self._tab_bar)

        # Body com bordas douradas (esquerda, direita, inferior)
        self._body_wrapper = QFrame()
        self._body_wrapper.setStyleSheet(
            f"QFrame {{ background: {C['panel']}; "
            f"border-left: 2px solid {C['gold']}; "
            f"border-right: 2px solid {C['gold']}; "
            f"border-bottom: 2px solid {C['gold']}; "
            f"border-top: none; }}")
        bw_layout = QVBoxLayout(self._body_wrapper)
        bw_layout.setContentsMargins(2, 0, 2, 2)
        bw_layout.setSpacing(0)

        # Stack para as 2 abas
        self._tab_stack = QStackedWidget()
        self._tab_stack.setStyleSheet(f"background: {C['panel']}; border: none;")
        self._tab_stack.addWidget(self._build_clip_tab())   # 0
        self._tab_stack.addWidget(self._build_image_tab())  # 1
        bw_layout.addWidget(self._tab_stack)
        outer.addWidget(self._body_wrapper)

        # Token frames (hidden, aparecem inline no scroll quando necessario)
        self._token_frame = None
        self._fs_token_frame = None
        self._auto_retry_generation = False

    def _switch_tab(self, idx):
        self._tab_stack.setCurrentIndex(idx)
        self._tab_bar._active = idx
        self._tab_bar.update()

    def _show_token_prompt(self, auto_generate=False):
        """Mostra campo inline no scroll para inserir HF token. auto_generate=True faz retry apos salvar."""
        if self._token_frame:
            try:
                self._token_frame.setParent(None)
                self._token_frame.deleteLater()
            except Exception:
                pass

        self._auto_retry_generation = auto_generate
        self._token_frame = QFrame()
        self._token_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['gold']}; border-radius: 6px;")
        tf_l = QVBoxLayout(self._token_frame)
        tf_l.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel("TOKEN HUGGINGFACE")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; font-weight: bold;")
        tf_l.addWidget(lbl)
        sub = QLabel("Crie em: huggingface.co/settings/tokens")
        sub.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        tf_l.addWidget(sub)
        self._token_entry = QLineEdit()
        self._token_entry.setPlaceholderText("hf_...")
        self._token_entry.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['gold']}; border-radius: 4px; padding: 4px; font-family: Consolas; font-size: 10pt;")
        self._token_entry.returnPressed.connect(self._save_hf_token)
        tf_l.addWidget(self._token_entry)
        btns = QHBoxLayout()
        btn_save = QPushButton("SALVAR")
        btn_save.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-weight: bold; border-radius: 3px; padding: 4px 12px;")
        btn_save.clicked.connect(self._save_hf_token)
        btns.addWidget(btn_save)
        btn_x = QPushButton("X")
        btn_x.setFixedSize(28, 24)
        btn_x.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        btn_x.clicked.connect(self._hide_token_prompt)
        btns.addWidget(btn_x)
        btns.addStretch()
        tf_l.addLayout(btns)

        # Inserir embaixo no scroll da aba ativa (antes do stretch final)
        if self._tab_stack.currentIndex() == 0:
            count = self._clip_scroll_layout.count()
            self._clip_scroll_layout.insertWidget(count - 1, self._token_frame)
        else:
            count = self._img_scroll_layout.count()
            self._img_scroll_layout.insertWidget(count - 1, self._token_frame)
        self._token_entry.setFocus()

    def _save_hf_token(self):
        token = self._token_entry.text().strip()
        if token:
            os.environ["HF_TOKEN"] = token
            self._status.setText("Token HF salvo!")
            self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
        self._hide_token_prompt()
        if self._auto_retry_generation and token:
            if self._tab_stack.currentIndex() == 0:
                self._on_generate()
            else:
                self._on_generate_image()

    def _hide_token_prompt(self):
        if self._token_frame:
            self._token_frame.setParent(None)
            self._token_frame.deleteLater()
            self._token_frame = None

    def _show_freesound_prompt(self, on_saved=None):
        """Mostra campo inline para Freesound API key (mesmo padrao do HF token)."""
        if self._fs_token_frame:
            try:
                self._fs_token_frame.setParent(None)
                self._fs_token_frame.deleteLater()
            except Exception:
                pass

        self._fs_on_saved = on_saved
        self._fs_token_frame = QFrame()
        self._fs_token_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['gold']}; border-radius: 6px;")
        fl = QVBoxLayout(self._fs_token_frame)
        fl.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel("FREESOUND API KEY")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; font-weight: bold;")
        fl.addWidget(lbl)
        sub = QLabel("Crie em: freesound.org/apiv2/apply")
        sub.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        fl.addWidget(sub)
        self._fs_entry = QLineEdit()
        self._fs_entry.setPlaceholderText("sua_api_key_aqui")
        self._fs_entry.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['gold']}; border-radius: 4px; padding: 4px; font-family: Consolas; font-size: 10pt;")
        self._fs_entry.returnPressed.connect(self._save_fs_key)
        fl.addWidget(self._fs_entry)
        btns = QHBoxLayout()
        btn_save = QPushButton("SALVAR")
        btn_save.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-weight: bold; border-radius: 3px; padding: 4px 12px;")
        btn_save.clicked.connect(self._save_fs_key)
        btns.addWidget(btn_save)
        btn_x = QPushButton("X")
        btn_x.setFixedSize(28, 24)
        btn_x.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        btn_x.clicked.connect(self._hide_fs_prompt)
        btns.addWidget(btn_x)
        btns.addStretch()
        fl.addLayout(btns)

        # Inserir embaixo no scroll (antes do stretch final)
        count = self._clip_scroll_layout.count()
        self._clip_scroll_layout.insertWidget(count - 1, self._fs_token_frame)
        self._fs_entry.setFocus()

    def _save_fs_key(self):
        key = self._fs_entry.text().strip()
        if key:
            os.environ["FREESOUND_API_KEY"] = key
            from makevid.core import freesound_provider
            freesound_provider.FREESOUND_API_KEY = key
            self._status.setText("Freesound key salva!")
            self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
        self._hide_fs_prompt()
        if key and self._fs_on_saved:
            self._fs_on_saved()

    def _hide_fs_prompt(self):
        if self._fs_token_frame:
            self._fs_token_frame.setParent(None)
            self._fs_token_frame.deleteLater()
            self._fs_token_frame = None

    # ============================================================
    # TAB: GERAR CLIP
    # ============================================================

    def _build_clip_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        L = QVBoxLayout(content)
        L.setContentsMargins(10, 10, 10, 10)
        L.setSpacing(6)
        self._clip_scroll_layout = L  # ref para inserir token inline

        # MODO
        L.addWidget(self._section_label("MODO"))
        mode_frame = QFrame()
        mode_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 5px;")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(10, 8, 10, 8)
        self._mode_group = QButtonGroup(self)
        self._rb_text = QRadioButton("Texto")
        self._rb_image = QRadioButton("Img+Texto")
        self._rb_motion = QRadioButton("Motion")
        self._rb_text.setChecked(True)

        radio_gold_qss = (
            f"QRadioButton {{ color: {C['text']}; font-family: 'Segoe UI'; font-size: 11pt; spacing: 6px; }}"
            f"QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 2px solid {C['gold']}; }}"
            f"QRadioButton::indicator:checked {{ background: {C['gold']}; border: 2px solid {C['gold']}; }}"
            f"QRadioButton::indicator:hover {{ border: 2px solid #ffd700; }}")
        radio_green_qss = (
            f"QRadioButton {{ color: {C['text']}; font-family: 'Segoe UI'; font-size: 11pt; spacing: 6px; }}"
            f"QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 2px solid #44cc88; }}"
            f"QRadioButton::indicator:checked {{ background: #44cc88; border: 2px solid #44cc88; }}"
            f"QRadioButton::indicator:hover {{ border: 2px solid #66ffaa; }}")

        self._rb_text.setStyleSheet(radio_gold_qss)
        self._rb_image.setStyleSheet(radio_gold_qss)
        self._rb_motion.setStyleSheet(radio_green_qss)

        for rb in (self._rb_text, self._rb_image, self._rb_motion):
            self._mode_group.addButton(rb)
            mode_layout.addWidget(rb)
        self._mode_group.buttonClicked.connect(self._on_mode_changed)
        L.addWidget(mode_frame)

        # REF IMAGES (thumbnails) - visivel apenas em modo Img+Texto
        self._ref_frame = QFrame()
        self._ref_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['cyan']}; border-radius: 6px;")
        ref_layout = QVBoxLayout(self._ref_frame)
        ref_layout.setContentsMargins(8, 6, 8, 6)
        ref_layout.setSpacing(4)
        ref_btn_row = QHBoxLayout()
        btn_add_ref = QPushButton("+ Imagem")
        btn_add_ref.setFixedHeight(28)
        btn_add_ref.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-weight: bold; font-size: 10pt; border: 1px solid {C['cyan']}; border-radius: 4px; padding: 0 10px;")
        btn_add_ref.clicked.connect(self._add_ref_image)
        ref_btn_row.addWidget(btn_add_ref)
        btn_clear_ref = QPushButton("Limpar")
        btn_clear_ref.setFixedHeight(28)
        btn_clear_ref.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-size: 9pt; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 8px;")
        btn_clear_ref.clicked.connect(self._clear_ref_images)
        ref_btn_row.addWidget(btn_clear_ref)
        ref_btn_row.addStretch()
        ref_layout.addLayout(ref_btn_row)
        self._ref_thumbs_widget = QWidget()
        self._ref_thumbs_layout = QHBoxLayout(self._ref_thumbs_widget)
        self._ref_thumbs_layout.setContentsMargins(0, 0, 0, 0)
        self._ref_thumbs_layout.setSpacing(3)
        ref_layout.addWidget(self._ref_thumbs_widget)
        self._ref_frame.hide()
        L.addWidget(self._ref_frame)

        # MOTION SECTION (hidden by default)
        self._motion_frame = QFrame()
        self._prompt = QTextEdit()
        self._prompt.setFixedHeight(90)
        self._prompt.setPlaceholderText("Descreva a cena...")
        self._prompt.setToolTip("Descreva o que voce quer ver no video.\nEx: 'Um guerreiro caminhando por uma floresta sombria'")
        self._prompt.setStyleSheet(
            f"QTextEdit {{ background: {C['input']}; color: {C['cyan']}; border: 2px solid {C['gold']}; "
            f"border-radius: 8px; font-family: Consolas; font-size: 11pt; font-weight: bold; }}"
            f"QTextEdit:hover {{ border: 3px solid #ffd700; }}"
            f"QTextEdit:focus {{ border: 3px solid #ffd700; }}")
        L.addWidget(self._prompt)

        # Continuidade
        self._continuity = QCheckBox("Continuar do anterior")
        self._continuity.setChecked(True)
        self._continuity.setToolTip("Usa o ultimo frame do clip anterior como referencia.\nGarante continuidade visual entre cenas.")
        self._continuity.setStyleSheet(f"color: {C['text']}; font-size: 10pt;")
        L.addWidget(self._continuity)

        # NEGATIVE PROMPT
        neg_lbl = self._sub_label("NEGATIVE PROMPT")
        neg_lbl.setToolTip("Descreva o que voce NAO quer no video.\nO modelo tenta evitar esses elementos.")
        neg_lbl.setCursor(Qt.WhatsThisCursor)
        L.addWidget(neg_lbl)
        self._negative = QTextEdit()
        self._negative.setFixedHeight(40)
        self._negative.setPlainText("blurry, low quality, distorted, watermark, static")
        self._negative.setStyleSheet(
            f"QTextEdit {{ background: {C['input']}; color: {C['text3']}; border: 2px solid {C['border']}; "
            f"border-radius: 8px; font-family: Consolas; font-size: 10pt; }}"
            f"QTextEdit:hover {{ border: 3px solid {C['gold']}; }}"
            f"QTextEdit:focus {{ border: 3px solid {C['gold']}; }}")
        L.addWidget(self._negative)

        # PARAMETROS
        self._motion_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 5px;")
        ml = QVBoxLayout(self._motion_frame)
        ml.setContentsMargins(8, 6, 8, 6)
        ml.addWidget(self._sub_label("VIDEO DE REFERENCIA (Motion)"))
        mr = QHBoxLayout()
        self._motion_path = QLineEdit()
        self._motion_path.setPlaceholderText("Selecione video...")
        self._motion_path.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 4px; font-size: 9pt;")
        mr.addWidget(self._motion_path)
        btn_browse = QPushButton("...")
        btn_browse.setFixedSize(28, 22)
        btn_browse.clicked.connect(self._browse_motion_video)
        mr.addWidget(btn_browse)
        ml.addLayout(mr)
        ct_row = QHBoxLayout()
        self._ctrl_type = QComboBox()
        self._ctrl_type.addItems(["Pose", "Depth"])
        self._ctrl_type.setStyleSheet(f"background: {C['card']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 6px;")
        ct_row.addWidget(QLabel("Tipo:"))
        ct_row.addWidget(self._ctrl_type)
        ct_row.addStretch()
        ml.addLayout(ct_row)
        self._motion_frame.hide()
        L.addWidget(self._motion_frame)

        # PARAMETROS
        L.addWidget(self._section_label("PARAMETROS"))
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 5px;")
        params_layout = QVBoxLayout(params_frame)
        params_layout.setContentsMargins(8, 8, 8, 8)
        params_layout.setSpacing(4)
        r1 = QHBoxLayout()
        self._dur = self._param_entry(r1, "Duracao", "5", 45, tooltip="Duracao do video em segundos")
        self._steps = self._param_entry(r1, "Steps", "30", 45, tooltip="Passos de inferencia.\nMais steps = mais qualidade, mais lento")
        params_layout.addLayout(r1)
        r2 = QHBoxLayout()
        self._cfg = self._param_entry(r2, "CFG", "5.0", 55, tooltip="Classifier-Free Guidance.\nBaixo (1-3): criativo\nMedio (4-7): equilibrado\nAlto (8+): segue o prompt")
        params_layout.addLayout(r2)
        r3 = QHBoxLayout()
        self._seed = self._param_entry(r3, "Seed", "", 65, tooltip="Semente para reproducibilidade.\nMesma seed + mesmo prompt = mesmo resultado")
        self._seed.setPlaceholderText("random")
        params_layout.addLayout(r3)
        r4 = QHBoxLayout()
        lbl = QLabel("Resolucao")
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        lbl.setToolTip("Resolucao do video gerado.\nMaior resolucao = mais VRAM e mais tempo")
        lbl.setCursor(Qt.WhatsThisCursor)
        r4.addWidget(lbl)
        self._resolution = QComboBox()
        self._resolution.addItems(["480p (832x480)", "720p (1280x720)", "1080p (1920x1080)", "4K (3840x2160)"])
        self._resolution.setCurrentIndex(0)
        self._resolution.setStyleSheet(f"background: {C['card']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 6px;")
        r4.addWidget(self._resolution)
        r4.addStretch()
        params_layout.addLayout(r4)
        L.addWidget(params_frame)

        # BOTAO GERAR
        self._gen_btn = QPushButton("GERAR CLIP")
        self._gen_btn.setFixedHeight(44)
        self._gen_btn.setStyleSheet(
            f"background: {C['gold']}; color: #0a0a0f; font-size: 14pt; font-weight: bold; "
            f"border: 2px solid #ffd700; border-radius: 6px;")
        self._gen_btn.clicked.connect(self._on_generate)
        L.addWidget(self._gen_btn)

        # PROGRESS + STATUS
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            f"QProgressBar {{ background: {C['card']}; border: none; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background: {C['cyan']}; border-radius: 3px; }}")
        L.addWidget(self._progress)
        self._status = QLabel("Pronto")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 10pt; border: none;")
        L.addWidget(self._status)
        L.addStretch()

        scroll.setWidget(content)
        return scroll

    # ============================================================
    # TAB: GERAR IMAGEM
    # ============================================================

    def _build_image_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        content = QWidget()
        L = QVBoxLayout(content)
        L.setContentsMargins(10, 10, 10, 10)
        L.setSpacing(6)
        self._img_scroll_layout = L  # ref para inserir token inline

        L.addWidget(self._section_label("GERAR IMAGEM"))
        L.addWidget(self._sub_label("Gera imagem estatica via HF API / FLUX / Local"))

        # Prompt
        L.addWidget(self._sub_label("PROMPT"))
        self._img_prompt = QTextEdit()
        self._img_prompt.setFixedHeight(70)
        self._img_prompt.setPlaceholderText("Descreva a imagem...")
        self._img_prompt.setStyleSheet(
            f"background: {C['input']}; color: {C['cyan']}; border: 2px solid {C['gold']}; "
            f"border-radius: 8px; font-family: Consolas; font-size: 11pt; font-weight: bold;")
        L.addWidget(self._img_prompt)

        # Negative
        L.addWidget(self._sub_label("NEGATIVE"))
        self._img_negative = QTextEdit()
        self._img_negative.setFixedHeight(35)
        self._img_negative.setPlainText("blurry, low quality, watermark")
        self._img_negative.setStyleSheet(
            f"background: {C['input']}; color: {C['text3']}; border: 2px solid {C['border']}; "
            f"border-radius: 8px; font-family: Consolas; font-size: 10pt;")
        L.addWidget(self._img_negative)

        # Engine
        r_eng = QHBoxLayout()
        r_eng.addWidget(self._sub_label("Engine:"))
        self._img_engine = QComboBox()
        self._img_engine.addItems(["HF API (FLUX)", "HF API (SD-XL)", "Local (SDXL)"])
        self._img_engine.setStyleSheet(f"background: {C['card']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 6px;")
        r_eng.addWidget(self._img_engine)
        r_eng.addStretch()
        L.addLayout(r_eng)

        # Resolution
        r_res = QHBoxLayout()
        r_res.addWidget(self._sub_label("Resolucao:"))
        self._img_resolution = QComboBox()
        self._img_resolution.addItems(["1024x1024", "1280x720", "832x480", "512x512"])
        self._img_resolution.setStyleSheet(f"background: {C['card']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 6px;")
        r_res.addWidget(self._img_resolution)
        r_res.addStretch()
        L.addLayout(r_res)

        # Duration as static clip
        r_dur = QHBoxLayout()
        self._img_dur = self._param_entry(r_dur, "Duracao (clip)", "5", 50)
        L.addLayout(r_dur)

        # Generate button
        self._img_gen_btn = QPushButton("GERAR IMAGEM")
        self._img_gen_btn.setFixedHeight(40)
        self._img_gen_btn.setStyleSheet(
            f"background: {C['cyan']}; color: #0a0a0f; font-size: 13pt; font-weight: bold; "
            f"border: 2px solid {C['cyan']}; border-radius: 6px;")
        self._img_gen_btn.clicked.connect(self._on_generate_image)
        L.addWidget(self._img_gen_btn)

        # Status
        self._img_status = QLabel("")
        self._img_status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        L.addWidget(self._img_status)
        L.addStretch()

        scroll.setWidget(content)
        return scroll

    # ============================================================
    # MODE SWITCH (Texto / Img+Texto / Motion)
    # ============================================================

    def _on_mode_changed(self, btn=None):
        """Mostra/esconde ref images e motion frame conforme o modo."""
        if self._rb_image.isChecked():
            self._ref_frame.show()
            self._motion_frame.hide()
        elif self._rb_motion.isChecked():
            self._ref_frame.hide()
            self._motion_frame.show()
        else:
            self._ref_frame.hide()
            self._motion_frame.hide()

    def _browse_motion_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Video de Referencia", "", "Video (*.mp4 *.avi *.mov *.mkv)")
        if path:
            self._motion_path.setText(path)

    # ============================================================
    # REF IMAGES (thumbnails)
    # ============================================================

    def _add_ref_image(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Imagens de Referencia", "", "Images (*.png *.jpg *.jpeg *.webp)")
        for p in paths:
            if p not in self._ref_images:
                self._ref_images.append(p)
        self._refresh_ref_thumbs()

    def _clear_ref_images(self):
        self._ref_images.clear()
        self._refresh_ref_thumbs()

    def _remove_ref_image(self, path):
        if path in self._ref_images:
            self._ref_images.remove(path)
            self._refresh_ref_thumbs()

    def _refresh_ref_thumbs(self):
        """Reconstroi thumbnails com botao X individual."""
        while self._ref_thumbs_layout.count():
            child = self._ref_thumbs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._ref_images:
            lbl = QLabel("Nenhuma imagem")
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
            self._ref_thumbs_layout.addWidget(lbl)
            return

        for p in self._ref_images:
            item_frame = QFrame()
            item_frame.setFixedSize(48, 48)
            item_frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['cyan']}; border-radius: 4px;")
            # Thumbnail
            thumb_lbl = QLabel(item_frame)
            pix = QPixmap(p).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumb_lbl.setPixmap(pix)
            thumb_lbl.move(2, 2)
            # Botao X
            btn_x = QPushButton("x", item_frame)
            btn_x.setFixedSize(14, 14)
            btn_x.setStyleSheet("background: #ff4444; color: #ffffff; font-size: 7pt; border-radius: 7px; font-weight: bold;")
            btn_x.move(34, 0)
            btn_x.clicked.connect(lambda ck=False, path=p: self._remove_ref_image(path))
            self._ref_thumbs_layout.addWidget(item_frame)

        # Contador
        count_lbl = QLabel(f" {len(self._ref_images)}")
        count_lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt; font-weight: bold;")
        self._ref_thumbs_layout.addWidget(count_lbl)

    # ============================================================
    # GENERATE IMAGE
    # ============================================================

    def _on_generate_image(self):
        """Gera imagem e salva como clip estatico na timeline."""
        prompt = self._img_prompt.toPlainText().strip()
        if not prompt:
            self._img_status.setText("Digite um prompt")
            return

        self._img_gen_btn.setEnabled(False)
        self._img_status.setText("Gerando imagem...")
        self._img_status.setStyleSheet(f"color: {C['gold']}; font-size: 9pt;")

        engine = self._img_engine.currentText()
        res_text = self._img_resolution.currentText()
        w, h = [int(x) for x in res_text.split("x")]
        duration = float(self._img_dur.text() or "5")
        token = os.environ.get("HF_TOKEN", "")

        # Verificar token ANTES de iniciar thread
        if not token and "HF" in engine:
            from makevid.core.hf_api import _get_token
            token = _get_token()
            if not token:
                self._img_gen_btn.setEnabled(True)
                self._img_status.setText("Insira o token HF")
                self._img_status.setStyleSheet(f"color: {C['gold']}; font-size: 9pt;")
                self._show_token_prompt(auto_generate=True)
                return

        # Animacao de progress (replica do commit 73804393 tkinter)
        self._img_progress_timer = QTimer(self)
        self._img_progress_timer.setInterval(200)
        self._img_progress_value = 15
        def _animate_progress():
            if self._img_progress_value < 85:
                self._img_progress_value += 2
                self._progress.setValue(self._img_progress_value)
        self._img_progress_timer.timeout.connect(_animate_progress)
        self._progress.setValue(15)
        self._img_progress_timer.start()

        def run():
            try:
                actual_token = token or os.environ.get("HF_TOKEN", "")

                import requests, tempfile, io
                from PIL import Image
                from pathlib import Path
                from makevid.config import OUTPUTS_DIR

                if "FLUX" in engine:
                    url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                else:
                    url = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

                headers = {"Authorization": f"Bearer {actual_token}"}
                payload = {"inputs": prompt}
                r = requests.post(url, headers=headers, json=payload, timeout=120)

                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    img = Image.open(io.BytesIO(r.content)).resize((w, h))
                    out_dir = OUTPUTS_DIR / self.project.id
                    out_dir.mkdir(parents=True, exist_ok=True)
                    img_path = out_dir / f"img_{int(__import__('time').time())}.png"
                    img.save(str(img_path))

                    # Criar video estatico a partir da imagem
                    mp4_path = img_path.with_suffix(".mp4")
                    self._image_to_static_video(str(img_path), str(mp4_path), duration, 16, w, h)

                    # Adicionar clip
                    clip = self.project.add_clip(prompt=prompt, position=len(self.project.clips))
                    clip.video_path = str(mp4_path)
                    clip.duration = duration
                    clip.status = "done"
                    self.project.save(PROJECTS_DIR)

                    from PySide6.QtCore import QTimer
                    def _on_img_done():
                        self._img_progress_timer.stop()
                        self._progress.setValue(100)
                        self._img_status.setText(f"\u2714 Imagem salva como clip ({duration}s)")
                        self._img_status.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")
                        self._img_gen_btn.setEnabled(True)
                        self.generation_requested.emit({"action": "image_done"})
                        QTimer.singleShot(1500, lambda: self._progress.setValue(0))
                    QTimer.singleShot(0, _on_img_done)
                else:
                    err = r.text[:60] if r.text else str(r.status_code)
                    from PySide6.QtCore import QTimer
                    def _on_img_fail():
                        self._img_progress_timer.stop()
                        self._progress.setValue(0)
                        self._img_status.setText(f"Erro: {err}")
                        self._img_status.setStyleSheet(f"color: #ff4444; font-size: 9pt;")
                        self._img_gen_btn.setEnabled(True)
                        # Se 401/403, mostrar token prompt
                        if "401" in err or "403" in err or "token" in err.lower():
                            self._show_token_prompt(auto_generate=True)
                    QTimer.singleShot(0, _on_img_fail)
            except Exception as e:
                from PySide6.QtCore import QTimer
                err_msg = str(e)[:40]
                def _on_img_error():
                    self._img_progress_timer.stop()
                    self._progress.setValue(0)
                    self._img_status.setText(f"Erro: {err_msg}")
                    self._img_status.setStyleSheet(f"color: #ff4444; font-size: 9pt;")
                    self._img_gen_btn.setEnabled(True)
                    # Se erro de autenticacao, mostrar prompt de token com auto-retry
                    if "401" in str(e) or "token" in str(e).lower() or "unauthorized" in str(e).lower():
                        self._show_token_prompt(auto_generate=True)
                QTimer.singleShot(0, _on_img_error)

        threading.Thread(target=run, daemon=True).start()

    def _image_to_static_video(self, img_path, mp4_path, duration, fps, w, h):
        """Converte imagem em video estatico."""
        import cv2
        img = cv2.imread(img_path)
        img = cv2.resize(img, (w, h))
        # Tentar H264 primeiro, fallback mp4v
        for codec in ["avc1", "H264", "mp4v"]:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(mp4_path, fourcc, fps, (w, h))
            if writer.isOpened():
                break
            writer.release()
        for _ in range(int(duration * fps)):
            writer.write(img)
        writer.release()

    # ============================================================
    # HELPERS
    # ============================================================

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text']}; font-size: 10pt; font-weight: bold; border: none;")
        return lbl

    def _sub_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; font-weight: bold; border: none;")
        return lbl

    def _param_entry(self, layout, label, default, width, tooltip=None):
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;")
        if tooltip:
            lbl.setToolTip(tooltip)
            lbl.setCursor(Qt.WhatsThisCursor)
        layout.addWidget(lbl)
        entry = QLineEdit(default)
        entry.setFixedWidth(width)
        entry.setStyleSheet(
            f"QLineEdit {{ background: {C['input']}; color: {C['cyan']}; border: 2px solid {C['border']}; "
            f"border-radius: 8px; font-family: Consolas; font-size: 11pt; font-weight: bold; padding: 2px 4px; }}"
            f"QLineEdit:hover {{ border: 3px solid {C['gold']}; }}"
            f"QLineEdit:focus {{ border: 3px solid {C['gold']}; }}")
        layout.addWidget(entry)
        return entry

    def _get_resolution(self):
        res_map = {
            "480p (832x480)": (832, 480),
            "720p (1280x720)": (1280, 720),
            "1080p (1920x1080)": (1920, 1080),
            "4K (3840x2160)": (3840, 2160),
        }
        return res_map.get(self._resolution.currentText(), (832, 480))

    # ============================================================
    # ACTIONS
    # ============================================================

    def _on_generate(self):
        """Dispara geração ou cria clip vazio."""
        prompt = self._prompt.toPlainText().strip()
        duration = float(self._dur.text() or "5")

        # Prompt vazio = clip vazio
        if not prompt:
            clip = self.project.add_clip(prompt="", position=len(self.project.clips))
            clip.duration = duration
            self.project.save(PROJECTS_DIR)
            self.generation_requested.emit({"action": "empty_clip"})
            return

        w, h = self._get_resolution()

        # Continuidade: extrair último frame do clip anterior como ref
        ref_images = list(self._ref_images)
        if self._continuity.isChecked() and not ref_images:
            last_frame = self._get_last_frame()
            if last_frame:
                ref_images = [last_frame]

        params = {
            "action": "generate",
            "prompt": prompt,
            "duration": duration,
            "steps": int(self._steps.text() or "30"),
            "guidance": float(self._cfg.text() or "5.0"),
            "seed": int(self._seed.text()) if self._seed.text().strip() else None,
            "width": w,
            "height": h,
            "negative": self._negative.toPlainText().strip(),
            "continuity": self._continuity.isChecked(),
            "ref_images": ref_images,
        }

        self._gen_btn.setEnabled(False)
        self._status.setText("Gerando...")
        self._status.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; border: none;")
        self._progress.setValue(15)

        # Limpar campos
        self._prompt.clear()
        self._seed.clear()

        self.generation_requested.emit(params)

    def _get_last_frame(self):
        """Extrai último frame do último clip done como imagem temp."""
        import tempfile
        clips = sorted(self.project.clips, key=lambda c: c.position)
        last_done = None
        for c in reversed(clips):
            if c.status == "done" and c.video_path and Path(c.video_path).exists():
                last_done = c
                break
        if not last_done:
            return None
        try:
            import cv2
            cap = cv2.VideoCapture(str(last_done.video_path))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total - 1)
            ret, frame = cap.read()
            cap.release()
            if ret:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                cv2.imwrite(tmp.name, frame)
                return tmp.name
        except Exception:
            pass
        return None

    # ============================================================
    # CALLBACKS (chamados pelo app após geração)
    # ============================================================

    def on_progress(self, msg):
        self._status.setText(msg)
        if "Step " in msg and "/" in msg:
            try:
                parts = msg.split("Step ")[1].split("/")
                current = int(parts[0])
                total = int(parts[1].split(" ")[0])
                self._progress.setValue(int(current / total * 100))
            except Exception:
                self._progress.setValue(50)
        elif "Salvando" in msg:
            self._progress.setValue(90)

    def on_done(self, clip):
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText(f"Pronto! {clip.duration:.1f}s")
        self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")

    def on_error(self, error):
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText(f"Erro: {error[:50]}")
        self._status.setStyleSheet(f"color: {C['red']}; font-size: 10pt; border: none;")

    def set_clip_data(self, clip):
        """Preenche campos com dados de um clip selecionado."""
        self._prompt.setPlainText(clip.prompt)
        self._dur.setText(str(clip.duration))
        self._seed.setText(str(clip.seed) if clip.seed else "")
