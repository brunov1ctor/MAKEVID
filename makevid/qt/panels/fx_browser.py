"""FX Browser — grid de seleção de efeitos com abas."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from makevid.qt.theme import C
from makevid.data.fx_definitions import FX_TABS, FX_TOOLTIPS, FX_TAB_TOOLTIPS

# ── Pixel art icons ──────────────────────────────────────────────────────────

_FX_ICONS = {
    "Fade In":     ["00000001","00000011","00000111","00001111","00011111","00111111","01111111","11111111"],
    "Fade Out":    ["11111111","01111111","00111111","00011111","00001111","00000111","00000011","00000001"],
    "Flash":       ["00010000","01010100","00111000","11111110","11111110","00111000","01010100","00010000"],
    "Wipe Left":   ["11110000","11110000","11110000","11111000","11111000","11110000","11110000","11110000"],
    "Wipe Right":  ["00001111","00001111","00001111","00011111","00011111","00001111","00001111","00001111"],
    "Dissolve":    ["10100101","01010010","10001101","01110010","10011101","01100010","10010101","01001010"],
    "Shake":       ["11111111","00000000","01111111","00000000","11111110","00000000","01111111","00000000"],
    "Slide":       ["00010000","00110000","01111111","11111111","11111111","01111111","00110000","00010000"],
    "Zoom":        ["01111110","10000001","10000001","10000001","10000001","01111100","00001110","00000111"],
    "Bounce":      ["00111100","01111110","01111110","00111100","00011000","00011000","00000000","01111110"],
    "Rotate":      ["00111000","01000100","10000010","10000110","10001110","01000100","00111000","00001110"],
    "Spin":        ["00011000","01100110","10011001","11000011","11000011","10011001","01100110","00011000"],
    "Blur":        ["00111100","01111110","11111111","11111111","11111111","11111111","01111110","00111100"],
    "Color Shift": ["11000000","11001100","11001100","00001100","00001111","00000011","00110011","00110000"],
    "Sepia":       ["00111100","01111110","11011011","11100111","11100111","11011011","01111110","00111100"],
    "Vignette":    ["11111111","10000001","10011001","10111101","10111101","10011001","10000001","11111111"],
    "Film Grain":  ["10010010","01001001","00100100","10010010","01001001","00100100","10010010","01001001"],
    "Pixelate":    ["11001100","11001100","00110011","00110011","11001100","11001100","00110011","00110011"],
    "Letterbox":   ["11111111","11111111","00000000","00000000","00000000","00000000","11111111","11111111"],
    "Invert":      ["11110000","11110000","11110000","11110000","00001111","00001111","00001111","00001111"],
    "Glitch":      ["11111111","00001111","11110000","11111111","11111111","00001111","11110000","11111111"],
    "RGB Split":   ["11000000","11100000","01110000","00111000","00011100","00001110","00000111","00000011"],
    "VHS":         ["11111111","00000000","11111111","00000000","11111111","00000000","11111111","00000000"],
    "Neon":        ["00010000","00010000","11111111","00111100","00111100","11111111","00010000","00010000"],
    "Pulse":       ["00111100","01000010","10011001","10100101","10100101","10011001","01000010","00111100"],
    "Camera":      ["01111110","10000001","10111101","11011011","11011011","10111101","10000001","01111110"],
}

_FX_ICON_COLORS = {
    "Fade In":      ("#aaccff", "#224488"),
    "Fade Out":     ("#224488", "#aaccff"),
    "Flash":        ("#ffffff", "#ffee88"),
    "Wipe Left":    ("#88ccff", "#0055aa"),
    "Wipe Right":   ("#88ccff", "#0055aa"),
    "Dissolve":     ("#aaaaff", "#334488"),
    "Shake":        ("#ffaa44", "#884400"),
    "Slide":        ("#44ddff", "#006688"),
    "Zoom":         ("#88ffcc", "#006644"),
    "Bounce":       ("#ffcc44", "#886600"),
    "Rotate":       ("#cc88ff", "#550088"),
    "Spin":         ("#ff88cc", "#880044"),
    "Blur":         ("#88aaff", "#2233aa"),
    "Color Shift":  ("#ff4444", "#4444ff"),
    "Sepia":        ("#ffcc88", "#884400"),
    "Vignette":     ("#888888", "#111111"),
    "Film Grain":   ("#ccbbaa", "#554433"),
    "Pixelate":     ("#44ffaa", "#006633"),
    "Letterbox":    ("#444444", "#111111"),
    "Invert":       ("#ffffff", "#000000"),
    "Glitch":       ("#ff2244", "#aa0022"),
    "RGB Split":    ("#ff3333", "#3333ff"),
    "VHS":          ("#aaffaa", "#224422"),
    "Neon":         ("#00ffee", "#006655"),
    "Pulse":        ("#ff44ff", "#660066"),
    "Camera":       ("#44aaff", "#002266"),
}


class _FxIconWidget(QWidget):
    def __init__(self, fx_name, parent=None):
        super().__init__(parent)
        clean = fx_name.strip()
        for i, ch in enumerate(clean):
            if ch.isascii() and ch.isalpha():
                clean = clean[i:].strip()
                break
        self._grid = _FX_ICONS.get(clean)
        if self._grid is None:
            for key in _FX_ICONS:
                if key.lower() in clean.lower() or clean.lower() in key.lower():
                    self._grid = _FX_ICONS[key]
                    clean = key
                    break
            else:
                self._grid = _FX_ICONS["Glitch"]
        c1, c2 = _FX_ICON_COLORS.get(clean, ("#aaaaff", "#334488"))
        self._color1, self._color2 = c1, c2

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        w, h = self.width(), self.height()
        px_w, px_h = w / 8, h / 8
        c1, c2 = QColor(self._color1), QColor(self._color2)
        for row in range(8):
            for col in range(8):
                if self._grid[row][col] == '1':
                    ratio = row / 7.0
                    r = int(c1.red()   * (1 - ratio) + c2.red()   * ratio)
                    g = int(c1.green() * (1 - ratio) + c2.green() * ratio)
                    b = int(c1.blue()  * (1 - ratio) + c2.blue()  * ratio)
                    p.fillRect(int(col * px_w), int(row * px_h),
                               int(px_w) + 1, int(px_h) + 1, QColor(r, g, b))


class FxBrowser(QWidget):
    """Grid de seleção de efeitos com abas."""

    fx_clicked = Signal(str)  # nome do FX

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_tab = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar
        self._tab_bar = QFrame()
        self._tab_bar.setFixedHeight(36)
        self._tab_bar.setStyleSheet(f"background: {C['card']}; border-radius: 0;")
        tab_layout = QHBoxLayout(self._tab_bar)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(2)
        self._tab_buttons = {}

        tab_keys = list(FX_TABS.keys())
        for key in tab_keys:
            tab = FX_TABS[key]
            from PySide6.QtWidgets import QPushButton
            btn = QPushButton(f"{tab['icon']} {tab['label']}")
            btn.setFixedHeight(26)
            btn.setToolTip(FX_TAB_TOOLTIPS.get(key, ""))
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
                f"font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 0 6px; }}"
                f"QPushButton:hover {{ color: {C['text']}; border-color: {C['purple']}; }}")
            btn.clicked.connect(lambda ck=False, k=key: self._select_tab(k))
            tab_layout.addWidget(btn)
            self._tab_buttons[key] = btn
        layout.addWidget(self._tab_bar)

        # Content scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(4)
        scroll.setWidget(self._content_widget)
        layout.addWidget(scroll)

        if tab_keys:
            self._select_tab(tab_keys[0])

    def _select_tab(self, key):
        self._current_tab = key
        for k, btn in self._tab_buttons.items():
            if k == key:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['secondary']}; color: {C['text']}; font-size: 8pt; "
                    f"font-weight: bold; border: 1px solid {C['accent']}; border-radius: 4px; padding: 0 6px; }}"
                    f"QPushButton:hover {{ background: {C['accent']}; }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['glass']}; color: {C['text3']}; font-size: 8pt; "
                    f"font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 0 6px; }}"
                    f"QPushButton:hover {{ color: {C['text']}; border-color: {C['secondary']}; }}")
        self._build_grid(key)

    def _build_grid(self, key):
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tab = FX_TABS[key]
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        for i, (name, desc) in enumerate(tab["items"]):
            grid.addWidget(self._make_fx_card(name, desc), i // 2, i % 2)

        self._content_layout.addWidget(grid_widget)
        self._content_layout.addStretch()

    def _make_fx_card(self, name, desc):
        from PySide6.QtWidgets import QPushButton
        card = QFrame()
        card.setFixedHeight(52)
        card.setObjectName("fxCard")
        card.setStyleSheet(
            f"QFrame#fxCard {{ background: {C['glass']}; border: 1px solid {C['glass_border']}; border-radius: 10px; }}"
            f"QFrame#fxCard:hover {{ border: 1px solid {C['primary']}; background: {C['glass_hover']}; }}")
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip(FX_TOOLTIPS.get(name, ""))

        cl = QHBoxLayout(card)
        cl.setContentsMargins(6, 4, 8, 4)
        cl.setSpacing(8)

        icon = _FxIconWidget(name)
        icon.setFixedSize(32, 32)
        icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        cl.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_lbl = QLabel(name)
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none; background: transparent;")
        text_col.addWidget(name_lbl)
        desc_lbl = QLabel(desc)
        desc_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        desc_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; border: none; background: transparent;")
        text_col.addWidget(desc_lbl)
        cl.addLayout(text_col)
        cl.addStretch()

        card.mousePressEvent = lambda e, n=name: self.fx_clicked.emit(n)
        return card
