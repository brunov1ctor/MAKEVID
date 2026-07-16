"""Voice Config - Configuracao completa de voz do personagem (inline no editor)."""

import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QSlider, QComboBox, QGridLayout, QFileDialog
)
from PySide6.QtCore import Qt

from makevid.qt.theme import C
from makevid.config import PROJECTS_DIR, AUDIO_DIR
from makevid.core.voice_engine import (
    VoiceProfile, VOICE_PRESETS, DEFAULT_EMOTIONS, build_speech_params
)
from makevid.qt.panels.style.voice_emotions import (
    build_emotions_section, collect_emotion_data, EMOTION_LABELS
)
from makevid.qt.panels.style.voice_test import VoiceTestSection


class VoiceConfigMixin:
    """Metodos de configuracao de voz inline no editor de personagem."""

    def _open_voice_config(self, char):
        """Abre Voice Profile inline no editor."""
        self._clear_editor()
        L = self._char_editor_layout

        profile = VoiceProfile.from_dict(char.voice_profile) if getattr(char, 'voice_profile', None) else VoiceProfile()
        if getattr(char, 'voice_id', '') and not char.voice_profile:
            profile.voice_id = char.voice_id

        # Header
        hdr = QHBoxLayout()
        btn_back = QPushButton("\u2190 VOLTAR")
        btn_back.setFixedHeight(26)
        btn_back.setStyleSheet(f"background: {C['card']}; color: {C['text2']}; font-weight: bold; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 10px;")
        btn_back.clicked.connect(lambda: self._select_char(char))
        hdr.addWidget(btn_back)
        title = QLabel("\U0001f3a4 VOICE PROFILE")
        title.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold;")
        hdr.addWidget(title)
        name_lbl = QLabel(char.name or "")
        name_lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 10pt;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        L.addLayout(hdr)

        self._vp_sep(L)

        # === ENGINE ===
        eng_row = QHBoxLayout()
        eng_row.addWidget(self._vp_label("ENGINE"))
        self._vp_engine_btns = {}
        engines = ["edge-tts", "bark", "xtts", "parler", "elevenlabs"]
        self._vp_engine = profile.engine
        for eng in engines:
            is_sel = eng == profile.engine
            btn = QPushButton(eng.upper())
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._vp_engine_style(is_sel))
            btn.clicked.connect(lambda checked=False, e=eng: self._vp_set_engine(e))
            eng_row.addWidget(btn)
            self._vp_engine_btns[eng] = btn
        eng_row.addStretch()
        L.addLayout(eng_row)

        # === TIMBRE ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("TIMBRE (voz base)"))
        timbre_frame = self._vp_card()
        tf_l = QVBoxLayout(timbre_frame)
        tf_l.setContentsMargins(8, 8, 8, 8)
        tf_l.setSpacing(4)

        voice_row = QHBoxLayout()
        voice_row.addWidget(self._vp_label("Voz:"))
        self._vp_voice_id = QComboBox()
        self._vp_voice_id.addItems(self._get_voice_list())
        self._vp_voice_id.setCurrentText(profile.voice_id)
        self._vp_voice_id.setEditable(True)
        self._vp_voice_id.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 6px;")
        voice_row.addWidget(self._vp_voice_id)
        btn_preview = QPushButton("\u25b6")
        btn_preview.setFixedSize(30, 24)
        btn_preview.setCursor(Qt.PointingHandCursor)
        btn_preview.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-weight: bold; border: 1px solid {C['cyan']}; border-radius: 4px;")
        btn_preview.clicked.connect(lambda: self._vp_preview_voice(char))
        voice_row.addWidget(btn_preview)
        tf_l.addLayout(voice_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(self._vp_label("Idioma:"))
        self._vp_language = QComboBox()
        self._vp_language.addItems(["pt-BR", "en-US", "es-ES", "fr-FR"])
        self._vp_language.setCurrentText(profile.language)
        self._vp_language.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px;")
        lang_row.addWidget(self._vp_language)
        lang_row.addWidget(self._vp_label("Genero:"))
        self._vp_gender = QComboBox()
        self._vp_gender.addItems(["male", "female"])
        self._vp_gender.setCurrentText(profile.gender)
        self._vp_gender.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px;")
        lang_row.addWidget(self._vp_gender)
        lang_row.addStretch()
        tf_l.addLayout(lang_row)
        L.addWidget(timbre_frame)

        # === PARAMETROS ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("PARAMETROS DE VOZ"))
        self._vp_sliders = {}
        params_frame = self._vp_card()
        pf_l = QGridLayout(params_frame)
        pf_l.setContentsMargins(8, 8, 8, 8)
        pf_l.setSpacing(4)
        for i, (key, label, mn, mx, val, unit) in enumerate([
            ("pitch_base", "TOM (pitch)", -20, 20, profile.pitch_base, "Hz"),
            ("rate_base", "VELOCIDADE", -50, 50, profile.rate_base, "%"),
            ("volume_base", "VOLUME", 50, 150, profile.volume_base, "%"),
        ]):
            self._vp_add_slider(pf_l, i, key, label, mn, mx, val, unit)
        L.addWidget(params_frame)

        # === POST-PROCESSING ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("POST-PROCESSING (simulacao de timbre)"))
        pp_frame = self._vp_card()
        pp_l = QGridLayout(pp_frame)
        pp_l.setContentsMargins(8, 8, 8, 8)
        pp_l.setSpacing(4)
        for i, (key, label, mn, mx, val, unit) in enumerate([
            ("breathiness", "RESPIRACAO", 0, 100, profile.breathiness, "%"),
            ("roughness", "ASPEREZA", 0, 100, profile.roughness, "%"),
            ("emphasis", "ENFASE", 0, 100, profile.emphasis, "%"),
        ]):
            self._vp_add_slider(pp_l, i, key, label, mn, mx, val, unit)
        L.addWidget(pp_frame)

        # === EMOCOES ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("EMOCOES (modificadores por cena)"))
        self._vp_emotion_state = build_emotions_section(L, profile)

        # === TESTE ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("TESTE"))
        self._vp_test = VoiceTestSection()
        self._vp_test.build(L, EMOTION_LABELS)
        self._vp_test.connect_listen(lambda text, emo: self._vp_do_test(char, text, emo))

        # === PRESETS ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("PRESETS RAPIDOS"))
        presets_frame = self._vp_card()
        presets_l = QGridLayout(presets_frame)
        presets_l.setContentsMargins(8, 8, 8, 8)
        presets_l.setSpacing(3)
        preset_labels = [
            ("heroi_grave", "Heroi Grave"), ("vilao_sombrio", "Vilao Sombrio"),
            ("jovem_nervoso", "Jovem Nervoso"), ("ancia_sabia", "Ancia Sabia"),
            ("crianca", "Crianca"), ("narrador_epico", "Narrador Epico"),
            ("soldado_cansado", "Soldado Cansado"), ("femme_fatale", "Femme Fatale"),
        ]
        for i, (key, label) in enumerate(preset_labels):
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"background: {C['panel']}; color: {C['gold']}; font-size: 8pt; font-weight: bold; border: 1px solid {C['gold']}; border-radius: 4px; padding: 0 6px;")
            btn.clicked.connect(lambda checked=False, k=key: self._vp_apply_preset(k))
            presets_l.addWidget(btn, i // 4, i % 4)
        L.addWidget(presets_frame)

        # === AMOSTRA ===
        self._vp_sep(L)
        L.addWidget(self._vp_section("AMOSTRA DE VOZ (para XTTS/clone)"))
        sample_frame = self._vp_card()
        sf_l = QHBoxLayout(sample_frame)
        sf_l.setContentsMargins(8, 8, 8, 8)
        sample_path = getattr(profile, 'voice_sample_path', '') or getattr(char, 'voice_sample', '') or ''
        self._vp_sample_path = sample_path
        self._vp_sample_lbl = QLabel(Path(sample_path).name if sample_path else "Nenhuma amostra")
        self._vp_sample_lbl.setStyleSheet(f"color: {'#44cc88' if sample_path else C['text3']}; font-size: 9pt;")
        sf_l.addWidget(self._vp_sample_lbl)
        btn_import = QPushButton("Importar")
        btn_import.setFixedHeight(24)
        btn_import.setStyleSheet(f"background: {C['card']}; color: {C['text2']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 8px;")
        btn_import.clicked.connect(self._vp_import_sample)
        sf_l.addWidget(btn_import)
        btn_rec = QPushButton("\u25cf Gravar")
        btn_rec.setFixedHeight(24)
        btn_rec.setStyleSheet(f"background: #2a0808; color: #ff4444; font-weight: bold; border: 1px solid #ff4444; border-radius: 4px; padding: 0 8px;")
        sf_l.addWidget(btn_rec)
        sf_l.addStretch()
        L.addWidget(sample_frame)

        # === BOTOES FINAIS ===
        final_sep = QFrame()
        final_sep.setFixedHeight(2)
        final_sep.setStyleSheet(f"background: {C['gold']};")
        L.addWidget(final_sep)

        final_row = QHBoxLayout()
        btn_save = QPushButton("\u2714 SALVAR VOICE PROFILE")
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 11pt; font-weight: bold; border-radius: 4px;")
        btn_save.clicked.connect(lambda: self._vp_save(char))
        final_row.addWidget(btn_save)
        btn_cancel = QPushButton("CANCELAR")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 16px;")
        btn_cancel.clicked.connect(lambda: self._select_char(char))
        final_row.addWidget(btn_cancel)
        L.addLayout(final_row)
        L.addStretch()

    # ============================================================
    # HELPERS
    # ============================================================

    def _vp_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return lbl

    def _vp_section(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return lbl

    def _vp_sep(self, layout):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']};")
        layout.addWidget(sep)

    def _vp_card(self):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px;")
        return frame

    def _vp_engine_style(self, is_sel):
        return (
            f"background: {C['cyan'] if is_sel else C['card']}; "
            f"color: {'#0a0a0f' if is_sel else C['text3']}; "
            f"font-weight: bold; font-size: 8pt; "
            f"border: 1px solid {C['cyan']}; border-radius: 4px; padding: 0 8px;")

    def _vp_add_slider(self, grid, row, key, label, mn, mx, val, unit):
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        grid.addWidget(lbl, row, 0)
        sl = QSlider(Qt.Horizontal)
        sl.setRange(mn, mx)
        sl.setValue(val)
        sl.setFocusPolicy(Qt.StrongFocus)
        sl.wheelEvent = lambda e: e.ignore()
        sl.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['input']}; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {C['gold']}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {C['cyan']}; border-radius: 3px; }}")
        grid.addWidget(sl, row, 1)
        val_lbl = QLabel(f"{val}{unit}")
        val_lbl.setFixedWidth(50)
        val_lbl.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt; font-weight: bold;")
        sl.valueChanged.connect(lambda v, l=val_lbl, u=unit: l.setText(f"{v}{u}"))
        grid.addWidget(val_lbl, row, 2)
        self._vp_sliders[key] = sl

    # ============================================================
    # ACTIONS
    # ============================================================

    def _vp_set_engine(self, engine):
        self._vp_engine = engine
        for eng, btn in self._vp_engine_btns.items():
            btn.setStyleSheet(self._vp_engine_style(eng == engine))

    def _vp_apply_preset(self, key):
        if key in VOICE_PRESETS:
            p = VOICE_PRESETS[key]
            self._vp_voice_id.setCurrentText(p.voice_id)
            self._vp_set_engine(p.engine)
            self._vp_language.setCurrentText(p.language)
            self._vp_gender.setCurrentText(p.gender)
            self._vp_sliders["pitch_base"].setValue(p.pitch_base)
            self._vp_sliders["rate_base"].setValue(p.rate_base)
            self._vp_sliders["volume_base"].setValue(p.volume_base)
            self._vp_sliders["breathiness"].setValue(p.breathiness)
            self._vp_sliders["roughness"].setValue(p.roughness)
            self._vp_sliders["emphasis"].setValue(p.emphasis)

    def _vp_preview_voice(self, char):
        name = char.name or "personagem"
        text = f"Ola, eu sou {name}. Esta e a minha voz."
        profile = self._vp_collect_profile()
        params = build_speech_params(profile, text, "neutral")
        def run():
            from makevid.core.tts_provider import generate_voice, play_audio
            path = AUDIO_DIR / "_voice_preview.wav"
            result = generate_voice(text, path, voice_profile=params)
            if result:
                play_audio(path)
        threading.Thread(target=run, daemon=True).start()

    def _vp_do_test(self, char, text, emotion_label):
        if not text:
            text = "Teste de voz."
        # Mapear label PT para key EN
        em_key = "neutral"
        for k, v in EMOTION_LABELS.items():
            if v == emotion_label:
                em_key = k
                break
        profile = self._vp_collect_profile()
        params = build_speech_params(profile, text, em_key)
        def run():
            from makevid.core.tts_provider import generate_voice, play_audio
            path = AUDIO_DIR / "_voice_test.wav"
            result = generate_voice(text, path, voice_profile=params)
            if result:
                play_audio(path)
        threading.Thread(target=run, daemon=True).start()

    def _vp_import_sample(self):
        path, _ = QFileDialog.getOpenFileName(self, "Voice Sample", "", "Audio (*.wav *.mp3 *.ogg)")
        if path:
            self._vp_sample_path = path
            self._vp_sample_lbl.setText(Path(path).name)
            self._vp_sample_lbl.setStyleSheet(f"color: #44cc88; font-size: 9pt;")

    def _vp_collect_profile(self):
        profile = VoiceProfile(
            engine=self._vp_engine,
            voice_id=self._vp_voice_id.currentText(),
            language=self._vp_language.currentText(),
            gender=self._vp_gender.currentText(),
            pitch_base=self._vp_sliders["pitch_base"].value(),
            rate_base=self._vp_sliders["rate_base"].value(),
            volume_base=self._vp_sliders["volume_base"].value(),
            breathiness=self._vp_sliders["breathiness"].value(),
            roughness=self._vp_sliders["roughness"].value(),
            emphasis=self._vp_sliders["emphasis"].value(),
            voice_sample_path=getattr(self, '_vp_sample_path', ''),
        )
        # Salvar emocao customizada se editada
        if hasattr(self, '_vp_emotion_state'):
            em_key, em_data = collect_emotion_data(self._vp_emotion_state)
            if em_data:
                profile.custom_emotions = profile.custom_emotions or {}
                profile.custom_emotions[em_key] = em_data
        return profile

    def _vp_save(self, char):
        profile = self._vp_collect_profile()
        char.voice_profile = profile.to_dict()
        char.voice_id = profile.voice_id
        char.voice_sample = profile.voice_sample_path
        self.project.save(PROJECTS_DIR)
        self._select_char(char)

    def _get_voice_list(self):
        try:
            from makevid.core.tts_provider import get_available_voices
            voices_pt = get_available_voices("pt-BR")
            voices_en = get_available_voices("en-US")
            return [v["ShortName"] for v in voices_pt + voices_en] if (voices_pt or voices_en) else self._default_voices()
        except Exception:
            return self._default_voices()

    def _default_voices(self):
        return [
            "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural",
            "en-US-ChristopherNeural", "en-US-RogerNeural", "en-US-GuyNeural",
            "en-US-EricNeural", "en-US-BrianNeural", "en-US-JennyNeural",
            "en-US-AriaNeural", "en-US-AvaNeural", "en-US-EmmaNeural",
        ]
