"""Characters tab do Style Panel."""

import uuid
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QFileDialog, QApplication,
    QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR
from makevid.qt.panels.style.widgets import AutoResizeTextEdit, FlexTextEdit


class CharactersMixin:
    """Metodos de personagens do StylePanel."""

    def _build_characters_tab(self):
        w = QWidget()
        L = QVBoxLayout(w)
        L.setContentsMargins(10, 10, 10, 10)
        L.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet(
            "QSplitter::handle { background: #2a2a4a; }"
            "QSplitter::handle:hover { background: #ffd700; }")
        # Instalar event filter para hover expand (como timeline)
        self._char_splitter = splitter

        # Lista esquerda
        left = QFrame()
        left.setMinimumWidth(200)
        left.setObjectName("charLeftPanel")
        left.setStyleSheet(f"QFrame#charLeftPanel {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px; }}")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)

        lh = QHBoxLayout()
        title_lbl = QLabel("PERSONAGENS")
        title_lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt; font-weight: bold; border: none; background: none;")
        lh.addWidget(title_lbl)
        lh.addStretch()
        btn_imp = QPushButton("\u2913")
        btn_imp.setFixedSize(32, 28)
        btn_imp.setToolTip("Importar personagem de arquivo .txt")
        btn_imp.setStyleSheet(f"background: {C['card']}; color: #44cc88; font-weight: bold; font-size: 14pt; border: 1px solid #44cc88; border-radius: 4px; padding: 0;")
        btn_imp.clicked.connect(self._import_char_txt)
        lh.addWidget(btn_imp)
        btn_add = QPushButton("+")
        btn_add.setFixedSize(32, 28)
        btn_add.setStyleSheet(f"background: {C['card']}; color: {C['gold']}; font-weight: bold; font-size: 14pt; border: 1px solid {C['gold']}; border-radius: 4px; padding: 0;")
        btn_add.clicked.connect(self._add_character)
        lh.addWidget(btn_add)
        ll.addLayout(lh)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['cyan']}; border: none;")
        ll.addWidget(sep)

        self._char_list_scroll = QScrollArea()
        self._char_list_scroll.setWidgetResizable(True)
        self._char_list_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._char_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._selected_char_id = None
        self._rebuild_char_cards()
        ll.addWidget(self._char_list_scroll)
        splitter.addWidget(left)

        # Editor direito
        self._char_editor_scroll = QScrollArea()
        self._char_editor_scroll.setWidgetResizable(True)
        self._char_editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._char_editor_scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {C['border']}; border-radius: 6px; background: {C['card']}; }}")
        self._char_editor_widget = QWidget()
        self._char_editor_widget.setStyleSheet(f"background: {C['card']};")
        self._char_editor_layout = QVBoxLayout(self._char_editor_widget)
        self._char_editor_layout.setContentsMargins(12, 12, 12, 12)
        self._char_editor_layout.setSpacing(6)
        self._char_editor_scroll.setWidget(self._char_editor_widget)
        splitter.addWidget(self._char_editor_scroll)

        splitter.setSizes([260, 600])
        # Event filter para hover expand no handle (como timeline)
        if splitter.count() >= 2:
            handle = splitter.handle(1)
            handle.setStyleSheet("background: #2a2a4a;")
            handle.installEventFilter(self._make_splitter_filter(splitter, handle))
        L.addWidget(splitter)

        self._char_fields = {}
        # Pre-selecionar primeiro personagem se existir
        if self.project.characters:
            self._selected_char_id = self.project.characters[0].id
            self._rebuild_char_cards()
            self._build_char_editor(self.project.characters[0])
        else:
            self._show_empty_editor()
        return w

    def _rebuild_char_cards(self):
        old = self._char_list_scroll.widget()
        if old:
            old.setParent(None)
            old.deleteLater()

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 4, 0, 4)
        vl.setSpacing(3)

        chars = self.project.characters
        if not chars:
            lbl = QLabel("Nenhum personagem.\nClique + para criar.")
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 9pt; border: none; background: none;")
            lbl.setAlignment(Qt.AlignCenter)
            vl.addWidget(lbl)
        else:
            for char in chars:
                selected = (char.id == self._selected_char_id)
                card = QFrame()
                card.setObjectName("charCard")
                card.setCursor(Qt.PointingHandCursor)
                card.setMinimumHeight(54)
                if selected:
                    card.setStyleSheet(
                        f"QFrame#charCard {{ background: {C['panel']}; border: 2px solid {C['cyan']}; border-radius: 6px; }}"
                        f"QFrame#charCard QLabel {{ border: none; background: none; }}"
                        f"QFrame#charCard QWidget {{ background: none; }}")
                else:
                    card.setStyleSheet(
                        f"QFrame#charCard {{ background: #0d0f1a; border: 1px solid {C['border']}; border-radius: 6px; }}"
                        f"QFrame#charCard:hover {{ background: #12162e; border: 2px solid {C['gold']}; margin-left: 4px; }}"
                        f"QFrame#charCard QLabel {{ border: none; background: none; }}"
                        f"QFrame#charCard QWidget {{ background: none; }}")
                cl = QHBoxLayout(card)
                cl.setContentsMargins(6, 6, 8, 6)
                cl.setSpacing(10)

                # Thumbnail 48x48
                ref_path = getattr(char, 'reference_image', '') or ''
                first_img = ref_path.split("|")[0].strip() if ref_path else ''
                if first_img and Path(first_img).exists():
                    pixmap = QPixmap(first_img)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb = QLabel()
                        thumb.setPixmap(pixmap)
                        thumb.setFixedSize(48, 48)
                        thumb.setStyleSheet(f"border: 2px solid {C['cyan']}; border-radius: 6px; padding: 1px;")
                        cl.addWidget(thumb)
                    else:
                        cl.addWidget(self._char_icon())
                else:
                    cl.addWidget(self._char_icon())

                info_w = QWidget()
                info_l = QVBoxLayout(info_w)
                info_l.setContentsMargins(0, 0, 0, 0)
                info_l.setSpacing(1)
                name_lbl = QLabel(char.name or "(sem nome)")
                name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 10pt; font-weight: bold;")
                info_l.addWidget(name_lbl)
                summary = getattr(char, 'summary', '') or getattr(char, 'description', '') or ''
                sub_text = (summary[:28] + "...") if len(summary) > 28 else summary
                if sub_text:
                    sub_lbl = QLabel(sub_text)
                    sub_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
                    info_l.addWidget(sub_lbl)
                cl.addWidget(info_w)
                cl.addStretch()
                card.mousePressEvent = lambda e, c=char: self._select_char(c)
                vl.addWidget(card)

        vl.addStretch()
        self._char_list_scroll.setWidget(container)

    def _char_icon(self):
        icon = QLabel("\U0001f464")
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 20pt;")
        return icon

    def _refresh_char_list(self):
        self._rebuild_char_cards()

    def _select_char(self, char):
        self._selected_char_id = char.id
        self._rebuild_char_cards()
        self._build_char_editor(char)

    def _show_empty_editor(self):
        self._clear_editor()
        lbl = QLabel("Selecione ou crie um personagem")
        lbl.setStyleSheet(f"color: {C['text3']}; font-size: 11pt; border: none; background: none;")
        lbl.setAlignment(Qt.AlignCenter)
        self._char_editor_layout.addStretch()
        self._char_editor_layout.addWidget(lbl)
        self._char_editor_layout.addStretch()

    def _clear_editor(self):
        L = self._char_editor_layout
        while L.count():
            item = L.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    child = sub.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def _add_character(self):
        from makevid.core.project import Character
        char = Character(id=str(uuid.uuid4())[:8], name="Novo Personagem")
        self.project.characters.append(char)
        self.project.save(PROJECTS_DIR)
        self._selected_char_id = char.id
        self._rebuild_char_cards()
        self._build_char_editor(char)

    def _build_char_editor(self, char):
        self._clear_editor()
        L = self._char_editor_layout

        hdr = QLabel("FICHA DE PERSONAGEM")
        hdr.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold; border: none; background: none;")
        L.addWidget(hdr)
        gold_sep = QFrame()
        gold_sep.setFixedHeight(1)
        gold_sep.setStyleSheet(f"background: {C['gold']}; border: none;")
        L.addWidget(gold_sep)

        # Imagens de referencia
        img_frame = QFrame()
        img_frame.setObjectName("charImgSection")
        img_frame.setStyleSheet(
            f"QFrame#charImgSection {{ background: {C['panel']}; border: 1px solid {C['cyan']}; border-radius: 4px; }}"
            f"QFrame#charImgSection QLabel {{ border: none; background: none; }}"
            f"QFrame#charImgSection QPushButton {{ border: none; background: none; }}")
        img_l = QVBoxLayout(img_frame)
        img_l.setContentsMargins(8, 6, 8, 8)
        img_l.setSpacing(4)

        img_hdr = QHBoxLayout()
        img_hdr.addWidget(QLabel("IMAGENS DE REFERENCIA"))
        img_hdr.itemAt(0).widget().setStyleSheet(f"color: {C['cyan']}; font-size: 9pt; font-weight: bold;")
        img_hdr.addStretch()
        btn_add_img = QPushButton("+ IMG")
        btn_add_img.setFixedHeight(22)
        btn_add_img.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-size: 8pt; font-weight: bold; border: 1px solid {C['cyan']}; border-radius: 4px; padding: 0 8px;")
        btn_add_img.clicked.connect(lambda: self._add_ref_image(char))
        img_hdr.addWidget(btn_add_img)
        img_l.addLayout(img_hdr)

        ref_paths = self._get_ref_paths(char)
        if not ref_paths:
            no_img = QLabel("Nenhuma imagem. Clique + IMG.")
            no_img.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
            img_l.addWidget(no_img)
        else:
            img_grid = QGridLayout()
            img_grid.setSpacing(4)
            for i, p in enumerate(ref_paths):
                cell = QFrame()
                cell.setFixedSize(70, 70)
                cell.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px;")
                cell_l = QVBoxLayout(cell)
                cell_l.setContentsMargins(2, 2, 2, 2)
                if Path(p).exists():
                    pixmap = QPixmap(p)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb = QLabel()
                        thumb.setPixmap(pixmap)
                        thumb.setAlignment(Qt.AlignCenter)
                        cell_l.addWidget(thumb)
                    else:
                        cell_l.addWidget(QLabel("?"))
                else:
                    cell_l.addWidget(QLabel("?"))
                btn_rm = QPushButton("X")
                btn_rm.setObjectName("closeBtn")
                btn_rm.setFixedSize(18, 18)
                btn_rm.clicked.connect(lambda checked=False, idx=i, c=char: self._remove_ref_image(c, idx))
                btn_rm.move(50, 2)
                btn_rm.setParent(cell)
                img_grid.addWidget(cell, i // 4, i % 4)
            img_l.addLayout(img_grid)
        L.addWidget(img_frame)

        # Campos
        from PySide6.QtWidgets import QFormLayout
        self._char_textboxes = {}
        fields = [
            ("name", "NOME", "entry"), ("char_type", "TIPO", "entry"),
            ("summary", "RESUMO", "text"), ("demographic", "PERFIL DEMOGRAFICO", "entry"),
            ("age", "IDADE", "entry"), ("height_build", "ALTURA E CONSTITUICAO", "entry"),
            ("proportion_style", "PROPORCAO", "entry"), ("face_design", "ROSTO E CABECA", "text"),
            ("hair_head", "CABELO / CABECA", "entry"), ("skin_surface", "PELE / SUPERFICIE", "text"),
            ("costume", "TRAJE / ARMADURA", "text"), ("asymmetric_details", "DETALHES ASSIMETRICOS", "text"),
            ("accessories", "ACESSORIOS", "entry"), ("continuity_locks", "CONTINUIDADE", "text"),
            ("visual_style", "ESTILO VISUAL", "entry"),
        ]
        for key, label, wtype in fields:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none; background: none;")
            L.addWidget(lbl)
            val = str(getattr(char, key, "") or "")
            box = FlexTextEdit(val, C['cyan'], C['border'])
            L.addWidget(box)
            self._char_textboxes[key] = box

        # Voz
        from makevid.core.voice_engine import VoiceProfile
        profile = VoiceProfile.from_dict(char.voice_profile) if getattr(char, 'voice_profile', None) else VoiceProfile()
        if getattr(char, 'voice_id', '') and not char.voice_profile:
            profile.voice_id = char.voice_id

        voz_lbl = QLabel("\U0001f3a4 VOZ DO PERSONAGEM")
        voz_lbl.setStyleSheet(f"color: {C['gold']}; font-size: 10pt; font-weight: bold; border: none; background: none;")
        L.addWidget(voz_lbl)

        voice_frame = QFrame()
        voice_frame.setObjectName("charVoiceSection")
        voice_frame.setStyleSheet(
            f"QFrame#charVoiceSection {{ background: {C['panel']}; border: 1px solid {C['cyan']}; border-radius: 4px; }}"
            f"QFrame#charVoiceSection QLabel {{ border: none; background: none; }}")
        vf_l = QVBoxLayout(voice_frame)
        vf_l.setContentsMargins(8, 8, 8, 8)
        vf_l.setSpacing(4)

        engine_text = profile.engine.upper()
        voice_text = profile.voice_id.split("-")[-1].replace("Neural", "") if "Neural" in profile.voice_id else profile.voice_id[:20]
        info_row = QHBoxLayout()
        info_row.addWidget(self._mini_label(f"Engine: ", C['text3']))
        info_row.addWidget(self._mini_label(engine_text, C['cyan'], bold=True))
        info_row.addWidget(self._mini_label(f"  Voz: ", C['text3']))
        info_row.addWidget(self._mini_label(voice_text, C['gold'], bold=True))
        info_row.addStretch()
        vf_l.addLayout(info_row)

        params_lbl = QLabel(f"Tom: {profile.pitch_base:+d}Hz  |  Vel: {profile.rate_base:+d}%  |  Aspereza: {profile.roughness}%  |  Resp: {profile.breathiness}%")
        params_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        vf_l.addWidget(params_lbl)

        vbtn_row = QHBoxLayout()
        btn_test = QPushButton("\u25b6 Testar")
        btn_test.setFixedHeight(26)
        btn_test.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-weight: bold; border: 1px solid {C['cyan']}; border-radius: 4px; padding: 0 10px;")
        btn_test.clicked.connect(lambda: self._test_voice(char))
        vbtn_row.addWidget(btn_test)
        btn_config = QPushButton("\u2699 CONFIGURAR VOZ")
        btn_config.setFixedHeight(26)
        btn_config.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-weight: bold; border-radius: 4px; padding: 0 12px;")
        btn_config.clicked.connect(lambda: self._open_voice_config(char))
        vbtn_row.addWidget(btn_config)
        sample_path = getattr(profile, 'voice_sample_path', '') or getattr(char, 'voice_sample', '') or ''
        if sample_path and Path(sample_path).exists():
            vbtn_row.addWidget(QLabel(f"  \u2713 {Path(sample_path).name}"))
        vbtn_row.addStretch()
        vf_l.addLayout(vbtn_row)
        L.addWidget(voice_frame)

        # Botoes
        btns = QHBoxLayout()
        btn_save = QPushButton("SALVAR")
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 11pt; font-weight: bold; border-radius: 4px;")
        btn_save.clicked.connect(lambda: self._save_character(char))
        btns.addWidget(btn_save)
        btn_copy = QPushButton("COPIAR FICHA")
        btn_copy.setFixedHeight(34)
        btn_copy.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-weight: bold; border: 1px solid {C['cyan']}; border-radius: 4px; padding: 0 12px;")
        btn_copy.clicked.connect(lambda: self._copy_char_sheet(char))
        btns.addWidget(btn_copy)
        btns.addStretch()
        btn_del = QPushButton("REMOVER")
        btn_del.setFixedHeight(34)
        btn_del.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; border: 1px solid #ff4444; border-radius: 4px; padding: 0 12px;")
        btn_del.clicked.connect(lambda: self._delete_character(char))
        btns.addWidget(btn_del)
        L.addLayout(btns)
        L.addStretch()

    def _save_character(self, char):
        for key, box in self._char_textboxes.items():
            setattr(char, key, box.toPlainText().strip())
        self.project.save(PROJECTS_DIR)
        self._rebuild_char_cards()

    def _delete_character(self, char):
        self.project.characters = [c for c in self.project.characters if c.id != char.id]
        self.project.save(PROJECTS_DIR)
        self._selected_char_id = None
        self._rebuild_char_cards()
        self._show_empty_editor()

    def _import_char_txt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar Personagem", "", "Text (*.txt)")
        if not path:
            return
        from makevid.core.project import Character
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        field_map = {
            "NOME": "name", "TIPO": "char_type", "RESUMO": "summary",
            "PERFIL DEMOGRAFICO": "demographic", "IDADE": "age",
            "ALTURA E CONSTITUICAO": "height_build", "PROPORCAO": "proportion_style",
            "ROSTO E CABECA": "face_design", "CABELO / CABECA": "hair_head",
            "PELE / SUPERFICIE": "skin_surface", "TRAJE / ARMADURA": "costume",
            "DETALHES ASSIMETRICOS": "asymmetric_details", "ACESSORIOS": "accessories",
            "CONTINUIDADE": "continuity_locks", "ESTILO VISUAL": "visual_style",
        }
        data = {}
        for line in text.strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                attr = field_map.get(key.strip().upper())
                if attr:
                    data[attr] = val.strip()
        char = Character(id=str(uuid.uuid4())[:8], name=data.get("name", "Importado"))
        for attr, val in data.items():
            setattr(char, attr, val)
        self.project.characters.append(char)
        self.project.save(PROJECTS_DIR)
        self._selected_char_id = char.id
        self._rebuild_char_cards()
        self._build_char_editor(char)

    def _copy_char_sheet(self, char):
        self._save_character(char)
        parts = []
        fields = [
            ("name", "NOME"), ("char_type", "TIPO"), ("summary", "RESUMO"),
            ("demographic", "PERFIL DEMOGRAFICO"), ("age", "IDADE"),
            ("height_build", "ALTURA E CONSTITUICAO"), ("proportion_style", "PROPORCAO"),
            ("face_design", "ROSTO E CABECA"), ("hair_head", "CABELO / CABECA"),
            ("skin_surface", "PELE / SUPERFICIE"), ("costume", "TRAJE / ARMADURA"),
            ("asymmetric_details", "DETALHES ASSIMETRICOS"), ("accessories", "ACESSORIOS"),
            ("continuity_locks", "CONTINUIDADE"), ("visual_style", "ESTILO VISUAL"),
        ]
        for attr, label in fields:
            val = getattr(char, attr, "") or ""
            if val:
                parts.append(f"{label}: {val}")
        QApplication.clipboard().setText("\n".join(parts))

    def _add_ref_image(self, char):
        paths, _ = QFileDialog.getOpenFileNames(self, "Imagem de Referencia", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not paths:
            return
        existing = (getattr(char, 'reference_image', '') or '').strip()
        for p in paths:
            existing = f"{existing}|{p}" if existing else p
        char.reference_image = existing
        self.project.save(PROJECTS_DIR)
        self._build_char_editor(char)

    def _remove_ref_image(self, char, idx):
        paths = self._get_ref_paths(char)
        if idx < len(paths):
            paths.pop(idx)
        char.reference_image = "|".join(paths)
        self.project.save(PROJECTS_DIR)
        self._build_char_editor(char)

    def _get_ref_paths(self, char):
        ref = getattr(char, 'reference_image', '') or ''
        return [p.strip() for p in ref.split("|") if p.strip()]

    def _test_voice(self, char):
        from makevid.core.voice_engine import VoiceProfile, build_speech_params
        profile = VoiceProfile.from_dict(char.voice_profile) if getattr(char, 'voice_profile', None) else VoiceProfile()
        if getattr(char, 'voice_id', '') and not char.voice_profile:
            profile.voice_id = char.voice_id
        name = char.name or "personagem"
        text = f"Ola, eu sou {name}. Esta e a minha voz."
        params = build_speech_params(profile, text, "neutral")
        def run():
            from makevid.core.tts_provider import generate_voice, play_audio
            from makevid.config import AUDIO_DIR
            path = AUDIO_DIR / "_voice_test.wav"
            result = generate_voice(text, path, voice_profile=params)
            if result:
                play_audio(path)
        threading.Thread(target=run, daemon=True).start()

    def _make_splitter_filter(self, splitter, handle):
        """Cria event filter para hover expand no handle do splitter."""
        from PySide6.QtCore import QObject, QEvent

        class _HoverFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Enter:
                    splitter.setHandleWidth(7)
                    handle.setStyleSheet("background: #ffd700;")
                elif event.type() == QEvent.Leave:
                    splitter.setHandleWidth(4)
                    handle.setStyleSheet("background: #2a2a4a;")
                return False

        f = _HoverFilter(handle)
        return f
