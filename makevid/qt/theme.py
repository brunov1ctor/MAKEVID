"""Theme Qt - Cores e stylesheet global (QSS)."""

# Cores (mesmas do tkinter theme.py)
C = {
    "bg": "#0a0a0f",
    "panel": "#0d0f1a",
    "card": "#111328",
    "card_hover": "#1a1d3a",
    "input": "#0a0c18",
    "border": "#1e2a4a",
    "gold": "#c89b3c",
    "cyan": "#0ac8b9",
    "purple": "#6b3fa0",
    "blue": "#005a82",
    "text": "#f0e6d2",
    "text2": "#a09b8c",
    "text3": "#5b5a56",
    "red": "#ff4444",
    "green": "#0ac8b9",
    "playhead": "#ff3333",
}

STYLESHEET = """
QMainWindow {
    background-color: #0d0f1a;
}
QWidget {
    background-color: #0d0f1a;
    color: #f0e6d2;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel {
    background: transparent;
    border: none;
    color: #f0e6d2;
}
QPushButton {
    background-color: #111328;
    color: #f0e6d2;
    border: 1px solid #1e2a4a;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1a1d3a;
    border-color: #c89b3c;
}
QPushButton:pressed {
    background-color: #0a0c18;
}
QPushButton#closeBtn {
    background: transparent;
    color: #5b5a56;
    border: none;
    font-size: 11pt;
    font-weight: bold;
    padding: 0;
}
QPushButton#closeBtn:hover {
    color: #ff4444;
}
QPushButton#primary {
    background-color: #c89b3c;
    color: #0a0a0f;
    border: 2px solid #ffd700;
}
QPushButton#primary:hover {
    background-color: #ffd700;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0a0c18;
    color: #0ac8b9;
    border: 2px solid #1e2a4a;
    border-radius: 6px;
    padding: 4px 8px;
    font-family: "Consolas";
    font-weight: bold;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #c89b3c;
}
QSlider::groove:horizontal {
    background: #1e2a4a;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #0ac8b9;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: #0ac8b9;
    border-radius: 2px;
}
QScrollBar:vertical {
    background: #0a0c14;
    width: 10px;
    border-radius: 5px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: #3a3a5a;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #c89b3c;
}
QScrollBar::handle:vertical:pressed {
    background: #ffd700;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: #0a0c14;
    height: 10px;
    border-radius: 5px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: #3a3a5a;
    min-width: 30px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #c89b3c;
}
QScrollBar::handle:horizontal:pressed {
    background: #ffd700;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
QSplitter::handle {
    background: #c89b3c;
}
QSplitter::handle:hover {
    background: #ffd700;
}
QSplitter::handle:pressed {
    background: #ffd700;
}
QSplitter {
    padding: 0px;
}
QGraphicsView {
    background-color: #07090e;
    border: none;
}
QToolTip {
    background-color: #111328;
    color: #a09b8c;
    border: 1px solid #c89b3c;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: "Segoe UI";
    font-size: 9pt;
}
"""
