"""FX Panel Qt - Efeitos visuais com abas e grid (replica do antigo)."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSlider
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from makevid.qt.theme import C
from makevid.data.fx_definitions import FX_TABS, FX_TOOLTIPS, FX_TAB_TOOLTIPS


# Icones pixel art 8x8 para cada FX — um por efeito, intuitivo
_FX_ICONS = {
    # TRANSICOES
    "Fade In": [       # retangulo escuro -> claro (esquerda escura, direita clara)
        "00000001",
        "00000011",
        "00000111",
        "00001111",
        "00011111",
        "00111111",
        "01111111",
        "11111111",
    ],
    "Fade Out": [      # retangulo claro -> escuro (inverso do fade in)
        "11111111",
        "01111111",
        "00111111",
        "00011111",
        "00001111",
        "00000111",
        "00000011",
        "00000001",
    ],
    "Flash": [         # explosao de luz central
        "00010000",
        "01010100",
        "00111000",
        "11111110",
        "11111110",
        "00111000",
        "01010100",
        "00010000",
    ],
    "Wipe Left": [     # barra vertical varrendo para esquerda
        "11110000",
        "11110000",
        "11110000",
        "11111000",
        "11111000",
        "11110000",
        "11110000",
        "11110000",
    ],
    "Wipe Right": [    # barra vertical varrendo para direita
        "00001111",
        "00001111",
        "00001111",
        "00011111",
        "00011111",
        "00001111",
        "00001111",
        "00001111",
    ],
    "Dissolve": [      # pontos espalhados (dissolve)
        "10100101",
        "01010010",
        "10001101",
        "01110010",
        "10011101",
        "01100010",
        "10010101",
        "01001010",
    ],
    # MOVIMENTO
    "Shake": [         # linhas deslocadas horizontalmente
        "11111111",
        "00000000",
        "01111111",
        "00000000",
        "11111110",
        "00000000",
        "01111111",
        "00000000",
    ],
    "Slide": [         # seta apontando para direita
        "00010000",
        "00110000",
        "01111111",
        "11111111",
        "11111111",
        "01111111",
        "00110000",
        "00010000",
    ],
    "Zoom": [          # lupa / quadrado expandindo
        "01111110",
        "10000001",
        "10000001",
        "10000001",
        "10000001",
        "01111100",
        "00001110",
        "00000111",
    ],
    "Bounce": [        # bola quicando com sombra
        "00111100",
        "01111110",
        "01111110",
        "00111100",
        "00011000",
        "00011000",
        "00000000",
        "01111110",
    ],
    "Rotate": [        # seta circular
        "00111000",
        "01000100",
        "10000010",
        "10000110",
        "10001110",
        "01000100",
        "00111000",
        "00001110",
    ],
    "Spin": [          # espiral / raios de rotacao
        "00011000",
        "01100110",
        "10011001",
        "11000011",
        "11000011",
        "10011001",
        "01100110",
        "00011000",
    ],
    # ESTILO
    "Blur": [          # bordas difusas / circulo desfocado
        "00111100",
        "01111110",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "01111110",
        "00111100",
    ],
    "Color Shift": [   # tres colunas RGB deslocadas
        "11000000",
        "11001100",
        "11001100",
        "00001100",
        "00001111",
        "00000011",
        "00110011",
        "00110000",
    ],
    "Sepia": [         # sol / circulo quente
        "00111100",
        "01111110",
        "11011011",
        "11100111",
        "11100111",
        "11011011",
        "01111110",
        "00111100",
    ],
    "Vignette": [      # bordas escuras, centro claro
        "11111111",
        "10000001",
        "10011001",
        "10111101",
        "10111101",
        "10011001",
        "10000001",
        "11111111",
    ],
    "Film Grain": [    # pontos de grao aleatorios
        "10010010",
        "01001001",
        "00100100",
        "10010010",
        "01001001",
        "00100100",
        "10010010",
        "01001001",
    ],
    "Pixelate": [      # grade de pixels grandes
        "11001100",
        "11001100",
        "00110011",
        "00110011",
        "11001100",
        "11001100",
        "00110011",
        "00110011",
    ],
    "Letterbox": [     # barras horizontais topo e base
        "11111111",
        "11111111",
        "00000000",
        "00000000",
        "00000000",
        "00000000",
        "11111111",
        "11111111",
    ],
    "Invert": [        # metade preta metade branca invertida
        "11110000",
        "11110000",
        "11110000",
        "11110000",
        "00001111",
        "00001111",
        "00001111",
        "00001111",
    ],
    # GLITCH
    "Glitch": [        # linhas deslocadas irregulares
        "11111111",
        "00001111",
        "11110000",
        "11111111",
        "11111111",
        "00001111",
        "11110000",
        "11111111",
    ],
    "RGB Split": [     # tres camadas deslocadas R G B
        "11000000",
        "11100000",
        "01110000",
        "00111000",
        "00011100",
        "00001110",
        "00000111",
        "00000011",
    ],
    "VHS": [           # linhas horizontais de scan
        "11111111",
        "00000000",
        "11111111",
        "00000000",
        "11111111",
        "00000000",
        "11111111",
        "00000000",
    ],
    "Neon": [          # estrela / brilho irradiando
        "00010000",
        "00010000",
        "11111111",
        "00111100",
        "00111100",
        "11111111",
        "00010000",
        "00010000",
    ],
    "Pulse": [         # ondas concentricas
        "00111100",
        "01000010",
        "10011001",
        "10100101",
        "10100101",
        "10011001",
        "01000010",
        "00111100",
    ],
    "Camera": [        # lente de camera
        "01111110",
        "10000001",
        "10111101",
        "11011011",
        "11011011",
        "10111101",
        "10000001",
        "01111110",
    ],
}

# Cores por efeito
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
    """Widget que desenha icone pixel art 8x8 escalado."""

    def __init__(self, fx_name, parent=None):
        super().__init__(parent)
        # Remove emoji prefix se houver (ex: "🎬 Fade In" -> "Fade In")
        clean = fx_name.strip()
        # Percorre caracteres até achar letra ASCII
        for i, ch in enumerate(clean):
            if ch.isascii() and ch.isalpha():
                clean = clean[i:].strip()
                break
        self._grid = _FX_ICONS.get(clean)
        if self._grid is None:
            # Tenta match parcial
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
        self.setMinimumWidth(0)
        self.setObjectName("fxPanel")
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
        self._content_scroll = QScrollArea(self)
        self._content_scroll.setWidgetResizable(True)
        self._content_scroll.setStyleSheet("border: none;")
        self._content_widget = QWidget(self._content_scroll)
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
        self._tab_bar.show()
        self._title.setText("EFEITOS")

        # Atualizar visual dos botoes
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
            f"QFrame#fxCard {{ background: {C['glass']}; border: 1px solid {C['glass_border']}; border-radius: 10px; }}"
            f"QFrame#fxCard:hover {{ border: 1px solid {C['primary']}; background: {C['glass_hover']}; }}")
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

        # Texto — usa o name direto (sem emoji, já vem limpo do FX_TABS)
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
        self._tab_bar.hide()

        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        name_lower = item.name.lower()
        is_fade = "fade" in name_lower or "flash" in name_lower

        if is_fade:
            self._build_fade_editor(item)
        else:
            self._build_generic_editor(item)

        self._content_layout.addStretch()

    # ── editor generico (nao-fade) ────────────────────────────────────────────

    def _build_generic_editor(self, item):
        L = self._content_layout

        info = QLabel(f"{item.name}  ·  {item.duration:.1f}s  ·  Início: {item.start_time:.1f}s")
        info.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        L.addWidget(info)

        self._fx_slider(L, item, "intensity", "INTENSIDADE", 0, 100,
                        int(item.params.get("intensity", 100)), "%", C['purple'])
        self._build_easing_section(L, item)
        self._build_fx_params(item)
        self._build_action_buttons(item)

    # ── editor profissional fade/flash ────────────────────────────────────────

    def _build_fade_editor(self, item):
        L = self._content_layout

        # ── Header info ──────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(
            f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 10px;"
        )
        hdr_l = QVBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 10, 12, 10)
        hdr_l.setSpacing(3)

        row1 = QHBoxLayout()
        fx_lbl = QLabel(item.name)
        fx_lbl.setStyleSheet(
            f"color: {C['text']}; font-size: 11pt; font-weight: bold; border: none;"
        )
        row1.addWidget(fx_lbl)
        row1.addStretch()
        hdr_l.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        for label, param, value in [
            ("DURAÇÃO",  "duration",   f"{item.duration:.1f}"),
            ("INÍCIO",   "start_time", f"{item.start_time:.1f}"),
        ]:
            from PySide6.QtWidgets import QLineEdit
            col = QVBoxLayout()
            col.setSpacing(1)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;")
            col.addWidget(lbl)
            edit = QLineEdit(value)
            edit.setFixedWidth(60)
            edit.setFixedHeight(22)
            edit.setStyleSheet(
                f"background: rgba(10,16,30,0.70); color: {C['accent']}; "
                f"font-family: Consolas; font-size: 9pt; font-weight: bold; "
                f"border: 1px solid rgba(255,255,255,0.12); border-radius: 5px; padding: 0 4px;"
            )
            def _make_handler(p, e):
                def _on_edit():
                    try:
                        v = float(e.text().replace(",", "."))
                        if v < 0:
                            v = 0.0
                        setattr(item, p, v)
                        e.setText(f"{v:.1f}")
                        self._auto_save()
                        try:
                            self.window().timeline.rebuild_scene()
                        except Exception:
                            pass
                    except ValueError:
                        e.setText(f"{getattr(item, p):.1f}")
                return _on_edit
            edit.editingFinished.connect(_make_handler(param, edit))
            col.addWidget(edit)
            row2.addLayout(col)
        row2.addStretch()
        hdr_l.addLayout(row2)
        L.addWidget(hdr)

        # ── Presets ───────────────────────────────────────────────────────────
        custom_thumb_ref = self._build_fade_presets(L, item)

        # ── Appearance ────────────────────────────────────────────────────────
        shared = {"on_color_change": None}
        self._appearance_section = self._build_fade_appearance(L, item, shared, custom_thumb_ref)

        # ── Animation ─────────────────────────────────────────────────────────
        self._build_fade_animation(L, item)

        # ── Preview ───────────────────────────────────────────────────────────
        self._build_fade_preview(L, item)

        self._build_action_buttons(item)

    # ── appearance: color picker HSV completo ───────────────────────────────

    def _build_fade_appearance(self, layout, item, shared, custom_thumb_ref=None):
        import colorsys
        from PySide6.QtWidgets import QLineEdit
        from PySide6.QtGui import QPainter, QLinearGradient, QImage, QPixmap  # QLinearGradient usado em _render_spectrum

        section = self._section_frame("▾ Appearance")
        body_l  = section.layout()

        # ── parse cor salva ──────────────────────────────────────────────────
        default_color = "255,255,255" if "flash" in item.name.lower() else "0,0,0"
        saved = item.params.get("color", default_color)
        try:
            ri, gi, bi = [int(x) for x in saved.split(",")]
        except Exception:
            ri, gi, bi = 0, 0, 0
        SP_W, SP_H = 194, 110   # espectro
        HUE_H      = 14          # barra de matiz

        # ── renders ─────────────────────────────────────────────────────────
        def _render_spectrum(hue_norm):
            """Quadrado SV: eixo X = saturação, eixo Y = valor."""
            img = QImage(SP_W, SP_H, QImage.Format_RGB888)
            p   = QPainter(img)
            rh, gh, bh = colorsys.hsv_to_rgb(hue_norm, 1.0, 1.0)
            base = QColor(int(rh*255), int(gh*255), int(bh*255))
            # gradiente horizontal: branco -> cor pura
            for x in range(SP_W):
                sat = x / (SP_W - 1)
                gr  = QLinearGradient(0, 0, 0, SP_H)
                rr  = int(255 + (base.red()   - 255) * sat)
                gg  = int(255 + (base.green() - 255) * sat)
                bb  = int(255 + (base.blue()  - 255) * sat)
                gr.setColorAt(0.0, QColor(rr, gg, bb))
                gr.setColorAt(1.0, QColor(0, 0, 0))
                p.fillRect(x, 0, 1, SP_H, gr)
            p.end()
            return QPixmap.fromImage(img)

        def _render_hue_bar():
            img = QImage(SP_W, HUE_H, QImage.Format_RGB888)
            p   = QPainter(img)
            for x in range(SP_W):
                rr, gg, bb = colorsys.hsv_to_rgb(x / (SP_W - 1), 1.0, 1.0)
                p.fillRect(x, 0, 1, HUE_H, QColor(int(rr*255), int(gg*255), int(bb*255)))
            p.end()
            return QPixmap.fromImage(img)

        # ── estado interno ───────────────────────────────────────────────────
        h0, s0, v0 = colorsys.rgb_to_hsv(ri/255, gi/255, bi/255)
        state = {"h": h0, "s": s0, "v": v0}

        # ── espectro SV ──────────────────────────────────────────────────────
        sv_lbl = QLabel()
        sv_lbl.setFixedSize(SP_W, SP_H)
        sv_lbl.setCursor(Qt.CrossCursor)
        sv_lbl.setStyleSheet(
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 6px;"
        )
        sv_lbl.setPixmap(_render_spectrum(h0))
        body_l.addWidget(sv_lbl)

        # ── barra de matiz ───────────────────────────────────────────────────
        hue_lbl = QLabel()
        hue_lbl.setFixedSize(SP_W, HUE_H)
        hue_lbl.setCursor(Qt.SizeHorCursor)
        hue_lbl.setStyleSheet(
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; margin-top: 4px;"
        )
        hue_lbl.setPixmap(_render_hue_bar())
        body_l.addWidget(hue_lbl)

        # ── linha inferior: swatch + HEX + RGB + opacidade + reset ──────────
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        info_row.setContentsMargins(0, 6, 0, 0)

        swatch = QLabel()
        swatch.setFixedSize(36, 36)
        swatch.setStyleSheet(
            f"background: rgb({ri},{gi},{bi}); "
            f"border: 2px solid rgba(255,255,255,0.25); border-radius: 6px;"
        )
        info_row.addWidget(swatch)

        fields_col = QVBoxLayout()
        fields_col.setSpacing(2)

        hex_edit = QLineEdit(f"#{ri:02X}{gi:02X}{bi:02X}")
        hex_edit.setFixedHeight(20)
        hex_edit.setMaxLength(7)
        hex_edit.setStyleSheet(
            f"background: rgba(10,16,30,0.70); color: {C['accent']}; "
            f"font-family: Consolas; font-size: 9pt; font-weight: bold; "
            f"border: 1px solid rgba(255,255,255,0.12); border-radius: 5px; padding: 0 6px;"
        )
        fields_col.addWidget(hex_edit)

        rgb_lbl = QLabel(f"R {ri}  G {gi}  B {bi}")
        rgb_lbl.setStyleSheet(
            f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;"
        )
        fields_col.addWidget(rgb_lbl)
        info_row.addLayout(fields_col)
        body_l.addLayout(info_row)

        # ── função central ───────────────────────────────────────────────────
        def _apply_color(r, g, b, save=True):
            swatch.setStyleSheet(
                f"background: rgb({r},{g},{b}); "
                f"border: 2px solid rgba(255,255,255,0.25); border-radius: 6px;"
            )
            rgb_lbl.setText(f"R {r}  G {g}  B {b}")
            hex_edit.blockSignals(True)
            hex_edit.setText(f"#{r:02X}{g:02X}{b:02X}")
            hex_edit.blockSignals(False)
            # atualiza thumbnail do card Custom
            if custom_thumb_ref and custom_thumb_ref[0] is not None:
                from PySide6.QtGui import QImage, QPixmap, QPainter, QLinearGradient
                w, h = 48, 28
                img = QImage(w, h, QImage.Format_RGB888)
                p   = QPainter(img)
                is_fi = "fade in" in item.name.lower()
                gr = QLinearGradient(0, 0, w, 0)
                if is_fi:
                    gr.setColorAt(0.0, QColor(r, g, b))
                    gr.setColorAt(1.0, QColor(20, 20, 30))
                else:
                    gr.setColorAt(0.0, QColor(20, 20, 30))
                    gr.setColorAt(1.0, QColor(r, g, b))
                p.fillRect(0, 0, w, h, gr)
                p.end()
                custom_thumb_ref[0].setPixmap(QPixmap.fromImage(img))
            if save:
                item.params["color"] = f"{r},{g},{b}"
                self._auto_save()

        # ── clique no espectro SV ────────────────────────────────────────────
        def _sv_pick(event):
            x = max(0, min(SP_W - 1, int(event.position().x())))
            y = max(0, min(SP_H - 1, int(event.position().y())))
            state["s"] = x / (SP_W - 1)
            state["v"] = 1.0 - y / (SP_H - 1)
            rr, gg, bb = colorsys.hsv_to_rgb(state["h"], state["s"], state["v"])
            _apply_color(int(rr*255), int(gg*255), int(bb*255))

        sv_lbl.mousePressEvent = _sv_pick
        sv_lbl.mouseMoveEvent  = _sv_pick

        # ── clique na barra de matiz ─────────────────────────────────────────
        def _hue_pick(event):
            x = max(0, min(SP_W - 1, int(event.position().x())))
            state["h"] = x / (SP_W - 1)
            sv_lbl.setPixmap(_render_spectrum(state["h"]))
            rr, gg, bb = colorsys.hsv_to_rgb(state["h"], state["s"], state["v"])
            _apply_color(int(rr*255), int(gg*255), int(bb*255))

        hue_lbl.mousePressEvent = _hue_pick
        hue_lbl.mouseMoveEvent  = _hue_pick

        # ── HEX input ────────────────────────────────────────────────────────
        def _on_hex_edit():
            txt = hex_edit.text().strip().lstrip("#")
            if len(txt) == 6:
                try:
                    r, g, b = int(txt[0:2], 16), int(txt[2:4], 16), int(txt[4:6], 16)
                    state["h"], state["s"], state["v"] = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                    sv_lbl.setPixmap(_render_spectrum(state["h"]))
                    _apply_color(r, g, b)
                except ValueError:
                    pass

        hex_edit.editingFinished.connect(_on_hex_edit)

        layout.addWidget(section)
        return section

    # ── preview visual do fade ──────────────────────────────────────────────

    def _build_fade_preview(self, layout, item):
        from PySide6.QtGui import QPainter, QLinearGradient, QImage, QPixmap
        from PySide6.QtCore import QTimer

        section = self._section_frame("▾ Preview")
        body_l  = section.layout()

        PW, PH = 220, 52
        is_fade_in = "fade in" in item.name.lower()

        # ── label descritivo ─────────────────────────────────────────────────
        if is_fade_in:
            desc = "escuro/colorido opaco  →  transparente"
        elif "flash" in item.name.lower():
            desc = "flash  →  transparente"
        else:
            desc = "transparente  →  escuro/colorido opaco"

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; border: none;"
        )
        body_l.addWidget(desc_lbl)

        # ── canvas animado ──────────────────────────────────────────────────
        canvas = QLabel()
        canvas.setFixedSize(PW, PH)
        canvas.setStyleSheet(
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;"
        )
        body_l.addWidget(canvas)

        # barra de progresso da animação
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 0)
        prog_bar = QLabel()
        prog_bar.setFixedSize(PW, 3)
        prog_bar.setStyleSheet(
            f"background: rgba(255,255,255,0.08); border-radius: 1px; border: none;"
        )
        prog_row.addWidget(prog_bar)
        body_l.addLayout(prog_row)

        # botão play/pause
        play_btn = QPushButton("▶  Play")
        play_btn.setFixedHeight(26)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(28,46,74,0.55); color: {C['text2']}; "
            f"font-size: 8pt; font-weight: bold; "
            f"border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; }}"
            f"QPushButton:hover {{ color: {C['text']}; border-color: {C['secondary']}; }}"
        )
        body_l.addWidget(play_btn)

        # estado da animação
        anim = {"t": 0.0, "running": False}
        timer = QTimer()
        timer.setInterval(30)  # ~33fps

        def _get_color():
            saved = item.params.get("color", "0,0,0")
            try:
                return [int(x) for x in saved.split(",")]
            except Exception:
                return [0, 0, 0]

        def _easing(t):
            mode = item.params.get("easing", "linear")
            t = max(0.0, min(1.0, t))
            if mode == "ease-in":     return t * t
            if mode == "ease-out":    return 1.0 - (1.0 - t) ** 2
            if mode == "ease-in-out":
                return 2*t*t if t < 0.5 else 1 - (-2*t+2)**2/2
            return t

        def _draw_frame(t):
            rgb   = _get_color()
            op    = float(item.params.get("color_opacity", 100)) / 100.0
            inten = float(item.params.get("intensity", 100)) / 100.0
            et    = _easing(t)

            # alpha da camada de cor sobre fundo de cena
            if is_fade_in:
                alpha = op * inten * (1.0 - et)   # começa opaco, vai a transparente
            else:
                alpha = op * inten * et            # começa transparente, vai a opaco

            img = QImage(PW, PH, QImage.Format_RGB888)
            p   = QPainter(img)

            # fundo: simula cena (gradiente azul escuro)
            bg = QLinearGradient(0, 0, PW, PH)
            bg.setColorAt(0.0, QColor(20, 30, 55))
            bg.setColorAt(1.0, QColor(10, 16, 32))
            p.fillRect(0, 0, PW, PH, bg)

            # texto "CENA" simulado
            p.setPen(QColor(255, 255, 255, 30))
            p.setFont(p.font())
            p.drawText(PW // 2 - 18, PH // 2 + 5, "CENA")

            # camada de cor do fade
            fade_color = QColor(rgb[0], rgb[1], rgb[2], int(alpha * 255))
            p.fillRect(0, 0, PW, PH, fade_color)

            # linha indicadora de progresso
            px_x = int(t * PW)
            p.setPen(QColor(255, 255, 255, 80))
            p.drawLine(px_x, 0, px_x, PH)

            p.end()
            canvas.setPixmap(QPixmap.fromImage(img))

            # barra de progresso
            filled = int(t * PW)
            prog_bar.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 {C['primary']}, stop:{t:.3f} {C['accent']}, "
                f"stop:{min(t+0.001,1.0):.3f} rgba(255,255,255,0.08), stop:1 rgba(255,255,255,0.08));"
                f"border-radius: 1px; border: none;"
            )

        _draw_frame(0.0)

        def _tick():
            anim["t"] += 0.016  # ~1.6s de duração total
            if anim["t"] >= 1.0:
                anim["t"] = 1.0
                _draw_frame(1.0)
                timer.stop()
                anim["running"] = False
                play_btn.setText("▶  Play")
                return
            _draw_frame(anim["t"])

        def _toggle():
            if anim["running"]:
                timer.stop()
                anim["running"] = False
                play_btn.setText("▶  Play")
            else:
                anim["t"] = 0.0
                anim["running"] = True
                play_btn.setText("⏸  Pause")
                timer.start()

        timer.timeout.connect(_tick)
        play_btn.clicked.connect(_toggle)

        layout.addWidget(section)

    # ── animation: intensidade + curva ────────────────────────────────────────

    def _build_fade_animation(self, layout, item):
        from PySide6.QtGui import QPainter, QPen, QPainterPath, QColor as QC
        from PySide6.QtCore import QPointF

        section = self._section_frame("\u25be Animation")
        body_l  = section.layout()

        # ── intensidade ──────────────────────────────────────────────────────
        intensity_val = int(item.params.get("intensity", 100))

        int_head = QHBoxLayout()
        int_lbl  = QLabel("INTENSIDADE")
        int_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold; border: none;")
        int_val_lbl = QLabel(f"{intensity_val}%")
        int_val_lbl.setStyleSheet(f"color: {C['purple']}; font-size: 9pt; font-weight: bold; border: none;")
        int_head.addWidget(int_lbl)
        int_head.addStretch()
        int_head.addWidget(int_val_lbl)
        body_l.addLayout(int_head)

        int_slider = QSlider(Qt.Horizontal)
        int_slider.setRange(0, 100)
        int_slider.setValue(intensity_val)
        int_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: rgba(10,16,30,0.70); height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {C['purple']}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {C['purple']}; border-radius: 3px; }}"
        )
        body_l.addWidget(int_slider)

        def _on_intensity(v):
            int_val_lbl.setText(f"{v}%")
            item.params["intensity"] = str(v)
            self._auto_save()

        int_slider.valueChanged.connect(_on_intensity)

        # ── separador ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba(255,255,255,0.08); border: none;")
        body_l.addWidget(sep)

        # ── curva de transição ────────────────────────────────────────────────
        curve_lbl = QLabel("CURVA DE TRANSIÇÃO")
        curve_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold; border: none;")
        body_l.addWidget(curve_lbl)

        CURVES = [
            ("linear",      "Linear",    "━━━"),
            ("ease-in",     "Ease In",   "╭━━"),
            ("ease-out",    "Ease Out",  "━━╮"),
            ("ease-in-out", "Ease I/O",  "╭━╮"),
        ]
        current_easing = item.params.get("easing", "linear")

        # mini canvas para preview da curva (desenhado com QPainter)
        CURVE_W, CURVE_H = 220, 48

        curve_canvas = QLabel()
        curve_canvas.setFixedSize(CURVE_W, CURVE_H)
        curve_canvas.setStyleSheet(
            "background: rgba(10,16,30,0.70); border: 1px solid rgba(255,255,255,0.10);"
            "border-radius: 6px;"
        )

        def _easing_fn(t, mode):
            t = max(0.0, min(1.0, t))
            if mode == "ease-in":     return t * t
            if mode == "ease-out":    return 1.0 - (1.0 - t) ** 2
            if mode == "ease-in-out":
                return 2*t*t if t < 0.5 else 1 - (-2*t+2)**2/2
            return t  # linear

        def _draw_curve(mode):
            from PySide6.QtGui import QPixmap
            px  = QPixmap(CURVE_W, CURVE_H)
            px.fill(QC(10, 16, 30, 178))
            p   = QPainter(px)
            p.setRenderHint(QPainter.Antialiasing)
            pad = 10
            W   = CURVE_W - pad * 2
            H   = CURVE_H - pad * 2

            # grade sutil
            p.setPen(QPen(QC(255, 255, 255, 18), 1))
            for i in range(1, 4):
                x = pad + W * i // 4
                p.drawLine(x, pad, x, pad + H)
            for i in range(1, 3):
                y = pad + H * i // 2
                p.drawLine(pad, y, pad + W, y)

            # curva
            path = QPainterPath()
            steps = 60
            for i in range(steps + 1):
                t  = i / steps
                yt = _easing_fn(t, mode)
                x  = pad + t  * W
                y  = pad + (1.0 - yt) * H
                if i == 0:
                    path.moveTo(QPointF(x, y))
                else:
                    path.lineTo(QPointF(x, y))

            pen = QPen(QC(C["primary"]), 2)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawPath(path)

            # ponto final
            p.setBrush(QC(C["accent"]))
            p.setPen(Qt.NoPen)
            t_end = 1.0
            yt_end = _easing_fn(t_end, mode)
            p.drawEllipse(QPointF(pad + t_end * W, pad + (1.0 - yt_end) * H), 4, 4)
            p.end()
            curve_canvas.setPixmap(px)

        _draw_curve(current_easing)
        body_l.addWidget(curve_canvas)

        # botões de curva
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_row.setContentsMargins(0, 0, 0, 0)
        ease_btns = []

        def _ease_style(active):
            if active:
                return (
                    f"QPushButton {{ background: {C['secondary']}; color: {C['text']}; "
                    f"font-size: 8pt; font-weight: bold; "
                    f"border: 2px solid {C['accent']}; border-radius: 6px; padding: 2px 6px; }}"
                )
            return (
                f"QPushButton {{ background: rgba(28,46,74,0.55); color: {C['text3']}; "
                f"font-size: 8pt; font-weight: bold; "
                f"border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; padding: 2px 6px; }}"
                f"QPushButton:hover {{ color: {C['text']}; border-color: {C['secondary']}; }}"
            )

        def _select_curve(val):
            item.params["easing"] = val
            self._auto_save()
            _draw_curve(val)
            for b, v in ease_btns:
                b.setStyleSheet(_ease_style(v == val))

        for val, label, icon in CURVES:
            btn = QPushButton(f"{icon}  {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_ease_style(val == current_easing))
            btn.clicked.connect(lambda ck=False, v=val: _select_curve(v))
            btn_row.addWidget(btn)
            ease_btns.append((btn, val))

        body_l.addLayout(btn_row)
        layout.addWidget(section)

    # ── opacity / alpha ────────────────────────────────────────────────────

    def _build_fade_opacity(self, layout, item, shared):
        from PySide6.QtGui import QPainter, QLinearGradient, QImage, QPixmap

        section = self._section_frame("▾ Opacity / Alpha")
        body_l  = section.layout()

        # ── parse valores iniciais ────────────────────────────────────────────
        default_color = "255,255,255" if "flash" in item.name.lower() else "0,0,0"
        saved = item.params.get("color", default_color)
        try:
            ri, gi, bi = [int(x) for x in saved.split(",")]
        except Exception:
            ri, gi, bi = 0, 0, 0
        opacity_val = int(item.params.get("color_opacity", 100))

        BAR_W, BAR_H = 220, 18
        CHESS = 5  # tamanho do quadrado do xadrez

        # ── barra visual (QLabel clicavel) ───────────────────────────────────
        bar_lbl = QLabel()
        bar_lbl.setFixedSize(BAR_W, BAR_H)
        bar_lbl.setCursor(Qt.SizeHorCursor)
        bar_lbl.setStyleSheet(
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 5px;"
        )

        # ── linha com valor % e handle ────────────────────────────────────────
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(8)

        pct_lbl = QLabel(f"{opacity_val}%")
        pct_lbl.setFixedWidth(40)
        pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pct_lbl.setStyleSheet(
            f"color: rgb({ri},{gi},{bi}); font-size: 10pt; font-weight: bold; "
            f"font-family: Consolas; border: none;"
        )

        desc_lbl = QLabel("transparente → opaco")
        desc_lbl.setStyleSheet(
            f"color: {C['text3']}; font-size: 7pt; border: none;"
        )

        val_row.addWidget(desc_lbl)
        val_row.addStretch()
        val_row.addWidget(pct_lbl)

        body_l.addWidget(bar_lbl)
        body_l.addLayout(val_row)

        # ── função de atualização da barra ──────────────────────────────────
        def _refresh_bar(r, g, b):
            img = QImage(BAR_W, BAR_H, QImage.Format_ARGB32)
            p   = QPainter(img)
            ca  = QColor(50, 55, 68)
            cb  = QColor(80, 86, 100)
            for yy in range(0, BAR_H, CHESS):
                for xx in range(0, BAR_W, CHESS):
                    p.fillRect(xx, yy, CHESS, CHESS,
                               ca if ((xx // CHESS + yy // CHESS) % 2 == 0) else cb)
            grad = QLinearGradient(0, 0, BAR_W, 0)
            grad.setColorAt(0.0, QColor(r, g, b, 0))
            grad.setColorAt(1.0, QColor(r, g, b, 255))
            p.fillRect(0, 0, BAR_W, BAR_H, grad)
            p.end()
            bar_lbl.setPixmap(QPixmap.fromImage(img))
            pct_lbl.setStyleSheet(
                f"color: rgb({r},{g},{b}); font-size: 10pt; font-weight: bold; "
                f"font-family: Consolas; border: none;"
            )

        _refresh_bar(ri, gi, bi)

        # ── clique/drag na barra ─────────────────────────────────────────────
        def _bar_pick(event):
            x   = max(0, min(BAR_W - 1, int(event.position().x())))
            pct = round(x / (BAR_W - 1) * 100)
            pct_lbl.setText(f"{pct}%")
            item.params["color_opacity"] = str(pct)
            self._auto_save()

        bar_lbl.mousePressEvent = _bar_pick
        bar_lbl.mouseMoveEvent  = _bar_pick

        # ── registra callback para quando a cor mudar no Appearance ──────────
        shared["on_color_change"] = _refresh_bar

        layout.addWidget(section)

    # ── presets com cards visuais ─────────────────────────────────────────────

    def _build_fade_presets(self, layout, item):
        from PySide6.QtGui import QPainter, QLinearGradient, QImage, QPixmap

        section = self._section_frame("▾ Presets")
        body_l  = section.layout()

        PRESETS = [
            ("Noir",   "0,0,0",       100, "Preto clássico"),
            ("Flash",  "255,255,255",  100, "Branco intenso"),
            ("Warm",   "255,180,80",   85,  "Laranja quente"),
            ("Custom", None,           None, "Cor personalizada"),
        ]

        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)
        cards_row.setContentsMargins(0, 0, 0, 0)

        saved_color = item.params.get("color", "0,0,0")
        custom_thumb_ref = [None]  # referência mutável para o thumb do Custom

        for name, color_str, intensity, tip in PRESETS:
            card = QFrame()
            card.setFixedSize(58, 68)
            card.setCursor(Qt.PointingHandCursor)
            card.setToolTip(tip)
            card.setObjectName("presetCard")
            card.setStyleSheet(
                "QFrame#presetCard { background: rgba(28,46,74,0.55); "
                f"border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }}"
                "QFrame#presetCard:hover { border: 1px solid #6C63FF; }"
            )

            cl = QVBoxLayout(card)
            cl.setContentsMargins(5, 6, 5, 5)
            cl.setSpacing(4)

            # Miniatura de cor — gradiente fade
            thumb = QLabel()
            thumb.setFixedSize(48, 28)
            thumb.setAttribute(Qt.WA_TransparentForMouseEvents)
            thumb.setStyleSheet("border: none; background: transparent;")

            if color_str:
                rgb = [int(x) for x in color_str.split(",")]
                w, h = 48, 28
                img = QImage(w, h, QImage.Format_RGB888)
                p = QPainter(img)
                is_fade_in = "fade in" in item.name.lower()
                g = QLinearGradient(0, 0, w, 0)
                if is_fade_in:
                    g.setColorAt(0.0, QColor(rgb[0], rgb[1], rgb[2]))
                    g.setColorAt(1.0, QColor(20, 20, 30))
                else:
                    g.setColorAt(0.0, QColor(20, 20, 30))
                    g.setColorAt(1.0, QColor(rgb[0], rgb[1], rgb[2]))
                p.fillRect(0, 0, w, h, g)
                p.end()
                thumb.setPixmap(QPixmap.fromImage(img))
            else:
                # Custom: xadrez
                w, h = 48, 28
                img = QImage(w, h, QImage.Format_RGB888)
                p = QPainter(img)
                s = 6
                c1 = QColor(50, 50, 60)
                c2 = QColor(80, 80, 95)
                for yy in range(0, h, s):
                    for xx in range(0, w, s):
                        p.fillRect(xx, yy, s, s,
                                   c1 if ((xx // s + yy // s) % 2 == 0) else c2)
                p.end()
                thumb.setPixmap(QPixmap.fromImage(img))

            if color_str is None:
                custom_thumb_ref[0] = thumb

            cl.addWidget(thumb, alignment=Qt.AlignHCenter)

            name_lbl = QLabel(name)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            name_lbl.setStyleSheet(
                f"color: {C['text2']}; font-size: 8pt; font-weight: bold; border: none;"
            )
            cl.addWidget(name_lbl)

            def _on_preset(checked=False, cs=color_str, iv=intensity, it=item):
                if cs is not None:
                    it.params["color"] = cs
                    if iv is not None:
                        it.params["intensity"] = str(iv)
                    self._auto_save()
                    self.show_item(it, self._project)
                else:
                    # Custom: salva a cor atual do picker e destaca Appearance
                    self._auto_save()
                    sec = getattr(self, "_appearance_section", None)
                    if sec:
                        self._content_scroll.ensureWidgetVisible(sec)
                        sec.setStyleSheet(
                            f"QFrame {{ background: {C['card']}; "
                            f"border: 2px solid {C['accent']}; border-radius: 10px; }}"
                        )
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(800, lambda: sec.setStyleSheet(
                            f"QFrame {{ background: {C['card']}; "
                            f"border: 1px solid {C['border']}; border-radius: 10px; }}"
                        ))

            card.mousePressEvent = lambda e, fn=_on_preset: fn()
            cards_row.addWidget(card)

        cards_row.addStretch()
        body_l.addLayout(cards_row)
        layout.addWidget(section)
        return custom_thumb_ref

    # ── helpers compartilhados ──────────────────────────────────────────────

    def _section_frame(self, title):
        """Cria um QFrame colapsável com título e corpo VBox."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {C['card']}; border: 1px solid {C['border']}; "
            f"border-radius: 10px; }}"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 8, 10, 10)
        fl.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {C['text2']}; font-size: 9pt; font-weight: bold; border: none;"
        )
        fl.addWidget(lbl)
        return frame

    def _build_action_buttons(self, item):
        L = self._content_layout
        btn_preview = QPushButton("\u25b6  PREVIEW")
        btn_preview.setFixedHeight(30)
        btn_preview.setStyleSheet(
            f"background: {C['card']}; color: {C['purple']}; font-weight: bold; "
            f"border: 2px solid {C['purple']}; border-radius: 6px;"
        )
        btn_preview.clicked.connect(lambda: self._preview_fx(item))
        L.addWidget(btn_preview)

        btn_remove = QPushButton("REMOVER FX")
        btn_remove.setFixedHeight(28)
        btn_remove.setStyleSheet(
            f"background: {C['danger_bg']}; color: {C['danger']}; font-weight: bold; "
            f"border: 1px solid {C['danger']}; border-radius: 6px;"
        )
        btn_remove.clicked.connect(lambda: self._remove_fx(item))
        L.addWidget(btn_remove)

    def _build_easing_section(self, layout, item):
        current_easing = item.params.get("easing", "linear")
        easing_options = [
            ("linear",     "━━━", "Linear",  "Intensidade constante durante todo o efeito."),
            ("ease-in",    "╭━━", "Entrada", "Começa suave e acelera no decorrer do efeito."),
            ("ease-out",   "━━╮", "Saída",   "Começa forte e suaviza no final do efeito."),
            ("ease-in-out","╭━╮", "Suave",   "Suave no início e no fim, mais intenso no meio."),
        ]
        self._ease_hint_map = {v: h for v, _, _, h in easing_options}

        ease_frame = QFrame()
        ease_frame.setStyleSheet(f"background: {C['card']}; border-radius: 4px;")
        ease_layout = QHBoxLayout(ease_frame)
        ease_layout.setContentsMargins(4, 4, 4, 4)
        ease_layout.setSpacing(3)

        self._ease_buttons = []
        for val, icon, label, tip in easing_options:
            btn = QPushButton(f"{icon} {label}")
            btn.setFixedSize(84, 28)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._ease_btn_style(val == current_easing))
            btn.clicked.connect(lambda ck=False, v=val: self._set_easing(item, v))
            ease_layout.addWidget(btn)
            self._ease_buttons.append((btn, val))
        layout.addWidget(ease_frame)

        self._ease_hint = QLabel(self._ease_hint_map.get(current_easing, ""))
        self._ease_hint.setWordWrap(True)
        self._ease_hint.setStyleSheet(
            f"color: {C['text3']}; font-size: 8pt; border: none; padding: 0 2px;"
        )
        layout.addWidget(self._ease_hint)

    def _set_easing(self, item, value):
        """Muda easing e atualiza visual dos botoes."""
        item.params["easing"] = value
        self._auto_save()
        for btn, val in self._ease_buttons:
            btn.setStyleSheet(self._ease_btn_style(val == value))
        if hasattr(self, "_ease_hint") and self._ease_hint is not None:
            self._ease_hint.setText(self._ease_hint_map.get(value, ""))

    def _ease_btn_style(self, is_active):
        if is_active:
            return (
                f"QPushButton {{ background: {C['secondary']}; color: {C['text']}; "
                f"font-family: Segoe UI; font-size: 8pt; font-weight: bold; "
                f"border: 2px solid {C['accent']}; border-radius: 4px; padding: 0 6px; }}"
            )
        return (
            f"QPushButton {{ background: {C['glass']}; color: {C['text3']}; "
            f"font-family: Segoe UI; font-size: 8pt; font-weight: bold; "
            f"border: 1px solid {C['glass_border']}; border-radius: 4px; padding: 0 6px; }}"
            f"QPushButton:hover {{ border: 1px solid {C['secondary']}; color: {C['text']}; }}"
        )

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

        sec = QLabel("MENU DO EFEITO")
        sec.setStyleSheet(
            f"color: {C['text3']}; font-size: 8pt; font-weight: bold; letter-spacing: 1px;"
        )
        L.addWidget(sec)

        if "flash" in name or "fade" in name:
            self._preset_row(
                L,
                "PRESETS RAPIDOS",
                item,
                [
                    ("Noir", {"intensity": 70, "color": "0,0,0"}),
                    ("Flash", {"intensity": 100, "color": "255,255,255"}),
                    ("Warm", {"intensity": 85, "color": "255,200,120"}),
                ],
            )
            # Color picker visual
            self._build_color_picker(L, item)
        elif "glitch" in name:
            self._preset_row(
                L,
                "PRESETS GLITCH",
                item,
                [
                    ("Suave", {"frequency": 6, "rgb_shift": 2}),
                    ("Medio", {"frequency": 12, "rgb_shift": 6}),
                    ("Caos", {"frequency": 22, "rgb_shift": 12}),
                ],
            )
            self._fx_slider(L, item, "frequency", "FREQUÊNCIA GLITCH", 1, 30, int(item.params.get("frequency", 10)), "", "#aa44ff")
            self._fx_slider(L, item, "rgb_shift", "RGB SHIFT", 0, 20, int(item.params.get("rgb_shift", 5)), "px", "#ff44aa")
        elif "blur" in name:
            self._fx_slider(L, item, "radius", "RAIO DO BLUR", 1, 30, int(item.params.get("radius", 5)), "px", "#4488ff")
        elif "shake" in name:
            self._preset_row(
                L,
                "PRESETS SHAKE",
                item,
                [
                    ("Handheld", {"amplitude": 5, "speed": 8}),
                    ("Impacto", {"amplitude": 14, "speed": 13}),
                    ("Frenetico", {"amplitude": 22, "speed": 18}),
                ],
            )
            self._fx_slider(L, item, "amplitude", "AMPLITUDE", 1, 30, int(item.params.get("amplitude", 8)), "px", "#ff8844")
            self._fx_slider(L, item, "speed", "VELOCIDADE", 1, 20, int(item.params.get("speed", 10)), "x", "#ffaa44")
        elif "color shift" in name or "rgb split" in name or "chromatic" in name:
            self._preset_row(
                L,
                "PRESETS RGB",
                item,
                [
                    ("Clean", {"red_shift": 0, "green_shift": 0, "blue_shift": 0}),
                    ("Split", {"red_shift": 4, "green_shift": -2, "blue_shift": 3}),
                    ("Extreme", {"red_shift": 10, "green_shift": -8, "blue_shift": 12}),
                ],
            )
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

    def _preset_row(self, layout, title, item, presets):
        """Linha de presets rápidos para efeitos com menu próprio."""
        frame = QFrame()
        frame.setStyleSheet(
            f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px;"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setSpacing(6)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold;")
        fl.addWidget(lbl)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        for text, values in presets:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setStyleSheet(
                f"QPushButton {{ background: {C['glass']}; color: {C['text2']}; font-size: 8pt; font-weight: bold; "
                f"border: 1px solid {C['glass_border']}; border-radius: 6px; padding: 2px 8px; }}"
                f"QPushButton:hover {{ border: 1px solid {C['secondary']}; color: {C['text']}; }}"
            )
            btn.clicked.connect(lambda checked=False, vals=values, it=item: self._apply_preset(it, vals))
            row.addWidget(btn)
        row.addStretch()
        fl.addLayout(row)
        layout.addWidget(frame)

    def _apply_preset(self, item, values):
        for key, value in values.items():
            item.params[key] = str(value)
        self._auto_save()
        self.show_item(item, self._project)

    def _build_color_picker(self, layout, item):
        """Color picker com espectro HSV visual."""
        from PySide6.QtGui import QImage, QPixmap, QPainter, QLinearGradient
        import colorsys

        lbl = QLabel("COR")
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px;")
        layout.addWidget(frame)

        outer = QVBoxLayout(frame)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)
        outer.addWidget(lbl)

        inner = QFrame()
        inner.setStyleSheet(f"background: transparent; border: none;")
        fl = QVBoxLayout(inner)
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
        alpha_default = int(item.params.get("color_opacity", 100))

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

        alpha_row = QHBoxLayout()
        alpha_row.setContentsMargins(0, 2, 0, 0)
        alpha_row.setSpacing(6)
        alpha_lbl = QLabel("OPACIDADE")
        alpha_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold;")
        alpha_row.addWidget(alpha_lbl)

        alpha_slider = QSlider(Qt.Horizontal)
        alpha_slider.setRange(0, 100)
        alpha_slider.setValue(alpha_default)
        alpha_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['input']}; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {C['accent']}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 3px; }}"
        )
        alpha_row.addWidget(alpha_slider)

        alpha_val = QLabel(f"{alpha_default}%")
        alpha_val.setFixedWidth(44)
        alpha_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        alpha_val.setStyleSheet(f"color: {C['accent']}; font-size: 8pt; font-weight: bold;")
        alpha_row.addWidget(alpha_val)
        fl.addLayout(alpha_row)

        alpha_preview = QLabel()
        alpha_preview.setFixedHeight(12)
        alpha_preview.setStyleSheet(f"border: 1px solid {C['border']}; border-radius: 3px;")
        fl.addWidget(alpha_preview)

        def _update_alpha_visual(rr, gg, bb):
            w, h = 200, 12
            img = QImage(w, h, QImage.Format_ARGB32)
            p = QPainter(img)

            # Fundo xadrez para indicar transparência.
            s = 4
            c1 = QColor(42, 48, 62)
            c2 = QColor(78, 86, 104)
            for yy in range(0, h, s):
                for xx in range(0, w, s):
                    p.fillRect(xx, yy, s, s, c1 if ((xx // s) + (yy // s)) % 2 == 0 else c2)

            # Gradiente da própria cor: transparente -> opaco.
            g = QLinearGradient(0, 0, w, 0)
            g.setColorAt(0.0, QColor(rr, gg, bb, 0))
            g.setColorAt(1.0, QColor(rr, gg, bb, 255))
            p.fillRect(0, 0, w, h, g)
            p.end()

            alpha_preview.setPixmap(QPixmap.fromImage(img))
            alpha_slider.setStyleSheet(
                f"QSlider::groove:horizontal {{ background: {C['input']}; height: 6px; border-radius: 3px; }}"
                f"QSlider::handle:horizontal {{ background: rgb({rr},{gg},{bb}); width: 14px; margin: -4px 0; border-radius: 7px; }}"
                f"QSlider::sub-page:horizontal {{ background: rgb({rr},{gg},{bb}); border-radius: 3px; }}"
            )
            alpha_val.setStyleSheet(f"color: rgb({rr},{gg},{bb}); font-size: 8pt; font-weight: bold;")

        _update_alpha_visual(rgb[0], rgb[1], rgb[2])

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
            _update_alpha_visual(ri, gi, bi)
            self._auto_save()

        spectrum_lbl.mousePressEvent = on_spectrum_click
        spectrum_lbl.mouseMoveEvent = on_spectrum_click

        def on_alpha_change(v, it=item):
            alpha_val.setText(f"{v}%")
            it.params["color_opacity"] = str(v)
            self._auto_save()

        alpha_slider.valueChanged.connect(on_alpha_change)

        outer.addWidget(inner)

    def _fx_slider(self, layout, item, param_key, label, mn, mx, default, unit, color):
        """Cria slider para parametro de FX com salvamento automatico."""
        frame = QFrame()
        frame.setStyleSheet(
            f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px;"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 7, 8, 7)
        fl.setSpacing(4)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold;")
        head.addWidget(lbl)
        head.addStretch()

        val_lbl = QLabel(f"{default}{unit}")
        val_lbl.setFixedWidth(56)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold;")
        head.addWidget(val_lbl)
        fl.addLayout(head)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        sl = QSlider(Qt.Horizontal)
        sl.setRange(mn, mx)
        sl.setValue(default)
        sl.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['input']}; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 3px; }}")
        row.addWidget(sl)
        sl.valueChanged.connect(lambda v, l=val_lbl, u=unit, k=param_key, it=item: [
            l.setText(f"{v}{u}"),
            it.params.__setitem__(k, str(v)),
            self._auto_save(),
        ])
        fl.addLayout(row)
        layout.addWidget(frame)

    def _auto_save(self):
        """Salva projeto automaticamente ao mudar parametro."""
        if self._project:
            from makevid.config import PROJECTS_DIR
            self._project.save(PROJECTS_DIR)
