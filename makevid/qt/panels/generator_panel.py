"""Generator Panel Qt - Painel esquerdo para gerar clips e imagens."""

import os
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QProgressBar, QScrollArea, QFrame, QFileDialog,
    QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject, QRect, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QKeySequence
from PySide6.QtWidgets import QApplication


class _PlainTextEdit(QTextEdit):
    """QTextEdit que sempre cola como texto puro, sem formatação HTML."""
    def insertFromMimeData(self, source):
        self.insertPlainText(source.text())

from makevid.qt.theme import C
from makevid.qt.widgets import BrowserTabBar, GlassButton, SectionLabel
from makevid.config import PROJECTS_DIR


class GeneratorPanel(QWidget):
    """Painel de geração de clips (modo texto/imagem/motion)."""

    generation_requested = Signal(dict)  # emite params de geração

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self._ref_images = []
        self.setMinimumWidth(250)

        self._build_ui()
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        self._tab_bar = BrowserTabBar(["GERAR CLIP", "GERAR IMAGEM"], self)
        self._tab_bar.tab_clicked.connect(self._switch_tab)
        outer.addWidget(self._tab_bar)
        outer.setSpacing(0)

        self._tab_stack = QStackedWidget()
        self._tab_stack.setStyleSheet(
            f"QStackedWidget {{ background: {__import__('makevid.qt.theme', fromlist=['C']).C['glass']}; "
            f"border: 1px solid rgba(255,255,255,0.06); border-top: none; "
            f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}"
        )
        self._tab_stack.addWidget(self._build_clip_tab())   # 0
        self._tab_stack.addWidget(self._build_image_tab())  # 1
        outer.addWidget(self._tab_stack)

        # Token frames (hidden, aparecem inline no scroll quando necessario)
        self._token_frame = None
        self._fs_token_frame = None
        self._auto_retry_generation = False

    def _switch_tab(self, idx):
        self._tab_stack.setCurrentIndex(idx)
        self._tab_bar.set_active(idx)

    def _show_token_prompt(self, auto_generate=False):
        """Mostra campo inline no scroll para inserir HF token. auto_generate=True faz retry apos salvar."""
        if self._token_frame:
            try:
                self._token_frame.hide()
                self._token_frame.deleteLater()
            except Exception:
                pass

        self._auto_retry_generation = auto_generate
        self._token_frame = QFrame()
        self._token_frame.setStyleSheet(f"background: {C['glass']}; border: 1px solid {C['primary']}; border-radius: 10px;")
        tf_l = QVBoxLayout(self._token_frame)
        tf_l.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel("TOKEN HUGGINGFACE")
        lbl.setStyleSheet(f"color: {C['primary']}; font-size: 10pt; font-weight: bold;")
        tf_l.addWidget(lbl)
        sub = QLabel("Crie em: huggingface.co/settings/tokens")
        sub.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        tf_l.addWidget(sub)
        self._token_entry = QLineEdit()
        self._token_entry.setPlaceholderText("hf_...")
        self._token_entry.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['primary']}; border-radius: 8px; padding: 4px; font-family: Consolas; font-size: 10pt;")
        self._token_entry.returnPressed.connect(self._save_hf_token)
        tf_l.addWidget(self._token_entry)
        btns = QHBoxLayout()
        btn_save = QPushButton("SALVAR")
        btn_save.setStyleSheet(f"background: {C['primary']}; color: {C['text']}; font-weight: bold; border-radius: 6px; padding: 4px 12px;")
        btn_save.clicked.connect(self._save_hf_token)
        btns.addWidget(btn_save)
        btn_x = QPushButton("X")
        btn_x.setFixedSize(28, 28)
        btn_x.setObjectName("closeBtn")
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
            self._token_frame.hide()
            self._token_frame.deleteLater()
            self._token_frame = None

    def _show_freesound_prompt(self, on_saved=None):
        """Mostra campo inline para Freesound API key (mesmo padrao do HF token)."""
        if self._fs_token_frame:
            try:
                self._fs_token_frame.hide()
                self._fs_token_frame.deleteLater()
            except Exception:
                pass

        self._fs_on_saved = on_saved
        self._fs_token_frame = QFrame()
        self._fs_token_frame.setStyleSheet(f"background: {C['glass']}; border: 1px solid {C['primary']}; border-radius: 10px;")
        fl = QVBoxLayout(self._fs_token_frame)
        fl.setContentsMargins(10, 8, 10, 8)
        lbl = QLabel("FREESOUND API KEY")
        lbl.setStyleSheet(f"color: {C['primary']}; font-size: 10pt; font-weight: bold;")
        fl.addWidget(lbl)
        sub = QLabel("Crie em: freesound.org/apiv2/apply")
        sub.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        fl.addWidget(sub)
        self._fs_entry = QLineEdit()
        self._fs_entry.setPlaceholderText("sua_api_key_aqui")
        self._fs_entry.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['primary']}; border-radius: 8px; padding: 4px; font-family: Consolas; font-size: 10pt;")
        self._fs_entry.returnPressed.connect(self._save_fs_key)
        fl.addWidget(self._fs_entry)
        btns = QHBoxLayout()
        btn_save = QPushButton("SALVAR")
        btn_save.setStyleSheet(f"background: {C['primary']}; color: {C['text']}; font-weight: bold; border-radius: 6px; padding: 4px 12px;")
        btn_save.clicked.connect(self._save_fs_key)
        btns.addWidget(btn_save)
        btn_x = QPushButton("X")
        btn_x.setFixedSize(28, 28)
        btn_x.setObjectName("closeBtn")
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
            self._fs_token_frame.hide()
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
        L.addWidget(SectionLabel("MODO"))
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(4, 0, 4, 4)
        mode_layout.setSpacing(16)
        self._mode_group = QButtonGroup(self)
        self._rb_text = QRadioButton("Texto")
        self._rb_image = QRadioButton("Img+Texto")
        self._rb_motion = QRadioButton("Motion")
        self._rb_text.setChecked(True)

        radio_qss = (
            f"QRadioButton {{ color: {C['text']}; font-family: 'Segoe UI'; font-size: 10pt; spacing: 6px; background: transparent; }}"
            f"QRadioButton::indicator {{ width: 13px; height: 13px; border-radius: 7px; border: 2px solid {C['primary']}; background: transparent; }}"
            f"QRadioButton::indicator:checked {{ background: {C['primary']}; border: 2px solid {C['primary']}; }}"
            f"QRadioButton::indicator:hover {{ border: 2px solid {C['secondary']}; }}")
        radio_motion_qss = (
            f"QRadioButton {{ color: {C['text']}; font-family: 'Segoe UI'; font-size: 10pt; spacing: 6px; background: transparent; }}"
            f"QRadioButton::indicator {{ width: 13px; height: 13px; border-radius: 7px; border: 2px solid {C['track_sfx']}; background: transparent; }}"
            f"QRadioButton::indicator:checked {{ background: {C['track_sfx']}; border: 2px solid {C['track_sfx']}; }}"
            f"QRadioButton::indicator:hover {{ border: 2px solid {C['accent']}; }}")

        self._rb_text.setStyleSheet(radio_qss)
        self._rb_image.setStyleSheet(radio_qss)
        self._rb_motion.setStyleSheet(radio_motion_qss)

        for rb in (self._rb_text, self._rb_image, self._rb_motion):
            self._mode_group.addButton(rb)
            mode_layout.addWidget(rb)
        mode_layout.addStretch()
        self._mode_group.buttonClicked.connect(self._on_mode_changed)
        L.addLayout(mode_layout)

        # REF IMAGES - visivel apenas em modo Img+Texto
        self._ref_frame = QFrame()
        self._ref_frame.setStyleSheet(
            f"QFrame {{ background: {C['glass']}; border: 1px solid {C['accent']}; border-radius: 12px; }}"
        )
        ref_layout = QVBoxLayout(self._ref_frame)
        ref_layout.setContentsMargins(10, 8, 10, 10)
        ref_layout.setSpacing(6)

        # Header: titulo + botoes
        ref_header = QHBoxLayout()
        ref_title = QLabel("IMAGENS DE REFERÊNCIA")
        ref_title.setStyleSheet(f"color: {C['accent']}; font-size: 8pt; font-weight: bold; border: none; background: transparent;")
        ref_header.addWidget(ref_title)
        ref_header.addStretch()
        btn_add_ref = QPushButton("+ Adicionar")
        btn_add_ref.setFixedHeight(24)
        btn_add_ref.setStyleSheet(
            f"QPushButton {{ background: {C['primary']}; color: {C['dark_text']}; font-weight: bold; font-size: 8pt; "
            f"border: none; border-radius: 6px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background: {C['secondary']}; }}")
        btn_add_ref.clicked.connect(self._add_ref_image)
        ref_header.addWidget(btn_add_ref)
        btn_clear_ref = QPushButton("Limpar")
        btn_clear_ref.setFixedHeight(24)
        btn_clear_ref.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
            f"border: 1px solid {C['border']}; border-radius: 6px; padding: 0 8px; }}"
            f"QPushButton:hover {{ color: {C['danger']}; border-color: {C['danger']}; }}")
        btn_clear_ref.clicked.connect(self._clear_ref_images)
        ref_header.addWidget(btn_clear_ref)
        ref_layout.addLayout(ref_header)

        # Area de thumbs com scroll horizontal
        self._ref_scroll = QScrollArea()
        self._ref_scroll.setFixedHeight(86)
        self._ref_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._ref_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._ref_scroll.setWidgetResizable(False)
        self._ref_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._ref_scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: 1px dashed {C['border']}; border-radius: 8px; }}"
            f"QScrollBar:horizontal {{ height: 4px; background: {C['card']}; border-radius: 2px; margin: 0; }}"
            f"QScrollBar::handle:horizontal {{ background: {C['primary']}; border-radius: 2px; }}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}")
        self._ref_thumbs_widget = QWidget()
        self._ref_thumbs_widget.setStyleSheet("background: transparent;")
        self._ref_thumbs_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._ref_thumbs_layout = QHBoxLayout(self._ref_thumbs_widget)
        self._ref_thumbs_layout.setContentsMargins(6, 4, 6, 4)
        self._ref_thumbs_layout.setSpacing(6)
        self._ref_thumbs_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._ref_scroll.setWidget(self._ref_thumbs_widget)
        ref_layout.addWidget(self._ref_scroll)

        self._ref_frame.hide()
        L.addWidget(self._ref_frame)

        # MOTION SECTION (hidden by default)
        self._motion_frame = QFrame()
        self._prompt = _PlainTextEdit()
        self._prompt.setFixedHeight(90)
        self._prompt.setPlaceholderText("Descreva a cena...")
        self._prompt.setToolTip("Descreva o que voce quer ver no video.\nEx: 'Um guerreiro caminhando por uma floresta sombria'")
        self._prompt.setStyleSheet(
            f"QTextEdit {{ background: {C['input']}; color: {C['accent']}; border: 1px solid {C['glass_border']}; "
            f"border-radius: 10px; font-family: Consolas; font-size: 11pt; font-weight: bold; }}"
            f"QTextEdit:hover {{ border: 1px solid {C['primary']}; }}"
            f"QTextEdit:focus {{ border: 2px solid {C['primary']}; }}")
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
            f"QTextEdit {{ background: {C['input']}; color: {C['text3']}; border: 1px solid {C['glass_border']}; "
            f"border-radius: 10px; font-family: Consolas; font-size: 10pt; }}"
            f"QTextEdit:hover {{ border: 1px solid {C['primary']}; }}"
            f"QTextEdit:focus {{ border: 1px solid {C['primary']}; }}")
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
        L.addWidget(SectionLabel("PARAMETROS"))
        params_layout = QVBoxLayout()
        params_layout.setContentsMargins(4, 0, 4, 0)
        params_layout.setSpacing(6)
        r1 = QHBoxLayout()
        self._dur = self._param_entry(r1, "Duracao", "5", 45, tooltip="Duracao do video em segundos")
        self._steps = self._param_entry(r1, "Steps", "30", 45, tooltip="Passos de inferencia.\nMais steps = mais qualidade, mais lento")
        r1.addStretch()
        params_layout.addLayout(r1)
        r2 = QHBoxLayout()
        self._cfg = self._param_entry(r2, "CFG", "5.0", 55, tooltip="Classifier-Free Guidance.\nBaixo (1-3): criativo\nMedio (4-7): equilibrado\nAlto (8+): segue o prompt")
        r2.addStretch()
        params_layout.addLayout(r2)
        r3 = QHBoxLayout()
        self._seed = self._param_entry(r3, "Seed", "", 65, tooltip="Semente para reproducibilidade.\nMesma seed + mesmo prompt = mesmo resultado")
        self._seed.setPlaceholderText("random")
        r3.addStretch()
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
        r4.addWidget(self._resolution)
        r4.addStretch()
        params_layout.addLayout(r4)
        L.addLayout(params_layout)

        # BOTAO GERAR
        self._gen_btn = GlassButton("GERAR CLIP", accent=True, height=44)
        self._gen_btn.clicked.connect(self._on_generate)
        L.addWidget(self._gen_btn)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setFixedHeight(30)
        self._cancel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['danger']}; font-weight: bold; "
            f"font-size: 9pt; border: 1px solid {C['danger']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {C['danger']}; color: {C['dark']}; }}")
        self._cancel_btn.clicked.connect(self._cancel_clip_generation)
        self._cancel_btn.hide()
        L.addWidget(self._cancel_btn)

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

        L.addWidget(SectionLabel("GERAR IMAGEM"))
        L.addWidget(self._sub_label("Gera imagem estatica via HF API / FLUX / Local"))

        # Prompt
        L.addWidget(self._sub_label("PROMPT"))
        self._img_prompt = _PlainTextEdit()
        self._img_prompt.setFixedHeight(70)
        self._img_prompt.setPlaceholderText("Descreva a imagem...")
        self._img_prompt.setStyleSheet(
            f"background: {C['input']}; color: {C['accent']}; border: 1px solid {C['glass_border']}; "
            f"border-radius: 10px; font-family: Consolas; font-size: 11pt; font-weight: bold;")
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
        self._img_engine.addItems(["FLUX.1-schnell (rapido)", "FLUX.1-schnell (HD)"])
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
        self._img_gen_btn = GlassButton("GERAR IMAGEM", accent=True, height=40)
        self._img_gen_btn.clicked.connect(self._on_generate_image)
        L.addWidget(self._img_gen_btn)

        self._img_cancel_btn = QPushButton("Cancelar")
        self._img_cancel_btn.setFixedHeight(30)
        self._img_cancel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C['danger']}; font-weight: bold; "
            f"font-size: 9pt; border: 1px solid {C['danger']}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {C['danger']}; color: {C['dark']}; }}")
        self._img_cancel_btn.clicked.connect(self._cancel_image_generation)
        self._img_cancel_btn.hide()
        L.addWidget(self._img_cancel_btn)

        # Status
        self._img_status = QLabel("")
        self._img_status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        L.addWidget(self._img_status)

        # Progress bar para tab de imagem
        self._img_progress = QProgressBar()
        self._img_progress.setFixedHeight(6)
        self._img_progress.setRange(0, 100)
        self._img_progress.setValue(0)
        self._img_progress.setTextVisible(False)
        self._img_progress.setStyleSheet(
            f"QProgressBar {{ background: {C['card']}; border: none; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background: {C['cyan']}; border-radius: 3px; }}")
        L.addWidget(self._img_progress)
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
        """Reconstroi thumbnails flutuantes com visual glass."""
        while self._ref_thumbs_layout.count():
            child = self._ref_thumbs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._ref_images:
            placeholder = QLabel("Clique em + Adicionar ou arraste imagens aqui")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(f"color: {C['text3']}; font-size: 8pt; background: transparent; border: none;")
            # Largura do scroll area para o placeholder preencher
            sw = max(200, self._ref_scroll.viewport().width())
            self._ref_thumbs_widget.setFixedSize(sw, 78)
            self._ref_thumbs_layout.addWidget(placeholder)
            return

        CARD = 72
        GAP = 6
        PAD = 12
        total_w = PAD + len(self._ref_images) * (CARD + GAP)
        self._ref_thumbs_widget.setFixedSize(total_w, 78)

        for p in self._ref_images:
            card = QFrame()
            card.setFixedSize(CARD, CARD)
            card.setStyleSheet(
                f"QFrame {{ background: {C['card']}; border: 1px solid {C['primary']}; border-radius: 8px; }}"
                f"QFrame:hover {{ border: 1px solid {C['accent']}; }}")

            thumb = QLabel(card)
            thumb.setFixedSize(CARD, CARD)
            pix = QPixmap(p).scaled(CARD, CARD, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            if pix.width() > CARD or pix.height() > CARD:
                ox = (pix.width() - CARD) // 2
                oy = (pix.height() - CARD) // 2
                pix = pix.copy(ox, oy, CARD, CARD)
            thumb.setPixmap(pix)
            thumb.move(0, 0)

            btn_x = QPushButton("X", card)
            btn_x.setObjectName("closeBtn")
            btn_x.setFixedSize(18, 18)
            btn_x.move(CARD - 20, 2)
            btn_x.clicked.connect(lambda ck=False, path=p: self._remove_ref_image(path))

            self._ref_thumbs_layout.addWidget(card)

    # ============================================================
    # GENERATE IMAGE
    # ============================================================

    def _on_generate_image(self):
        """Gera imagem e salva como clip estatico na timeline."""
        prompt = self._img_prompt.toPlainText().strip()
        if not prompt:
            self._img_status.setText("Digite um prompt")
            return

        # Garante que projeto é persistido antes de usar self.project
        self.generation_requested.emit({"action": "ensure_project"})
        self._img_cancelled = False
        self._img_gen_btn.setEnabled(False)
        self._img_cancel_btn.show()
        self._img_status.setText("Gerando imagem...")
        self._img_status.setStyleSheet(f"color: {C['gold']}; font-size: 9pt;")

        engine = self._img_engine.currentText()
        res_text = self._img_resolution.currentText()
        w, h = [int(x) for x in res_text.split("x")]
        duration = float(self._img_dur.text() or "5")
        token = os.environ.get("HF_TOKEN", "")

        # Verificar token
        if not token:
            from makevid.core.hf_api import _get_token
            token = _get_token()
            if not token:
                self._img_gen_btn.setEnabled(True)
                self._img_status.setText("Insira o token HF")
                self._img_status.setStyleSheet(f"color: {C['gold']}; font-size: 9pt;")
                self._show_token_prompt(auto_generate=True)
                return

        # Animacao de progress com tempo decorrido
        if hasattr(self, '_img_progress_timer') and self._img_progress_timer:
            self._img_progress_timer.stop()
            self._img_progress_timer = None
        self._img_progress_timer = QTimer(self)
        self._img_progress_timer.setInterval(500)
        self._img_start_time = __import__('time').time()
        _progress_val = [5]
        _done = [False]
        def _animate_progress():
            if _done[0]:
                return
            import time as _t
            elapsed = _t.time() - self._img_start_time
            if _progress_val[0] < 90:
                _progress_val[0] += 1
                self._img_progress.setValue(_progress_val[0])
            m, s = int(elapsed) // 60, int(elapsed) % 60
            self._img_status.setText(f"Gerando... {m:02d}:{s:02d}")
            self._img_status.setStyleSheet(f"color: {C['gold']}; font-size: 9pt;")
        self._img_progress_timer.timeout.connect(_animate_progress)
        self._img_progress.setValue(5)
        self._img_progress_timer.start()

        def run():
            try:
                actual_token = token or os.environ.get("HF_TOKEN", "")

                import requests, tempfile, io
                from PIL import Image
                from pathlib import Path
                from makevid.config import OUTPUTS_DIR

                url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                headers = {"Authorization": f"Bearer {actual_token}"}
                import random
                payload = {"inputs": prompt, "parameters": {"seed": random.randint(0, 2**32 - 1)}}
                print(f"[IMG] Gerando: '{prompt[:40]}' token={actual_token[:10]}...")
                r = requests.post(url, headers=headers, json=payload, timeout=120)
                print(f"[IMG] Status={r.status_code} size={len(r.content)}")

                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    img = Image.open(io.BytesIO(r.content)).resize((w, h))
                    out_dir = OUTPUTS_DIR / self.project.id
                    out_dir.mkdir(parents=True, exist_ok=True)
                    img_path = out_dir / f"img_{int(__import__('time').time())}.png"
                    img.save(str(img_path))

                    mp4_path = img_path.with_suffix(".mp4")
                    self._image_to_static_video(str(img_path), str(mp4_path), duration, 16, w, h)

                    clip = self.project.add_clip(prompt=prompt, position=len(self.project.clips))
                    clip.video_path = str(mp4_path)
                    clip.duration = duration
                    clip.status = "done"
                    self.project.save(PROJECTS_DIR)

                    import time as _t
                    elapsed = _t.time() - self._img_start_time

                    def _on_img_done(elapsed=elapsed, clip_id=clip.id):
                        _done[0] = True
                        if hasattr(self, '_img_progress_timer') and self._img_progress_timer:
                            self._img_progress_timer.stop()
                            self._img_progress_timer = None
                        if self._img_cancelled:
                            self._reset_img_status()
                            return
                        from makevid.qt.timeline.clip_item import ClipGraphicsItem
                        if ClipGraphicsItem._thumb_cache:
                            ClipGraphicsItem._thumb_cache.invalidate(clip_id)
                        self.generation_requested.emit({"action": "image_done"})
                        self._img_progress.setValue(100)
                        self._img_status.setText(f"\u2714 Pronto! {w}x{h} | {elapsed:.1f}s")
                        self._img_status.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")
                        self._img_gen_btn.setEnabled(True)
                        self._img_cancel_btn.hide()
                        self._img_prompt.clear()
                        QTimer.singleShot(3000, self._reset_img_status)
                    QTimer.singleShot(0, _on_img_done)
                else:
                    err = r.text[:60] if r.text else str(r.status_code)
                    def _on_img_fail():
                        _done[0] = True
                        if hasattr(self, '_img_progress_timer') and self._img_progress_timer:
                            self._img_progress_timer.stop()
                            self._img_progress_timer = None
                        self._img_progress.setValue(0)
                        self._img_cancel_btn.hide()
                        self._img_gen_btn.setEnabled(True)
                        if self._img_cancelled:
                            self._img_status.setText("Cancelado")
                            self._img_status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
                        else:
                            self._img_status.setText(f"Erro: {err}")
                            self._img_status.setStyleSheet(f"color: {C['danger']}; font-size: 9pt;")
                            if "401" in err or "403" in err or "token" in err.lower():
                                self._show_token_prompt(auto_generate=True)
                        QTimer.singleShot(4000, self._reset_img_status)
                    QTimer.singleShot(0, _on_img_fail)
            except Exception as e:
                err_msg = str(e)[:40]
                def _on_img_error():
                        _done[0] = True
                        if hasattr(self, '_img_progress_timer') and self._img_progress_timer:
                            self._img_progress_timer.stop()
                            self._img_progress_timer = None
                    self._img_progress.setValue(0)
                    self._img_cancel_btn.hide()
                    self._img_gen_btn.setEnabled(True)
                    if self._img_cancelled:
                        self._img_status.setText("Cancelado")
                        self._img_status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
                    else:
                        self._img_status.setText(f"Erro: {err_msg}")
                        self._img_status.setStyleSheet(f"color: {C['danger']}; font-size: 9pt;")
                        if "401" in str(e) or "token" in str(e).lower() or "unauthorized" in str(e).lower():
                            self._show_token_prompt(auto_generate=True)
                    QTimer.singleShot(4000, self._reset_img_status)
                QTimer.singleShot(0, _on_img_error)

        threading.Thread(target=run, daemon=True).start()

    def _image_to_static_video(self, img_path, mp4_path, duration, fps, w, h):
        """Converte imagem em video estatico."""
        import cv2
        img = cv2.imread(img_path)
        img = cv2.resize(img, (w, h))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(mp4_path, fourcc, fps, (w, h))
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
            f"QLineEdit {{ background: {C['input']}; color: {C['accent']}; border: 1px solid {C['glass_border']}; "
            f"border-radius: 8px; font-family: Consolas; font-size: 11pt; font-weight: bold; padding: 2px 4px; }}"
            f"QLineEdit:hover {{ border: 1px solid {C['primary']}; }}"
            f"QLineEdit:focus {{ border: 2px solid {C['primary']}; }}")
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
            self.generation_requested.emit({"action": "empty_clip", "duration": duration})
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
        self._cancel_btn.show()
        self._status.setText("Gerando...")
        self._status.setStyleSheet(f"color: {C['primary']}; font-size: 10pt; border: none;")
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

    def _cancel_clip_generation(self):
        self._cancel_btn.hide()
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText("Cancelado")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 10pt; border: none;")
        QTimer.singleShot(3000, self._reset_clip_status)

    def _reset_clip_status(self):
        self._cancel_btn.hide()
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText("Pronto")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 10pt; border: none;")

    def on_done(self, clip):
        self._cancel_btn.hide()
        self._gen_btn.setEnabled(True)
        self._progress.setValue(100)
        self._status.setText(f"\u2714 Pronto! {clip.duration:.1f}s")
        self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; border: none;")
        QTimer.singleShot(3000, self._reset_clip_status)

    def _cancel_image_generation(self):
        self._img_cancelled = True
        self._img_cancel_btn.hide()
        self._img_gen_btn.setEnabled(True)
        if hasattr(self, '_img_progress_timer'):
            self._img_progress_timer.stop()
        self._img_progress.setValue(0)
        self._img_status.setText("Cancelado")
        self._img_status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        QTimer.singleShot(3000, self._reset_img_status)

    def _reset_img_status(self):
        self._img_cancel_btn.hide()
        self._img_gen_btn.setEnabled(True)
        self._img_progress.setValue(0)
        self._img_status.setText("")

    def on_error(self, error):
        self._cancel_btn.hide()
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText(f"Erro: {error[:50]}")
        self._status.setStyleSheet(f"color: {C['danger']}; font-size: 10pt; border: none;")
        QTimer.singleShot(5000, self._reset_clip_status)

    def set_clip_data(self, clip):
        """Preenche campos com dados de um clip selecionado."""
        self._prompt.setPlainText(clip.prompt)
        self._dur.setText(str(clip.duration))
        self._seed.setText(str(clip.seed) if clip.seed else "")

    def _on_project_changed(self, proj):
        self.project = proj
