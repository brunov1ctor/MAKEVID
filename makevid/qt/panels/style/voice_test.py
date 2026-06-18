"""Voice Test - Teste de voz, preview, comparacao de slots."""

import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit
)
from PySide6.QtCore import Qt

from makevid.qt.theme import C
from makevid.config import AUDIO_DIR
from makevid.core.voice_engine import VoiceProfile, build_speech_params


class VoiceTestSection:
    """Gerencia a secao de teste de voz com slots de comparacao."""

    def __init__(self):
        self.slots = []
        self._test_text = None
        self._slots_container = None

    def build(self, parent_layout, emotion_labels):
        """Constroi a secao de teste."""
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['cyan']}; border-radius: 4px;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setSpacing(4)

        self._test_text = QLineEdit("Eu preciso sair daqui... agora!")
        self._test_text.setStyleSheet(
            f"background: {C['input']}; color: {C['cyan']}; border: 2px solid {C['border']}; "
            f"border-radius: 8px; padding: 4px 8px; font-family: Consolas; font-size: 11pt; font-weight: bold;")
        fl.addWidget(self._test_text)

        # Emocao para teste
        emo_row = QHBoxLayout()
        emo_row.addWidget(self._label("Emocao:"))
        from PySide6.QtWidgets import QComboBox
        self._test_emotion = QComboBox()
        self._test_emotion.addItems(list(emotion_labels.values()))
        self._test_emotion.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 3px; padding: 2px 6px;")
        emo_row.addWidget(self._test_emotion)
        emo_row.addStretch()
        fl.addLayout(emo_row)

        # Botoes
        btn_row = QHBoxLayout()
        self._btn_listen = QPushButton("\u25b6 OUVIR")
        self._btn_listen.setFixedHeight(28)
        self._btn_listen.setStyleSheet(f"background: {C['cyan']}; color: #0a0a0f; font-weight: bold; border-radius: 4px; padding: 0 12px;")
        btn_row.addWidget(self._btn_listen)

        btn_save_slot = QPushButton("+ GUARDAR CONFIG")
        btn_save_slot.setFixedHeight(28)
        btn_save_slot.setStyleSheet(f"background: {C['card']}; color: {C['gold']}; font-weight: bold; border: 1px solid {C['gold']}; border-radius: 4px; padding: 0 10px;")
        btn_save_slot.clicked.connect(self._save_slot)
        btn_row.addWidget(btn_save_slot)
        btn_row.addStretch()
        fl.addLayout(btn_row)

        # Slots container
        self._slots_container = QVBoxLayout()
        self._slots_container.setSpacing(2)
        empty_lbl = QLabel("Nenhuma config salva. Ajuste os parametros e clique + GUARDAR CONFIG.")
        empty_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        self._slots_container.addWidget(empty_lbl)
        fl.addLayout(self._slots_container)

        parent_layout.addWidget(frame)
        return self

    def connect_listen(self, callback):
        """Conecta o botao OUVIR a um callback(text, emotion_label)."""
        self._btn_listen.clicked.connect(
            lambda: callback(self._test_text.text(), self._test_emotion.currentText()))

    def get_text(self):
        return self._test_text.text() if self._test_text else "Teste de voz."

    def get_emotion_label(self):
        return self._test_emotion.currentText() if hasattr(self, '_test_emotion') else "NEUTRO"

    def _save_slot(self):
        """Salva config atual como slot (placeholder - precisa do profile do parent)."""
        self.slots.append({
            "name": f"Slot {len(self.slots) + 1}",
            "text": self._test_text.text(),
            "emotion": self._test_emotion.currentText(),
        })
        self._refresh_slots()

    def _refresh_slots(self):
        # Limpar
        while self._slots_container.count():
            item = self._slots_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.slots:
            lbl = QLabel("Nenhuma config salva.")
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
            self._slots_container.addWidget(lbl)
            return

        for idx, slot in enumerate(self.slots):
            row_frame = QFrame()
            row_frame.setStyleSheet(f"background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 4px;")
            rl = QHBoxLayout(row_frame)
            rl.setContentsMargins(6, 4, 6, 4)

            name_lbl = QLabel(slot["name"])
            name_lbl.setStyleSheet(f"color: {C['gold']}; font-size: 9pt; font-weight: bold;")
            rl.addWidget(name_lbl)

            info = QLabel(f"{slot['emotion']} | {slot['text'][:20]}...")
            info.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
            rl.addWidget(info)
            rl.addStretch()

            btn_play = QPushButton("\u25b6")
            btn_play.setFixedSize(24, 22)
            btn_play.setStyleSheet(f"background: {C['cyan']}; color: #0a0a0f; font-weight: bold; border-radius: 4px;")
            rl.addWidget(btn_play)

            btn_rm = QPushButton("\u2715")
            btn_rm.setFixedSize(22, 22)
            btn_rm.setStyleSheet(f"background: transparent; color: #ff4444; font-weight: bold;")
            btn_rm.clicked.connect(lambda checked=False, i=idx: self._remove_slot(i))
            rl.addWidget(btn_rm)

            self._slots_container.addWidget(row_frame)

    def _remove_slot(self, idx):
        if idx < len(self.slots):
            self.slots.pop(idx)
            self._refresh_slots()

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        return lbl
