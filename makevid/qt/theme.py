"""Theme Qt - Liquid Glass Design System (paleta azul/roxo fria)."""

C = {
    # Backgrounds
    "bg":           "rgba(11,18,32,0.0)",
    "panel":        "rgba(17,24,39,0.0)",
    "card":         "rgba(28,46,74,0.55)",
    "card_hover":   "rgba(36,58,94,0.65)",
    "input":        "rgba(10,16,30,0.70)",
    "border":       "rgba(255,255,255,0.10)",

    # Liquid Glass — tint frio azulado iOS
    "glass":        "rgba(28,46,74,0.55)",
    "glass_hover":  "rgba(36,58,94,0.65)",
    "glass_border": "rgba(255,255,255,0.55)",

    # Brand — roxo como primário, azul como accent
    "primary":   "#6C63FF",
    "secondary": "#8B7DFF",
    "accent":    "#58D8FF",

    # Aliases
    "gold":   "#6C63FF",   # substituído por primário
    "cyan":   "#58D8FF",
    "purple": "#8B7DFF",
    "blue":   "#60A5FA",

    # Text
    "text":  "#F3F6FF",
    "text2": "#A9B4C8",
    "text3": "#6E7A91",

    # States
    "red":       "#EF4444",
    "green":     "#34D399",
    "playhead":  "#EF4444",
    "danger":    "#EF4444",
    "danger_bg": "#1f1010",
    "dark":      "#0B1220",
    "dark_text": "#0B1220",

    # Track colors — cores distintas e vibrantes por faixa
    "track_voice": "#A78BFA",   # violeta claro
    "track_sfx":   "#34D399",   # verde esmeralda
    "track_music": "#F472B6",   # rosa
    "track_audio": "#38BDF8",   # azul céu
    "track_fx":    "#FB923C",   # laranja

    # Timeline
    "ruler":       "#111827",
    "ruler_text":  "#6E7A91",
    "ruler_line":  "#1A2336",
    "trim_handle": "#6C63FF",

    # Neon glow
    "neon_gold":   "#8B7DFF",
    "neon_cyan":   "#58D8FF",
    "neon_purple": "#6C63FF",

    # Extra
    "selected":    "#2C3C5A",
    "warning":     "#FBBF24",
    "info":        "#60A5FA",
    "success":     "#34D399",
}

STYLESHEET = """
QMainWindow {
    background-color: #040814;
}
QWidget {
    background-color: transparent;
    color: #F3F6FF;
    font-family: "Segoe UI";
    font-size: 10pt;
}
#AppRoot {
    background: transparent;
}
QLabel {
    background: transparent;
    border: none;
    color: #F3F6FF;
}

/* ── Botões Glass ── */
QPushButton {
    background-color: rgba(28,46,74,0.55);
    color: #F3F6FF;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: rgba(36,58,94,0.70);
    border-color: rgba(255,255,255,0.22);
    color: #8B7DFF;
}
QPushButton:pressed {
    background-color: rgba(44,60,90,0.80);
    border-color: #6C63FF;
}
QPushButton#closeBtn {
    background: transparent;
    color: #6E7A91;
    border: none;
    font-size: 11pt;
    font-weight: bold;
    padding: 0;
    border-radius: 0;
}
QPushButton#closeBtn:hover {
    color: #EF4444;
}

/* ── Isolamento de QFrame ── */
QFrame > QLabel {
    border: none;
    background: transparent;
}
QFrame > QPushButton#closeBtn {
    background: transparent;
    color: #6E7A91;
    border: none;
    border-radius: 0;
    padding: 0;
}
QFrame > QPushButton#closeBtn:hover {
    color: #EF4444;
}
QPushButton#primary {
    background-color: #6C63FF;
    color: #0B1220;
    border: 1px solid #8B7DFF;
    border-radius: 10px;
}
QPushButton#primary:hover {
    background-color: #8B7DFF;
    border-color: #58D8FF;
}

/* ── Inputs Glass ── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: rgba(10,16,30,0.70);
    color: #58D8FF;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    padding: 4px 10px;
    font-family: "Consolas";
    font-weight: bold;
}
QLineEdit:hover, QTextEdit:hover {
    border-color: rgba(255,255,255,0.20);
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #6C63FF;
    background-color: rgba(10,16,30,0.80);
}

/* ── ComboBox Glass ── */
QComboBox {
    background-color: rgba(28,46,74,0.55);
    color: #F3F6FF;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 4px 10px;
}
QComboBox:hover {
    border-color: #6C63FF;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: rgba(20,32,55,0.92);
    color: #F3F6FF;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    selection-background-color: rgba(36,58,94,0.80);
    selection-color: #6C63FF;
    outline: none;
}

/* ── Slider Glass ── */
QSlider::groove:horizontal {
    background: #1A2336;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #6C63FF;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 2px solid #8B7DFF;
}
QSlider::handle:horizontal:hover {
    background: #8B7DFF;
    border-color: #58D8FF;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6C63FF, stop:1 #58D8FF);
    border-radius: 2px;
}

/* ── ScrollBar Glass ── */
QScrollBar:vertical {
    background: rgba(10,16,30,0.30);
    width: 8px;
    border-radius: 4px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: rgba(28,46,74,0.60);
    min-height: 30px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #6C63FF;
}
QScrollBar::handle:vertical:pressed {
    background: #8B7DFF;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: rgba(10,16,30,0.30);
    height: 8px;
    border-radius: 4px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(28,46,74,0.60);
    min-width: 30px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #6C63FF;
}
QScrollBar::handle:horizontal:pressed {
    background: #8B7DFF;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ── Splitter Glass ── */
QSplitter::handle {
    background: rgba(255,255,255,0.08);
}
QSplitter::handle:hover {
    background: #6C63FF;
}
QSplitter::handle:pressed {
    background: #8B7DFF;
}
QSplitter { padding: 0px; }

/* ── GraphicsView ── */
QGraphicsView {
    background-color: transparent;
    border: none;
}
QScrollArea {
    background: transparent;
    border: none;
}

/* ── ProgressBar Glass ── */
QProgressBar {
    background: rgba(28,46,74,0.45);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 4px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6C63FF, stop:1 #58D8FF);
    border-radius: 4px;
}

/* ── Tooltip Glass ── */
QToolTip {
    background-color: rgba(20,32,55,0.92);
    color: #A9B4C8;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 10px;
    padding: 8px 12px;
    font-family: "Segoe UI";
    font-size: 9pt;
}

/* ── Menu Glass ── */
QMenu {
    background-color: rgba(20,32,55,0.92);
    color: #F3F6FF;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 12px;
    padding: 6px 4px;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMenu::item {
    padding: 7px 22px;
    border-radius: 8px;
    margin: 1px 4px;
}
QMenu::item:selected {
    background-color: rgba(36,58,94,0.80);
    color: #6C63FF;
}
QMenu::item:pressed {
    background-color: #6C63FF;
    color: #0B1220;
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.10);
    margin: 4px 10px;
}
QMenu::indicator:checked {
    width: 8px;
    height: 8px;
    border-radius: 4px;
    background: #6C63FF;
    margin-left: 6px;
}

/* ── AudioCard: waveform e botão play ── */
QWidget#waveformWidget {
    background-color: rgba(28,46,74,0.55);
}
QPushButton#btnPlay {
    background-color: rgba(28,46,74,0.55);
    color: #58D8FF;
    border: 1px solid #58D8FF;
    border-radius: 5px;
    font-size: 12pt;
    font-weight: bold;
    font-family: "Segoe UI Symbol", "Arial Unicode MS", sans-serif;
    padding: 0;
}
QPushButton#btnPlay:hover {
    background-color: #58D8FF;
    color: #0B1220;
}
"""
