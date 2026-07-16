"""FX Generic Editor — editor de parâmetros para efeitos não-fade."""

import colorsys

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QSlider
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter

from makevid.qt.theme import C
from makevid.qt.panels.fx_base import FxEditorBase


class FxGenericEditor(FxEditorBase):
    """Editor genérico de FX com sliders por tipo de efeito."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def _build(self, item):
        L = self._layout

        info = QLabel(f"{item.name}  ·  {item.duration:.1f}s  ·  Início: {item.start_time:.1f}s")
        info.setStyleSheet(f"color: {C['text3']}; font-size: 8pt;")
        L.addWidget(info)

        self._fx_slider(L, item, "intensity", "INTENSIDADE", 0, 100,
                        self._param_int(item.params, "intensity", 100), "%", C["purple"])
        self._build_easing_section(item)
        self._build_fx_params(item)
        self._build_action_buttons(item)

    # ── easing ────────────────────────────────────────────────────────────────

    def _build_easing_section(self, item):
        L = self._layout
        current_easing = item.params.get("easing", "linear")
        easing_options = [
            ("linear",      "━━━", "Linear",  "Intensidade constante durante todo o efeito."),
            ("ease-in",     "╭━━", "Entrada", "Começa suave e acelera no decorrer do efeito."),
            ("ease-out",    "━━╮", "Saída",   "Começa forte e suaviza no final do efeito."),
            ("ease-in-out", "╭━╮", "Suave",   "Suave no início e no fim, mais intenso no meio."),
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
        L.addWidget(ease_frame)

        self._ease_hint = QLabel(self._ease_hint_map.get(current_easing, ""))
        self._ease_hint.setWordWrap(True)
        self._ease_hint.setStyleSheet(f"color: {C['text3']}; font-size: 8pt; border: none; padding: 0 2px;")
        L.addWidget(self._ease_hint)

    def _set_easing(self, item, value):
        item.params["easing"] = value
        self._auto_save()
        for btn, val in self._ease_buttons:
            btn.setStyleSheet(self._ease_btn_style(val == value))
        if hasattr(self, "_ease_hint") and self._ease_hint:
            self._ease_hint.setText(self._ease_hint_map.get(value, ""))

    def _ease_btn_style(self, is_active):
        if is_active:
            return (
                f"QPushButton {{ background: {C['secondary']}; color: {C['text']}; "
                f"font-size: 8pt; font-weight: bold; "
                f"border: 2px solid {C['accent']}; border-radius: 4px; padding: 0 6px; }}"
            )
        return (
            f"QPushButton {{ background: {C['glass']}; color: {C['text3']}; "
            f"font-size: 8pt; font-weight: bold; "
            f"border: 1px solid {C['glass_border']}; border-radius: 4px; padding: 0 6px; }}"
            f"QPushButton:hover {{ border: 1px solid {C['secondary']}; color: {C['text']}; }}"
        )

    # ── params por tipo ───────────────────────────────────────────────────────

    def _build_fx_params(self, item):
        L = self._layout
        name = "".join(c for c in item.name.lower() if c.isascii())

        sec = QLabel("MENU DO EFEITO")
        sec.setStyleSheet(f"color: {C['text3']}; font-size: 8pt; font-weight: bold; letter-spacing: 1px;")
        L.addWidget(sec)

        if "flash" in name or "fade" in name:
            self._preset_row(L, "PRESETS RÁPIDOS", item, [
                ("Noir",  {"intensity": 70,  "color": "0,0,0"}),
                ("Flash", {"intensity": 100, "color": "255,255,255"}),
                ("Warm",  {"intensity": 85,  "color": "255,200,120"}),
            ])
            self._build_color_picker(L, item)
        elif "glitch" in name:
            self._preset_row(L, "PRESETS GLITCH", item, [
                ("Suave", {"frequency": 6,  "rgb_shift": 2}),
                ("Medio", {"frequency": 12, "rgb_shift": 6}),
                ("Caos",  {"frequency": 22, "rgb_shift": 12}),
            ])
            self._fx_slider(L, item, "frequency", "FREQUÊNCIA GLITCH", 1, 30, self._param_int(item.params, "frequency", 10), "", "#aa44ff")
            self._fx_slider(L, item, "rgb_shift",  "RGB SHIFT",         0, 20, self._param_int(item.params, "rgb_shift",  5),  "px", "#ff44aa")
        elif "blur" in name:
            self._fx_slider(L, item, "radius", "RAIO DO BLUR", 1, 30, self._param_int(item.params, "radius", 5), "px", "#4488ff")
        elif "shake" in name:
            self._preset_row(L, "PRESETS SHAKE", item, [
                ("Handheld",  {"amplitude": 5,  "speed": 8}),
                ("Impacto",   {"amplitude": 14, "speed": 13}),
                ("Frenetico", {"amplitude": 22, "speed": 18}),
            ])
            self._fx_slider(L, item, "amplitude", "AMPLITUDE",   1, 30, self._param_int(item.params, "amplitude", 8),  "px", "#ff8844")
            self._fx_slider(L, item, "speed",     "VELOCIDADE",  1, 20, self._param_int(item.params, "speed",     10), "x",  "#ffaa44")
        elif "color shift" in name or "rgb split" in name or "chromatic" in name:
            self._preset_row(L, "PRESETS RGB", item, [
                ("Clean",   {"red_shift": 0,  "green_shift": 0,  "blue_shift": 0}),
                ("Split",   {"red_shift": 4,  "green_shift": -2, "blue_shift": 3}),
                ("Extreme", {"red_shift": 10, "green_shift": -8, "blue_shift": 12}),
            ])
            self._fx_slider(L, item, "red_shift",   "RED SHIFT",   -20, 20, self._param_int(item.params, "red_shift",   0), "px", "#ff4444")
            self._fx_slider(L, item, "green_shift", "GREEN SHIFT", -20, 20, self._param_int(item.params, "green_shift", 0), "px", "#44ff44")
            self._fx_slider(L, item, "blue_shift",  "BLUE SHIFT",  -20, 20, self._param_int(item.params, "blue_shift",  0), "px", "#4444ff")
        elif "vignette" in name:
            self._fx_slider(L, item, "radius",   "RAIO",       20, 100, self._param_int(item.params, "radius",   60), "%", "#885533")
            self._fx_slider(L, item, "softness", "SUAVIDADE",  10, 100, self._param_int(item.params, "softness", 50), "%", "#aa7744")
        elif "pixelate" in name:
            self._fx_slider(L, item, "pixel_size", "TAMANHO PIXEL", 2, 32, self._param_int(item.params, "pixel_size", 8), "px", "#44ccaa")
        elif "film grain" in name or "noise" in name:
            self._fx_slider(L, item, "amount", "QUANTIDADE", 5, 80, self._param_int(item.params, "amount", 30), "", "#aa8855")
        elif "letterbox" in name:
            self._fx_slider(L, item, "bar_size", "TAMANHO BARRAS", 5, 25, self._param_int(item.params, "bar_size", 12), "%", "#666666")
        elif "sepia" in name:
            self._fx_slider(L, item, "strength", "FORÇA", 0, 100, self._param_int(item.params, "strength", 80), "%", "#cc9944")
        elif "wipe" in name:
            self._fx_slider(L, item, "edge_softness", "SUAVIDADE BORDA", 0, 50, self._param_int(item.params, "edge_softness", 0), "px", "#8855bb")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _preset_row(self, layout, title, item, presets):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px;")
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
        self.load(item, self._project)

    def _build_color_picker(self, layout, item):
        lbl = QLabel("COR")
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px;")
        layout.addWidget(frame)

        outer = QVBoxLayout(frame)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)
        outer.addWidget(lbl)

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
        outer.addWidget(spectrum_lbl)

        saved_color = item.params.get("color", "255,255,255" if "flash" in item.name.lower() else "0,0,0")
        rgb = list(self._param_color(item.params, "color",
                                     (255, 255, 255) if "flash" in item.name.lower() else (0, 0, 0)))
        alpha_default = self._param_int(item.params, "color_opacity", 100)

        color_row = QHBoxLayout()
        color_swatch = QLabel()
        color_swatch.setFixedSize(32, 32)
        color_swatch.setStyleSheet(
            f"background: rgb({rgb[0]},{rgb[1]},{rgb[2]}); border: 2px solid {C['border']}; border-radius: 4px;"
        )
        color_row.addWidget(color_swatch)

        color_info = QLabel(f"R:{rgb[0]} G:{rgb[1]} B:{rgb[2]}")
        color_info.setStyleSheet(f"color: {C['text']}; font-family: Consolas; font-size: 9pt; font-weight: bold;")
        color_row.addWidget(color_info)
        color_row.addStretch()
        outer.addLayout(color_row)

        alpha_row = QHBoxLayout()
        alpha_row.setSpacing(6)
        alpha_lbl = QLabel("OPACIDADE")
        alpha_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold;")
        alpha_row.addWidget(alpha_lbl)

        alpha_slider = QSlider(Qt.Horizontal)
        alpha_slider.setRange(0, 100)
        alpha_slider.setValue(alpha_default)
        alpha_slider.setFocusPolicy(Qt.StrongFocus)
        alpha_slider.wheelEvent = lambda e: e.ignore()
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
        outer.addLayout(alpha_row)

        def on_spectrum_click(event):
            x = max(0, min(pw-1, int(event.position().x())))
            y = max(0, min(ph-1, int(event.position().y())))
            r, g, b = colorsys.hsv_to_rgb(x / pw, 1.0, 1.0 - y / ph)
            ri, gi, bi = int(r*255), int(g*255), int(b*255)
            item.params["color"] = f"{ri},{gi},{bi}"
            color_swatch.setStyleSheet(
                f"background: rgb({ri},{gi},{bi}); border: 2px solid {C['border']}; border-radius: 4px;"
            )
            color_info.setText(f"R:{ri} G:{gi} B:{bi}")
            self._auto_save()

        spectrum_lbl.mousePressEvent = on_spectrum_click
        spectrum_lbl.mouseMoveEvent  = on_spectrum_click

        def _on_alpha(v):
            alpha_val.setText(f"{v}%")
            item.params["color_opacity"] = str(v)
            self._auto_save()

        alpha_slider.valueChanged.connect(_on_alpha)

    def _fx_slider(self, layout, item, param_key, label, mn, mx, default, unit, color):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 7, 8, 7)
        fl.setSpacing(4)

        head = QHBoxLayout()
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

        sl = QSlider(Qt.Horizontal)
        sl.setRange(mn, mx)
        sl.setValue(default)
        sl.setFocusPolicy(Qt.StrongFocus)
        sl.wheelEvent = lambda e: e.ignore()
        sl.setStyleSheet(
            f"QSlider::groove:horizontal {{ background: {C['input']}; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 3px; }}"
        )
        def _on_slider(v):
            val_lbl.setText(f"{v}{unit}")
            item.params[param_key] = str(v)
            self._auto_save()

        sl.valueChanged.connect(_on_slider)
        fl.addWidget(sl)
        layout.addWidget(frame)


