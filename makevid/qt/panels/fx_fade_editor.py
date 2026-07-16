"""FX Fade Editor — editor de fade/flash com color picker HSV, presets, animação e preview."""

import colorsys

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QSlider, QLineEdit
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QLinearGradient

from makevid.qt.theme import C
from makevid.qt.panels.fx_base import FxEditorBase

_SP_W, _SP_H, _HUE_H = 194, 110, 14
_spectrum_cache: dict[int, QPixmap] = {}   # key = round(hue * 360)
_hue_bar_cache: QPixmap | None = None


def _render_spectrum(hue_norm: float) -> QPixmap:
    key = round(hue_norm * 360)
    if key in _spectrum_cache:
        return _spectrum_cache[key]
    img = QImage(_SP_W, _SP_H, QImage.Format_RGB888)
    p = QPainter(img)
    rh, gh, bh = colorsys.hsv_to_rgb(hue_norm, 1.0, 1.0)
    base = QColor(int(rh*255), int(gh*255), int(bh*255))
    for x in range(_SP_W):
        sat = x / (_SP_W - 1)
        gr = QLinearGradient(0, 0, 0, _SP_H)
        gr.setColorAt(0.0, QColor(
            int(255 + (base.red()   - 255) * sat),
            int(255 + (base.green() - 255) * sat),
            int(255 + (base.blue()  - 255) * sat),
        ))
        gr.setColorAt(1.0, QColor(0, 0, 0))
        p.fillRect(x, 0, 1, _SP_H, gr)
    p.end()
    px = QPixmap.fromImage(img)
    _spectrum_cache[key] = px
    return px


def _render_hue_bar() -> QPixmap:
    global _hue_bar_cache
    if _hue_bar_cache is not None:
        return _hue_bar_cache
    img = QImage(_SP_W, _HUE_H, QImage.Format_RGB888)
    p = QPainter(img)
    for x in range(_SP_W):
        rr, gg, bb = colorsys.hsv_to_rgb(x / (_SP_W - 1), 1.0, 1.0)
        p.fillRect(x, 0, 1, _HUE_H, QColor(int(rr*255), int(gg*255), int(bb*255)))
    p.end()
    _hue_bar_cache = QPixmap.fromImage(img)
    return _hue_bar_cache


class FxFadeEditor(FxEditorBase):
    """Editor de fade/flash com color picker HSV, presets, animação e preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._appearance_section = None

    def _build(self, item):
        L = self._layout

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(
            f"background: {C['card']}; border: 1px solid {C['border']}; border-radius: 10px;"
        )
        hdr_l = QVBoxLayout(hdr)
        hdr_l.setContentsMargins(12, 10, 12, 10)
        hdr_l.setSpacing(3)

        row1 = QHBoxLayout()
        fx_lbl = QLabel(item.name)
        fx_lbl.setStyleSheet(f"color: {C['text']}; font-size: 11pt; font-weight: bold; border: none;")
        row1.addWidget(fx_lbl)
        row1.addStretch()
        hdr_l.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        for label, param in [("DURAÇÃO", "duration"), ("INÍCIO", "start_time")]:
            col = QVBoxLayout()
            col.setSpacing(1)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; font-weight: bold; border: none;")
            col.addWidget(lbl)
            value = f"{getattr(item, param):.1f}"
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

        # ── Seções ────────────────────────────────────────────────────────────
        custom_thumb_ref = self._build_presets(item)
        shared = {"on_color_change": None}
        self._appearance_section = self._build_appearance(item, shared, custom_thumb_ref)
        self._build_animation(item)
        self._build_preview(item)
        self._build_action_buttons(item)

    def _build_presets(self, item):
        section = self._section_frame("▾ Presets")
        body_l = section.layout()

        PRESETS = [
            ("Noir",   "0,0,0",       100, "Preto clássico"),
            ("Flash",  "255,255,255", 100, "Branco intenso"),
            ("Warm",   "255,180,80",   85, "Laranja quente"),
            ("Custom", None,          None, "Cor personalizada"),
        ]

        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)
        cards_row.setContentsMargins(0, 0, 0, 0)

        custom_thumb_ref = [None]

        for name, color_str, intensity, tip in PRESETS:
            card = QFrame()
            card.setFixedSize(58, 68)
            card.setCursor(Qt.PointingHandCursor)
            card.setToolTip(tip)
            card.setObjectName("presetCard")
            card.setStyleSheet(
                "QFrame#presetCard { background: rgba(28,46,74,0.55); "
                "border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }"
                "QFrame#presetCard:hover { border: 1px solid #6C63FF; }"
            )

            cl = QVBoxLayout(card)
            cl.setContentsMargins(5, 6, 5, 5)
            cl.setSpacing(4)

            thumb = QLabel()
            thumb.setFixedSize(48, 28)
            thumb.setAttribute(Qt.WA_TransparentForMouseEvents)
            thumb.setStyleSheet("border: none; background: transparent;")

            if color_str:
                rgb = [int(x) for x in color_str.split(",")]
                img = QImage(48, 28, QImage.Format_RGB888)
                p = QPainter(img)
                is_fade_in = "fade in" in item.name.lower()
                g = QLinearGradient(0, 0, 48, 0)
                if is_fade_in:
                    g.setColorAt(0.0, QColor(rgb[0], rgb[1], rgb[2]))
                    g.setColorAt(1.0, QColor(20, 20, 30))
                else:
                    g.setColorAt(0.0, QColor(20, 20, 30))
                    g.setColorAt(1.0, QColor(rgb[0], rgb[1], rgb[2]))
                p.fillRect(0, 0, 48, 28, g)
                p.end()
                thumb.setPixmap(QPixmap.fromImage(img))
            else:
                img = QImage(48, 28, QImage.Format_RGB888)
                p = QPainter(img)
                s = 6
                c1, c2 = QColor(50, 50, 60), QColor(80, 80, 95)
                for yy in range(0, 28, s):
                    for xx in range(0, 48, s):
                        p.fillRect(xx, yy, s, s, c1 if ((xx // s + yy // s) % 2 == 0) else c2)
                p.end()
                thumb.setPixmap(QPixmap.fromImage(img))
                custom_thumb_ref[0] = thumb

            cl.addWidget(thumb, alignment=Qt.AlignHCenter)

            name_lbl = QLabel(name)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            name_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold; border: none;")
            cl.addWidget(name_lbl)

            def _on_preset(checked=False, cs=color_str, iv=intensity, it=item):
                if cs is not None:
                    it.params["color"] = cs
                    if iv is not None:
                        it.params["intensity"] = str(iv)
                    self._auto_save()
                    self.load(it, self._project)
                else:
                    self._auto_save()
                    sec = getattr(self, "_appearance_section", None)
                    if sec:
                        self._scroll.ensureWidgetVisible(sec)
                        sec.setStyleSheet(
                            f"QFrame {{ background: {C['card']}; border: 2px solid {C['accent']}; border-radius: 10px; }}"
                        )
                        QTimer.singleShot(800, lambda: sec.setStyleSheet(
                            f"QFrame {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 10px; }}"
                        ))

            card.mousePressEvent = lambda e, fn=_on_preset: fn()
            cards_row.addWidget(card)

        cards_row.addStretch()
        body_l.addLayout(cards_row)
        self._layout.addWidget(section)
        return custom_thumb_ref

    def _build_appearance(self, item, shared, custom_thumb_ref=None):
        section = self._section_frame("▾ Appearance")
        body_l = section.layout()

        ri, gi, bi = self._param_color(item.params, "color",
                                       (255, 255, 255) if "flash" in item.name.lower() else (0, 0, 0))

        h0, s0, v0 = colorsys.rgb_to_hsv(ri/255, gi/255, bi/255)
        state = {"h": h0, "s": s0, "v": v0}

        sv_lbl = QLabel()
        sv_lbl.setFixedSize(_SP_W, _SP_H)
        sv_lbl.setCursor(Qt.CrossCursor)
        sv_lbl.setStyleSheet("border: 1px solid rgba(255,255,255,0.15); border-radius: 6px;")
        sv_lbl.setPixmap(_render_spectrum(h0))
        body_l.addWidget(sv_lbl)

        hue_lbl = QLabel()
        hue_lbl.setFixedSize(_SP_W, _HUE_H)
        hue_lbl.setCursor(Qt.SizeHorCursor)
        hue_lbl.setStyleSheet("border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; margin-top: 4px;")
        hue_lbl.setPixmap(_render_hue_bar())
        body_l.addWidget(hue_lbl)

        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        info_row.setContentsMargins(0, 6, 0, 0)

        swatch = QLabel()
        swatch.setFixedSize(36, 36)
        swatch.setStyleSheet(
            f"background: rgb({ri},{gi},{bi}); border: 2px solid rgba(255,255,255,0.25); border-radius: 6px;"
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
        rgb_lbl.setStyleSheet(f"color: {C['text3']}; font-family: Consolas; font-size: 7pt; border: none;")
        fields_col.addWidget(rgb_lbl)
        info_row.addLayout(fields_col)
        body_l.addLayout(info_row)

        def _apply_color(r, g, b, save=True):
            swatch.setStyleSheet(
                f"background: rgb({r},{g},{b}); border: 2px solid rgba(255,255,255,0.25); border-radius: 6px;"
            )
            rgb_lbl.setText(f"R {r}  G {g}  B {b}")
            hex_edit.blockSignals(True)
            hex_edit.setText(f"#{r:02X}{g:02X}{b:02X}")
            hex_edit.blockSignals(False)
            if custom_thumb_ref and custom_thumb_ref[0] is not None:
                w, h = 48, 28
                img = QImage(w, h, QImage.Format_RGB888)
                p = QPainter(img)
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

        def _sv_pick(event):
            x = max(0, min(_SP_W - 1, int(event.position().x())))
            y = max(0, min(_SP_H - 1, int(event.position().y())))
            state["s"] = x / (_SP_W - 1)
            state["v"] = 1.0 - y / (_SP_H - 1)
            rr, gg, bb = colorsys.hsv_to_rgb(state["h"], state["s"], state["v"])
            _apply_color(int(rr*255), int(gg*255), int(bb*255))

        sv_lbl.mousePressEvent = _sv_pick
        sv_lbl.mouseMoveEvent  = _sv_pick

        def _hue_pick(event):
            x = max(0, min(_SP_W - 1, int(event.position().x())))
            state["h"] = x / (_SP_W - 1)
            sv_lbl.setPixmap(_render_spectrum(state["h"]))
            rr, gg, bb = colorsys.hsv_to_rgb(state["h"], state["s"], state["v"])
            _apply_color(int(rr*255), int(gg*255), int(bb*255))

        hue_lbl.mousePressEvent = _hue_pick
        hue_lbl.mouseMoveEvent  = _hue_pick

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
        self._layout.addWidget(section)
        return section

    def _build_animation(self, item):
        from PySide6.QtGui import QPainter, QPen, QPainterPath, QColor as QC
        from PySide6.QtCore import QPointF

        section = self._section_frame("▾ Animation")
        body_l = section.layout()

        intensity_val = self._param_int(item.params, "intensity", 100)

        int_head = QHBoxLayout()
        int_lbl = QLabel("INTENSIDADE")
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
        int_slider.setFocusPolicy(Qt.StrongFocus)
        int_slider.wheelEvent = lambda e: e.ignore()
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

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.08); border: none;")
        body_l.addWidget(sep)

        curve_lbl = QLabel("CURVA DE TRANSIÇÃO")
        curve_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 8pt; font-weight: bold; border: none;")
        body_l.addWidget(curve_lbl)

        CURVES = [
            ("linear",      "Linear",   "━━━"),
            ("ease-in",     "Ease In",  "╭━━"),
            ("ease-out",    "Ease Out", "━━╮"),
            ("ease-in-out", "Ease I/O", "╭━╮"),
        ]
        current_easing = item.params.get("easing", "linear")
        CURVE_W, CURVE_H = 220, 48

        curve_canvas = QLabel()
        curve_canvas.setFixedSize(CURVE_W, CURVE_H)
        curve_canvas.setStyleSheet(
            "background: rgba(10,16,30,0.70); border: 1px solid rgba(255,255,255,0.10); border-radius: 6px;"
        )

        def _easing_fn(t, mode):
            t = max(0.0, min(1.0, t))
            if mode == "ease-in":     return t * t
            if mode == "ease-out":    return 1.0 - (1.0 - t) ** 2
            if mode == "ease-in-out": return 2*t*t if t < 0.5 else 1 - (-2*t+2)**2/2
            return t

        def _draw_curve(mode):
            from PySide6.QtGui import QPen, QPainterPath, QPixmap
            px = QPixmap(CURVE_W, CURVE_H)
            px.fill(QC(10, 16, 30, 178))
            p = QPainter(px)
            p.setRenderHint(QPainter.Antialiasing)
            pad = 10
            W, H = CURVE_W - pad * 2, CURVE_H - pad * 2
            p.setPen(QPen(QC(255, 255, 255, 18), 1))
            for i in range(1, 4):
                p.drawLine(pad + W * i // 4, pad, pad + W * i // 4, pad + H)
            for i in range(1, 3):
                p.drawLine(pad, pad + H * i // 2, pad + W, pad + H * i // 2)
            path = QPainterPath()
            for i in range(61):
                t = i / 60
                x = pad + t * W
                y = pad + (1.0 - _easing_fn(t, mode)) * H
                path.moveTo(QPointF(x, y)) if i == 0 else path.lineTo(QPointF(x, y))
            pen = QPen(QC(C["primary"]), 2)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawPath(path)
            p.setBrush(QC(C["accent"]))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(pad + W, pad + (1.0 - _easing_fn(1.0, mode)) * H), 4, 4)
            p.end()
            curve_canvas.setPixmap(px)

        _draw_curve(current_easing)
        body_l.addWidget(curve_canvas)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        ease_btns = []

        def _ease_style(active):
            if active:
                return (
                    f"QPushButton {{ background: {C['secondary']}; color: {C['text']}; font-size: 8pt; font-weight: bold; "
                    f"border: 2px solid {C['accent']}; border-radius: 6px; padding: 2px 6px; }}"
                )
            return (
                f"QPushButton {{ background: rgba(28,46,74,0.55); color: {C['text3']}; font-size: 8pt; font-weight: bold; "
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
        self._layout.addWidget(section)

    def _build_preview(self, item):
        section = self._section_frame("▾ Preview")
        body_l = section.layout()

        PW, PH = 220, 52
        is_fade_in = "fade in" in item.name.lower()

        if is_fade_in:
            desc = "escuro/colorido opaco  →  transparente"
        elif "flash" in item.name.lower():
            desc = "flash  →  transparente"
        else:
            desc = "transparente  →  escuro/colorido opaco"

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {C['text3']}; font-size: 7pt; border: none;")
        body_l.addWidget(desc_lbl)

        canvas = QLabel()
        canvas.setFixedSize(PW, PH)
        canvas.setStyleSheet("border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;")
        body_l.addWidget(canvas)

        prog_bar = QLabel()
        prog_bar.setFixedSize(PW, 3)
        prog_bar.setStyleSheet("background: rgba(255,255,255,0.08); border-radius: 1px; border: none;")
        body_l.addWidget(prog_bar)

        play_btn = QPushButton("▶  Play")
        play_btn.setFixedHeight(26)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(28,46,74,0.55); color: {C['text2']}; font-size: 8pt; font-weight: bold; "
            f"border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; }}"
            f"QPushButton:hover {{ color: {C['text']}; border-color: {C['secondary']}; }}"
        )
        body_l.addWidget(play_btn)

        anim = {"t": 0.0, "running": False}
        timer = QTimer()
        timer.setInterval(30)

        def _get_color():
            try:
                return [int(x) for x in item.params.get("color", "0,0,0").split(",")]
            except Exception:
                return [0, 0, 0]

        def _easing(t):
            mode = item.params.get("easing", "linear")
            t = max(0.0, min(1.0, t))
            if mode == "ease-in":     return t * t
            if mode == "ease-out":    return 1.0 - (1.0 - t) ** 2
            if mode == "ease-in-out": return 2*t*t if t < 0.5 else 1 - (-2*t+2)**2/2
            return t

        def _draw_frame(t):
            rgb   = _get_color()
            op    = float(item.params.get("color_opacity", 100)) / 100.0
            inten = float(item.params.get("intensity", 100)) / 100.0
            et    = _easing(t)
            alpha = op * inten * (1.0 - et) if is_fade_in else op * inten * et

            img = QImage(PW, PH, QImage.Format_RGB888)
            p = QPainter(img)
            bg = QLinearGradient(0, 0, PW, PH)
            bg.setColorAt(0.0, QColor(20, 30, 55))
            bg.setColorAt(1.0, QColor(10, 16, 32))
            p.fillRect(0, 0, PW, PH, bg)
            p.setPen(QColor(255, 255, 255, 30))
            p.drawText(PW // 2 - 18, PH // 2 + 5, "CENA")
            p.fillRect(0, 0, PW, PH, QColor(rgb[0], rgb[1], rgb[2], int(alpha * 255)))
            p.setPen(QColor(255, 255, 255, 80))
            p.drawLine(int(t * PW), 0, int(t * PW), PH)
            p.end()
            canvas.setPixmap(QPixmap.fromImage(img))
            prog_bar.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 {C['primary']}, stop:{t:.3f} {C['accent']}, "
                f"stop:{min(t+0.001,1.0):.3f} rgba(255,255,255,0.08), stop:1 rgba(255,255,255,0.08));"
                f"border-radius: 1px; border: none;"
            )

        _draw_frame(0.0)

        def _tick():
            anim["t"] += 0.016
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
        self._layout.addWidget(section)


