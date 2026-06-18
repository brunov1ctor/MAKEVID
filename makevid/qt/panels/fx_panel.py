"""FX Panel Qt - Efeitos visuais com abas e grid (replica do antigo)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSlider
)
from PySide6.QtCore import Qt, Signal

from makevid.qt.theme import C
from makevid.data.fx_definitions import FX_TABS, FX_TOOLTIPS, FX_TAB_TOOLTIPS


# Icones pixel art 8x8 para cada tipo de FX (1=cor, 0=transparente)
_FX_ICONS = {
    "fade": [
        "00011000",
        "00111100",
        "01111110",
        "11111111",
        "11111111",
        "01111110",
        "00111100",
        "00011000",
    ],
    "slide": [
        "00010000",
        "00110000",
        "01111111",
        "11111111",
        "11111111",
        "01111111",
        "00110000",
        "00010000",
    ],
    "zoom": [
        "01111100",
        "10000010",
        "10000010",
        "10000010",
        "10000010",
        "01111100",
        "00001010",
        "00000101",
    ],
    "bounce": [
        "00011000",
        "00100100",
        "00011000",
        "00011000",
        "00100100",
        "01000010",
        "10000001",
        "11111111",
    ],
    "rotate": [
        "00111100",
        "01000010",
        "10000001",
        "10000001",
        "10000001",
        "01000010",
        "00111100",
        "00001110",
    ],
    "glitch": [
        "11111111",
        "00001111",
        "11110000",
        "11111111",
        "11111111",
        "00001111",
        "11110000",
        "11111111",
    ],
    "blur": [
        "00111100",
        "01111110",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "01111110",
        "00111100",
    ],
    "flash": [
        "00010000",
        "00110000",
        "01111100",
        "11111000",
        "00111110",
        "01111100",
        "00011000",
        "00010000",
    ],
    "shake": [
        "10000001",
        "01000010",
        "10100101",
        "01000010",
        "10000001",
        "01000010",
        "10100101",
        "01000010",
    ],
    "spin": [
        "00111100",
        "01000010",
        "10000001",
        "10001001",
        "10010001",
        "10000001",
        "01000010",
        "00111100",
    ],
    "pulse": [
        "00010100",
        "00101010",
        "01000001",
        "10000001",
        "10000001",
        "01000001",
        "00101010",
        "00010100",
    ],
    "camera": [
        "01111110",
        "11111111",
        "10011001",
        "10100101",
        "10100101",
        "10011001",
        "11111111",
        "01111110",
    ],
    "vhs": [
        "11111111",
        "10000001",
        "10111101",
        "10100101",
        "10100101",
        "10111101",
        "10000001",
        "11111111",
    ],
    "neon": [
        "00011000",
        "00100100",
        "01000010",
        "10011001",
        "10011001",
        "01000010",
        "00100100",
        "00011000",
    ],
    "default": [
        "00111100",
        "01000010",
        "10011001",
        "10100101",
        "10100101",
        "10011001",
        "01000010",
        "00111100",
    ],
}

# Cores por categoria
_FX_ICON_COLORS = {
    "fade": ("#ffd700", "#c89b3c"),
    "slide": ("#0ac8b9", "#066b62"),
    "zoom": ("#3399ff", "#1a5599"),
    "bounce": ("#44cc88", "#228855"),
    "rotate": ("#cc44aa", "#882266"),
    "glitch": ("#ff4444", "#aa2222"),
    "blur": ("#8888ff", "#4444aa"),
    "flash": ("#ffffff", "#aaaaaa"),
    "shake": ("#ff9944", "#aa6622"),
    "spin": ("#cc44aa", "#882266"),
    "pulse": ("#ff4488", "#aa2244"),
    "camera": ("#0ac8b9", "#066b62"),
    "vhs": ("#ff9944", "#885522"),
    "neon": ("#44ffaa", "#22aa66"),
    "default": ("#c89b3c", "#886622"),
}


def _get_fx_icon_key(name):
    """Determina qual icone usar baseado no nome do FX."""
    n = name.lower()
    for key in _FX_ICONS:
        if key in n:
            return key
    return "default"


class _FxIconWidget(QWidget):
    """Widget que desenha icone pixel art 8x8 escalado."""

    def __init__(self, fx_name, parent=None):
        super().__init__(parent)
        self._key = _get_fx_icon_key(fx_name)
        self._grid = _FX_ICONS.get(self._key, _FX_ICONS["default"])
        self._color1, self._color2 = _FX_ICON_COLORS.get(self._key, _FX_ICON_COLORS["default"])

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        w, h = self.width(), self.height()
        px_w = w / 8
        px_h = h / 8

        c1 = QColor(self._color1)
        c2 = QColor(self._color2)

        for row in range(8):
            for col in range(8):
                if self._grid[row][col] == '1':
                    # Gradiente simples: topo = c1, baixo = c2
                    ratio = row / 7.0
                    r = int(c1.red() * (1 - ratio) + c2.red() * ratio)
                    g = int(c1.green() * (1 - ratio) + c2.green() * ratio)
                    b = int(c1.blue() * (1 - ratio) + c2.blue() * ratio)
                    p.fillRect(int(col * px_w), int(row * px_h),
                               int(px_w) + 1, int(px_h) + 1,
                               QColor(r, g, b))



class FxPanel(QWidget):
    """Painel de efeitos visuais com abas e grid."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setObjectName("fxPanel")
        self.setStyleSheet(f"QWidget#fxPanel {{ background: {C['panel']}; }}")
        self._current_tab = None
        self._project = None
        self._item = None
        self._build_ui()

    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Header
        hdr_l = QHBoxLayout()
        hdr_l.setContentsMargins(10, 6, 6, 4)
        self._title = QLabel("EFEITOS")
        self._title.setStyleSheet(f"color: {C['purple']}; font-size: 13pt; font-weight: bold; background: transparent; border: none;")
        hdr_l.addWidget(self._title)
        hdr_l.addStretch()
        close_btn = QPushButton("X")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.closed.emit)
        hdr_l.addWidget(close_btn)
        self._layout.addLayout(hdr_l)

        # Separador purple
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background: {C['purple']};")
        self._layout.addWidget(sep)

        # Tab bar
        self._tab_bar = QFrame()
        self._tab_bar.setFixedHeight(36)
        self._tab_bar.setStyleSheet(f"background: {C['card']}; border-radius: 0;")
        self._tab_layout = QHBoxLayout(self._tab_bar)
        self._tab_layout.setContentsMargins(4, 4, 4, 4)
        self._tab_layout.setSpacing(2)
        self._tab_buttons = {}

        tab_keys = list(FX_TABS.keys())
        for key in tab_keys:
            tab = FX_TABS[key]
            btn = QPushButton(f"{tab['icon']} {tab['label']}")
            btn.setFixedHeight(26)
            btn.setToolTip(FX_TAB_TOOLTIPS.get(key, ""))
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
                f"font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 0 6px; }}"
                f"QPushButton:hover {{ color: {C['text']}; border-color: {C['purple']}; }}")
            btn.clicked.connect(lambda ck=False, k=key: self._select_tab(k))
            self._tab_layout.addWidget(btn)
            self._tab_buttons[key] = btn

        self._layout.addWidget(self._tab_bar)

        # Content area (scroll com grid)
        self._content_scroll = QScrollArea()
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setStyleSheet("border: none;")
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(4)
        self._content_scroll.setWidget(self._content_widget)
        self._layout.addWidget(self._content_scroll)

        # Selecionar primeira aba
        if tab_keys:
            self._select_tab(tab_keys[0])

    def _select_tab(self, key):
        self._current_tab = key

        # Atualizar visual dos botoes
        for k, btn in self._tab_buttons.items():
            if k == key:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['purple']}; color: {C['text']}; font-size: 8pt; "
                    f"font-weight: bold; border: 1px solid #bb77ff; border-radius: 4px; padding: 0 6px; }}"
                    f"QPushButton:hover {{ background: #bb77ff; }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {C['text3']}; font-size: 8pt; "
                    f"font-weight: bold; border: 1px solid transparent; border-radius: 4px; padding: 0 6px; }}"
                    f"QPushButton:hover {{ color: {C['text']}; border-color: {C['purple']}; }}")

        # Rebuild conteudo
        self._build_grid(key)

    def _build_grid(self, key):
        """Constroi grid de efeitos para a aba selecionada."""
        # Limpar
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tab = FX_TABS[key]

        # Grid responsivo (2 colunas)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        items = tab["items"]
        cols = 2
        for i, (name, desc) in enumerate(items):
            row = i // cols
            col = i % cols
            card = self._make_fx_card(name, desc)
            grid.addWidget(card, row, col)

        self._content_layout.addWidget(grid_widget)
        self._content_layout.addStretch()

    def _make_fx_card(self, name, desc):
        """Cria card individual de efeito com ícone desenhado."""
        card = QFrame()
        card.setFixedHeight(52)
        card.setObjectName("fxCard")
        card.setStyleSheet(
            f"QFrame#fxCard {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 6px; }}"
            f"QFrame#fxCard:hover {{ border: 2px solid {C['purple']}; background: #1a1a3a; }}")
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip(FX_TOOLTIPS.get(name, ""))

        cl = QHBoxLayout(card)
        cl.setContentsMargins(6, 4, 8, 4)
        cl.setSpacing(8)

        # Ícone desenhado pixel a pixel
        icon = _FxIconWidget(name)
        icon.setFixedSize(32, 32)
        icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        cl.addWidget(icon)

        # Texto
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        # Remover emoji do nome se tiver
        display_name = name
        if len(name) > 2 and name[1] == ' ':
            display_name = name[2:]
        elif len(name) > 3 and name[2] == ' ':
            display_name = name[3:]
        name_lbl = QLabel(display_name)
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        name_lbl.setStyleSheet(f"color: {C['text']}; font-size: 9pt; font-weight: bold; border: none; background: transparent;")
        text_col.addWidget(name_lbl)
        desc_lbl = QLabel(desc)
        desc_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        desc_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; border: none; background: transparent;")
        text_col.addWidget(desc_lbl)
        cl.addLayout(text_col)
        cl.addStretch()

        card.mousePressEvent = lambda e, n=name: self._on_fx_clicked(n)
        return card

    def _on_fx_clicked(self, name):
        """Emite signal para adicionar FX na timeline."""
        # Acessar app via parent chain
        from makevid.qt.app import MakeVidWindow
        app = self.window()
        if isinstance(app, MakeVidWindow):
            app._add_fx_to_timeline(name)

    # ============================================================
    # SHOW ITEM (editor de FX existente)
    # ============================================================

    def show_item(self, item, project=None):
        """Mostra editor de um item FX existente."""
        self._item = item
        self._project = project
        self._title.setText(f"FX: {item.name}")

        # Limpar conteudo
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Info
        info = QLabel(f"{item.name} | {item.duration:.1f}s | Inicio: {item.start_time:.1f}s")
        info.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        self._content_layout.addWidget(info)

        # Intensidade
        self._fx_slider(self._content_layout, item, "intensity", "INTENSIDADE", 0, 100,
                        int(item.params.get("intensity", 100)), "%", C['purple'])

        # Easing (botoes visuais)
        ease_lbl = QLabel("TRANSIÇÃO")
        ease_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        self._content_layout.addWidget(ease_lbl)

        ease_frame = QFrame()
        ease_frame.setStyleSheet(f"background: {C['card']}; border-radius: 4px;")
        ease_layout = QHBoxLayout(ease_frame)
        ease_layout.setContentsMargins(4, 4, 4, 4)
        ease_layout.setSpacing(3)

        current_easing = item.params.get("easing", "linear")
        easing_options = [
            ("linear", "━━━", "Constante"),
            ("ease-in", "╭━━", "Suave entrada"),
            ("ease-out", "━━╮", "Suave saída"),
            ("ease-in-out", "╭━╮", "Suave ambos"),
        ]
        self._ease_buttons = []
        for val, icon, tip in easing_options:
            btn = QPushButton(icon)
            btn.setFixedSize(48, 28)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            is_active = (val == current_easing)
            if is_active:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['purple']}; color: #ffffff; "
                    f"font-family: Consolas; font-size: 11pt; font-weight: bold; "
                    f"border: 2px solid #bb77ff; border-radius: 4px; }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['card']}; color: {C['text3']}; "
                    f"font-family: Consolas; font-size: 11pt; "
                    f"border: 1px solid {C['border']}; border-radius: 4px; }}"
                    f"QPushButton:hover {{ border: 1px solid {C['purple']}; color: {C['text']}; }}")
            btn.clicked.connect(lambda ck=False, v=val: self._set_easing(item, v))
            ease_layout.addWidget(btn)
            self._ease_buttons.append((btn, val))

        self._content_layout.addWidget(ease_frame)

        # Parametros especificos por efeito
        self._build_fx_params(item)

        # Preview
        btn_preview = QPushButton("\u25b6 PREVIEW")
        btn_preview.setFixedHeight(30)
        btn_preview.setStyleSheet(
            f"background: {C['card']}; color: {C['purple']}; font-weight: bold; "
            f"border: 2px solid {C['purple']}; border-radius: 4px;")
        btn_preview.clicked.connect(lambda: self._preview_fx(item))
        self._content_layout.addWidget(btn_preview)

        # Remover
        btn_remove = QPushButton("REMOVER FX")
        btn_remove.setFixedHeight(28)
        btn_remove.setStyleSheet(
            f"background: #2a0808; color: #ff4444; font-weight: bold; "
            f"border: 1px solid #ff4444; border-radius: 4px;")
        btn_remove.clicked.connect(lambda: self._remove_fx(item))
        self._content_layout.addWidget(btn_remove)

        self._content_layout.addStretch()

    def _set_easing(self, item, value):
        """Muda easing e atualiza visual dos botoes."""
        item.params["easing"] = value
        self._auto_save()
        for btn, val in self._ease_buttons:
            if val == value:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['purple']}; color: #ffffff; "
                    f"font-family: Consolas; font-size: 11pt; font-weight: bold; "
                    f"border: 2px solid #bb77ff; border-radius: 4px; }}")
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C['card']}; color: {C['text3']}; "
                    f"font-family: Consolas; font-size: 11pt; "
                    f"border: 1px solid {C['border']}; border-radius: 4px; }}"
                    f"QPushButton:hover {{ border: 1px solid {C['purple']}; color: {C['text']}; }}")

    def _save_fx(self):
        self._auto_save()

    def _preview_fx(self, item):
        """Move playhead para o inicio do FX e da play."""
        try:
            app = self.window()
            app.timeline.set_playhead(item.start_time)
            app.preview._on_display_click(None)
        except Exception:
            pass

    def _remove_fx(self, item):
        """Remove o item FX da timeline."""
        if self._project and item:
            from makevid.config import PROJECTS_DIR
            self._project.remove_track_item(item.id)
            self._project.save(PROJECTS_DIR)
            self._title.setText("EFEITOS")
            self._select_tab(list(FX_TABS.keys())[0])
            try:
                app = self.window()
                app.timeline.redraw()
            except Exception:
                pass

    def _build_fx_params(self, item):
        """Constroi parametros especificos por tipo de FX."""
        L = self._content_layout
        # Remover emojis para comparar nome
        name = ''.join(c for c in item.name.lower() if c.isascii())

        if "flash" in name or "fade" in name:
            # Color picker visual
            self._build_color_picker(L, item)
        elif "glitch" in name:
            self._fx_slider(L, item, "frequency", "FREQUÊNCIA GLITCH", 1, 30, int(item.params.get("frequency", 10)), "", "#aa44ff")
            self._fx_slider(L, item, "rgb_shift", "RGB SHIFT", 0, 20, int(item.params.get("rgb_shift", 5)), "px", "#ff44aa")
        elif "blur" in name:
            self._fx_slider(L, item, "radius", "RAIO DO BLUR", 1, 30, int(item.params.get("radius", 5)), "px", "#4488ff")
        elif "shake" in name:
            self._fx_slider(L, item, "amplitude", "AMPLITUDE", 1, 30, int(item.params.get("amplitude", 8)), "px", "#ff8844")
            self._fx_slider(L, item, "speed", "VELOCIDADE", 1, 20, int(item.params.get("speed", 10)), "x", "#ffaa44")
        elif "color shift" in name or "rgb split" in name or "chromatic" in name:
            self._fx_slider(L, item, "red_shift", "RED SHIFT", -20, 20, int(item.params.get("red_shift", 0)), "px", "#ff4444")
            self._fx_slider(L, item, "green_shift", "GREEN SHIFT", -20, 20, int(item.params.get("green_shift", 0)), "px", "#44ff44")
            self._fx_slider(L, item, "blue_shift", "BLUE SHIFT", -20, 20, int(item.params.get("blue_shift", 0)), "px", "#4444ff")
        elif "vignette" in name:
            self._fx_slider(L, item, "radius", "RAIO", 20, 100, int(item.params.get("radius", 60)), "%", "#885533")
            self._fx_slider(L, item, "softness", "SUAVIDADE", 10, 100, int(item.params.get("softness", 50)), "%", "#aa7744")
        elif "pixelate" in name:
            self._fx_slider(L, item, "pixel_size", "TAMANHO PIXEL", 2, 32, int(item.params.get("pixel_size", 8)), "px", "#44ccaa")
        elif "film grain" in name or "noise" in name:
            self._fx_slider(L, item, "amount", "QUANTIDADE", 5, 80, int(item.params.get("amount", 30)), "", "#aa8855")
        elif "letterbox" in name:
            self._fx_slider(L, item, "bar_size", "TAMANHO BARRAS", 5, 25, int(item.params.get("bar_size", 12)), "%", "#666666")
        elif "sepia" in name:
            self._fx_slider(L, item, "strength", "FORÇA", 0, 100, int(item.params.get("strength", 80)), "%", "#cc9944")
        elif "wipe" in name:
            self._fx_slider(L, item, "edge_softness", "SUAVIDADE BORDA", 0, 50, int(item.params.get("edge_softness", 0)), "px", "#8855bb")

    def _build_color_picker(self, layout, item):
        """Color picker com espectro HSV visual."""
        from PySide6.QtGui import QImage, QPixmap
        import colorsys

        lbl = QLabel("COR")
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        layout.addWidget(lbl)

        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 4px;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setSpacing(4)

        # Espectro 200x80
        pw, ph = 200, 80
        img = QImage(pw, ph, QImage.Format_RGB888)
        for x in range(pw):
            hue = x / pw
            for y in range(ph):
                val = 1.0 - (y / ph)
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, val)
                img.setPixelColor(x, y, QColor(int(r*255), int(g*255), int(b*255)))

        spectrum_lbl = QLabel()
        spectrum_lbl.setPixmap(QPixmap.fromImage(img))
        spectrum_lbl.setFixedSize(pw, ph)
        spectrum_lbl.setCursor(Qt.CrossCursor)
        fl.addWidget(spectrum_lbl)

        # Cor atual
        saved_color = item.params.get("color", "255,255,255" if "flash" in item.name.lower() else "0,0,0")
        rgb = [int(x) for x in saved_color.split(",")]

        color_row = QHBoxLayout()
        self._color_swatch = QLabel()
        self._color_swatch.setFixedSize(32, 32)
        self._color_swatch.setStyleSheet(
            f"background: rgb({rgb[0]},{rgb[1]},{rgb[2]}); border: 2px solid {C['border']}; border-radius: 4px;")
        color_row.addWidget(self._color_swatch)

        self._color_info = QLabel(f"R:{rgb[0]} G:{rgb[1]} B:{rgb[2]}")
        self._color_info.setStyleSheet(f"color: {C['text']}; font-family: Consolas; font-size: 9pt; font-weight: bold;")
        color_row.addWidget(self._color_info)
        color_row.addStretch()
        fl.addLayout(color_row)

        # Click no espectro
        def on_spectrum_click(event, it=item):
            x = max(0, min(pw-1, int(event.position().x())))
            y = max(0, min(ph-1, int(event.position().y())))
            hue = x / pw
            val = 1.0 - (y / ph)
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, val)
            ri, gi, bi = int(r*255), int(g*255), int(b*255)
            it.params["color"] = f"{ri},{gi},{bi}"
            self._color_swatch.setStyleSheet(
                f"background: rgb({ri},{gi},{bi}); border: 2px solid {C['border']}; border-radius: 4px;")
            self._color_info.setText(f"R:{ri} G:{gi} B:{bi}")
            self._auto_save()

        spectrum_lbl.mousePressEvent = on_spectrum_click
        spectrum_lbl.mouseMoveEvent = on_spectrum_click

        layout.addWidget(frame)

    def _fx_slider(self, layout, item, param_key, label, mn, mx, default, unit, color):
        """Cria slider para parametro de FX com salvamento automatico."""
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        sl = QSlider(Qt.Horizontal)
        sl.setRange(mn, mx)
        sl.setValue(default)
        sl.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['input']}; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 3px; }}")
        row.addWidget(sl)
        val_lbl = QLabel(f"{default}{unit}")
        val_lbl.setFixedWidth(45)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold;")
        sl.valueChanged.connect(lambda v, l=val_lbl, u=unit, k=param_key, it=item: [
            l.setText(f"{v}{u}"),
            it.params.__setitem__(k, str(v)),
            self._auto_save(),
        ])
        row.addWidget(val_lbl)
        layout.addLayout(row)

    def _auto_save(self):
        """Salva projeto automaticamente ao mudar parametro."""
        if self._project:
            from makevid.config import PROJECTS_DIR
            self._project.save(PROJECTS_DIR)
