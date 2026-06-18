"""Voice Emotions - Configuracao detalhada de emocoes por personagem."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QGridLayout
)
from PySide6.QtCore import Qt

from makevid.qt.theme import C
from makevid.core.voice_engine import DEFAULT_EMOTIONS, EmotionModifier


EMOTION_LABELS = {
    "neutral": "NEUTRO", "fear": "MEDO", "anger": "RAIVA",
    "sadness": "TRISTE", "whisper": "SUSSURRO", "shout": "GRITO",
    "sarcasm": "SARCASMO", "despair": "DESESPERO", "joy": "ALEGRIA",
    "seduction": "SEDUCAO", "fatigue": "CANSACO", "tension": "TENSAO",
    "relief": "ALIVIO",
}

EMOTION_COLORS = {
    "neutral": "#888888", "fear": "#aa44ff", "anger": "#ff4444",
    "sadness": "#4488ff", "whisper": "#888888", "shout": "#ff8800",
    "sarcasm": "#ffcc00", "despair": "#ff00ff", "joy": "#44ff44",
    "seduction": "#ff6699", "fatigue": "#886644", "tension": "#ff6600",
    "relief": "#44ccaa",
}


def build_emotions_section(parent_layout, profile, on_emotion_select=None):
    """Constroi a secao de emocoes com grid de botoes e painel de detalhe.

    Returns:
        (emotion_detail_frame, selected_emotion_var, em_slider_vars)
    """
    frame = QFrame()
    frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px;")
    fl = QVBoxLayout(frame)
    fl.setContentsMargins(8, 8, 8, 8)
    fl.setSpacing(4)

    # Grid de botoes
    emotion_names = list(DEFAULT_EMOTIONS.keys())
    state = {"selected": "neutral", "sliders": {}}

    # Detail frame
    detail_frame = QFrame()
    detail_frame.setStyleSheet(f"background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 4px;")
    detail_layout = QVBoxLayout(detail_frame)
    detail_layout.setContentsMargins(8, 6, 8, 6)
    detail_layout.setSpacing(3)

    def _show_detail(em_name):
        state["selected"] = em_name
        state["sliders"].clear()

        # Limpar detail
        while detail_layout.count():
            item = detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    child = sub.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

        em = DEFAULT_EMOTIONS.get(em_name, EmotionModifier())
        if em_name in (profile.custom_emotions or {}):
            data = profile.custom_emotions[em_name]
            em = EmotionModifier(**data) if isinstance(data, dict) else em

        clr = EMOTION_COLORS.get(em_name, C["text2"])
        title = QLabel(f"CONFIG: {EMOTION_LABELS.get(em_name, em_name.upper())}")
        title.setStyleSheet(f"color: {clr}; font-size: 9pt; font-weight: bold;")
        detail_layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(3)
        em_params = [
            ("pitch_delta", "Pitch", -20, 20, em.pitch_delta, "Hz"),
            ("rate_delta", "Rate", -50, 50, em.rate_delta, "%"),
            ("volume_delta", "Volume", -50, 50, em.volume_delta, "%"),
            ("tremor", "Tremor", 0, 100, em.tremor, "%"),
            ("pausas", "Pausas", 0, 100, em.pausas, "%"),
            ("quebras", "Quebras", 0, 100, em.quebras, "%"),
            ("intensidade", "Intensidade", 0, 100, em.intensidade, "%"),
        ]
        for i, (key, label, mn, mx, val, unit) in enumerate(em_params):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
            grid.addWidget(lbl, i, 0)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(mn, mx)
            sl.setValue(val)
            sl.setStyleSheet(
                f"QSlider::groove:horizontal {{ background: {C['input']}; height: 5px; border-radius: 2px; }}"
                f"QSlider::handle:horizontal {{ background: {clr}; width: 12px; margin: -4px 0; border-radius: 6px; }}"
                f"QSlider::sub-page:horizontal {{ background: {clr}; border-radius: 2px; }}")
            grid.addWidget(sl, i, 1)
            val_lbl = QLabel(f"{val}{unit}")
            val_lbl.setFixedWidth(45)
            val_lbl.setStyleSheet(f"color: {clr}; font-size: 8pt; font-weight: bold;")
            sl.valueChanged.connect(lambda v, l=val_lbl, u=unit: l.setText(f"{v}{u}"))
            grid.addWidget(val_lbl, i, 2)
            state["sliders"][key] = sl
        detail_layout.addLayout(grid)

    # Criar botoes em 2 rows
    row1 = QHBoxLayout()
    row1.setSpacing(3)
    row2 = QHBoxLayout()
    row2.setSpacing(3)
    for i, em_name in enumerate(emotion_names):
        clr = EMOTION_COLORS.get(em_name, C["text2"])
        label = EMOTION_LABELS.get(em_name, em_name.upper())
        btn = QPushButton(label)
        btn.setFixedHeight(24)
        btn.setStyleSheet(
            f"QPushButton {{ background: {C['panel']}; color: {clr}; font-size: 7pt; font-weight: bold; "
            f"border: 1px solid {clr}; border-radius: 4px; padding: 0 4px; }}"
            f"QPushButton:hover {{ background: #1a1a2a; }}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=False, n=em_name: _show_detail(n))
        if i < 7:
            row1.addWidget(btn)
        else:
            row2.addWidget(btn)
    row2.addStretch()
    fl.addLayout(row1)
    fl.addLayout(row2)
    fl.addWidget(detail_frame)

    parent_layout.addWidget(frame)

    # Mostrar neutro por default
    _show_detail("neutral")

    return state


def collect_emotion_data(state):
    """Coleta os dados da emocao atualmente selecionada."""
    em_key = state["selected"]
    data = {}
    for key, sl in state["sliders"].items():
        data[key] = sl.value()
    return em_key, data
