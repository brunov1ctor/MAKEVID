"""FX Editor - Painel de edicao de efeitos visuais."""

import math
import customtkinter as ctk
from makevid.ui.theme import C


class FxEditor:
    """Constroi e gerencia painel de edicao de FX."""

    def __init__(self, fx_panel):
        self.fx_panel = fx_panel

    def build(self, frame, item):
        """Constroi painel de edicao de efeito visual profissional."""
        from makevid.config import PROJECTS_DIR
        p = frame
        self._fx_item = item
        self._fx_params = {}

        header = ctk.CTkFrame(p, fg_color="transparent", height=32)
        header.pack(fill="x", padx=10, pady=(10, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="FX EDITOR", font=("Segoe UI", 13, "bold"),
                     text_color=C["purple"]).pack(side="left")
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=self.fx_panel.hide).pack(side="right")

        ctk.CTkFrame(p, height=2, fg_color=C["purple"]).pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkLabel(p, text=item.name, font=("Segoe UI", 11, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=12, pady=(0, 2))
        ctk.CTkLabel(p, text=f"{item.duration:.1f}s | Inicio: {item.start_time:.1f}s",
                     font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w", padx=12, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                        scrollbar_button_color=C["purple"],
                                        scrollbar_button_hover_color="#bb77ff")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        name_lower = item.name.lower()

        # --- INTENSIDADE (todos) ---
        from makevid.ui.menus import _ToolTip
        int_lbl = ctk.CTkLabel(scroll, text="INTENSIDADE", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"])
        int_lbl.pack(anchor="w", padx=4, pady=(4, 0))
        _ToolTip(int_lbl, "Forca do efeito de 0% a 100%.\n0% = sem efeito, 100% = efeito maximo.")
        saved_intensity = int(item.params.get("intensity", 100))
        self._fx_params["intensity"] = self._slider(
            scroll, "", 0, 100, saved_intensity, "%", C["purple"])
        _int_slider = self._fx_params["intensity"]
        _int_lbl = _int_slider.master.winfo_children()[-1]

        def _on_intensity_change(val, it=item, lb=_int_lbl):
            lb.configure(text=f"{int(float(val))}%")
            it.params["intensity"] = str(int(float(val)))
            from makevid.config import PROJECTS_DIR
            self.fx_panel.timeline.project.save(PROJECTS_DIR)
        _int_slider.configure(command=_on_intensity_change)

        # --- EASING ---
        easing_lbl = ctk.CTkLabel(scroll, text="TRANSICAO", font=("Segoe UI", 9, "bold"),
                     text_color=C["text2"])
        easing_lbl.pack(anchor="w", padx=4, pady=(4, 2))
        easing_frame = ctk.CTkFrame(scroll, fg_color=C["card"], corner_radius=4)
        easing_frame.pack(fill="x", padx=4, pady=(0, 8))
        self._fx_params["easing"] = ctk.StringVar(value="linear")
        for ease_name, ease_val in [("Constante", "linear"), ("Suave entrada", "ease-in"),
                                     ("Suave saida", "ease-out"), ("Suave ambos", "ease-in-out")]:
            ctk.CTkRadioButton(easing_frame, text=ease_name, variable=self._fx_params["easing"],
                               value=ease_val, fg_color=C["purple"], text_color=C["text"],
                               font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=2)

        # Parametros especificos por efeito
        self._build_specific_params(scroll, item, name_lower)

        # Botao preview
        ctk.CTkButton(scroll, text="\u25b6 PREVIEW", height=28, font=("Segoe UI", 9, "bold"),
                      fg_color=C["card"], border_color=C["purple"], border_width=1,
                      text_color=C["purple"], hover_color="#1a0a2a",
                      command=lambda: self._preview_fx(item)).pack(fill="x", padx=4, pady=(8, 4))

    def _build_specific_params(self, scroll, item, name_lower):
        """Constroi parametros especificos por tipo de FX."""
        from makevid.core.fx_processor import set_fx_color

        if "flash" in name_lower:
            ctk.CTkLabel(scroll, text="COR DO FLASH", font=("Segoe UI", 9, "bold"),
                         text_color=C["text2"]).pack(anchor="w", padx=4, pady=(4, 2))
            saved_color = item.params.get("color", "255,255,255")
            rgb = [int(x) for x in saved_color.split(",")]
            set_fx_color("flash", rgb)

            def _on_flash_color(c):
                set_fx_color("flash", c)
                item.params["color"] = f"{c[0]},{c[1]},{c[2]}"
                from makevid.config import PROJECTS_DIR
                self.fx_panel.timeline.project.save(PROJECTS_DIR)
            self._build_color_picker(scroll, rgb, _on_flash_color)

        elif "glitch" in name_lower:
            self._slider(scroll, "FREQUENCIA GLITCH", 1, 30, 10, "", "#aa44ff", steps=29)
            self._slider(scroll, "RGB SHIFT", 0, 20, 5, "px", "#ff44aa", steps=20)

        elif "blur" in name_lower:
            self._slider(scroll, "RAIO DO BLUR", 1, 30, 5, "px", "#4488ff", steps=29)

        elif "shake" in name_lower:
            self._slider(scroll, "AMPLITUDE", 1, 30, 8, "px", "#ff8844", steps=29)
            self._slider(scroll, "VELOCIDADE", 1, 20, 10, "x", "#ffaa44", steps=19)

        elif "color shift" in name_lower:
            self._slider(scroll, "RED SHIFT", -20, 20, 0, "px", "#ff4444", steps=40)
            self._slider(scroll, "GREEN SHIFT", -20, 20, 0, "px", "#44ff44", steps=40)
            self._slider(scroll, "BLUE SHIFT", -20, 20, 0, "px", "#4444ff", steps=40)

        elif "vignette" in name_lower:
            self._slider(scroll, "RAIO", 20, 100, 60, "%", "#885533", steps=80)
            self._slider(scroll, "SUAVIDADE", 10, 100, 50, "%", "#aa7744", steps=90)

        elif "pixelate" in name_lower:
            self._slider(scroll, "TAMANHO PIXEL", 2, 32, 8, "px", "#44ccaa", steps=30)

        elif "film grain" in name_lower:
            self._slider(scroll, "QUANTIDADE", 5, 80, 30, "", "#aa8855", steps=75)

        elif "letterbox" in name_lower:
            self._slider(scroll, "TAMANHO BARRAS", 5, 25, 12, "%", "#666666", steps=20)

        elif "sepia" in name_lower:
            self._slider(scroll, "FORCA", 0, 100, 80, "%", "#cc9944", steps=100)

        elif "wipe" in name_lower:
            self._slider(scroll, "SUAVIDADE BORDA", 0, 50, 0, "px", "#8855bb", steps=50)

        elif "fade" in name_lower:
            ctk.CTkLabel(scroll, text="COR BASE", font=("Segoe UI", 9, "bold"),
                         text_color=C["text2"]).pack(anchor="w", padx=4, pady=(4, 2))
            saved_color = item.params.get("color", "0,0,0")
            rgb = [int(x) for x in saved_color.split(",")]
            set_fx_color("fade", rgb)

            def _on_fade_color(c):
                set_fx_color("fade", c)
                item.params["color"] = f"{c[0]},{c[1]},{c[2]}"
                from makevid.config import PROJECTS_DIR
                self.fx_panel.timeline.project.save(PROJECTS_DIR)
            self._build_color_picker(scroll, rgb, _on_fade_color)

    def _preview_fx(self, item):
        tl = self.fx_panel.timeline
        tl.playhead_pos = item.start_time
        tl.draw()
        player = tl.app.preview_panel.player
        tl.app.preview_panel._on_play_click(lambda: self.fx_panel._start_player_at_time(player, item.start_time))

    def _slider(self, parent, label, from_, to, default, unit, color, steps=100, fmt_fn=None):
        """Cria slider padrao com label e valor."""
        if label:
            ctk.CTkLabel(parent, text=label, font=("Segoe UI", 9, "bold"),
                         text_color=C["text2"]).pack(anchor="w", padx=4, pady=(4, 2))
        frame = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=4)
        frame.pack(fill="x", padx=4, pady=(0, 8))
        slider = ctk.CTkSlider(frame, from_=from_, to=to, number_of_steps=steps,
                                fg_color=C["border"], progress_color=color,
                                button_color=color, button_hover_color=color)
        slider.set(default)
        slider.pack(fill="x", padx=8, pady=(8, 2))
        if fmt_fn:
            lbl = ctk.CTkLabel(frame, text=fmt_fn(default), font=("Consolas", 9), text_color=C["text3"])
            slider.configure(command=lambda v: lbl.configure(text=fmt_fn(v)))
        else:
            lbl = ctk.CTkLabel(frame, text=f"{int(default)}{unit}", font=("Consolas", 9), text_color=C["text3"])
            slider.configure(command=lambda v: lbl.configure(text=f"{int(v)}{unit}"))
        lbl.pack(padx=8, pady=(0, 6))
        return slider

    def _build_color_picker(self, parent, color_list, on_change=None):
        """Cria color picker visual com espectro de cores."""
        import tkinter as tk
        import colorsys
        from PIL import Image as PILImage, ImageTk

        frame = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=6,
                             border_color=C["border"], border_width=1)
        frame.pack(fill="x", padx=4, pady=(0, 8))

        picker_w, picker_h = 260, 110
        canvas = tk.Canvas(frame, width=picker_w, height=picker_h,
                           bg="#000000", highlightthickness=0, cursor="crosshair")
        canvas.pack(padx=8, pady=(8, 0))

        state = {"sat": 1.0, "photo": None}

        def render_spectrum(sat=1.0):
            img = PILImage.new("RGB", (picker_w, picker_h))
            pixels = img.load()
            for x in range(picker_w):
                hue = x / picker_w
                for y in range(picker_h):
                    val = 1.0 - (y / picker_h)
                    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
                    pixels[x, y] = (int(r * 255), int(g * 255), int(b * 255))
            photo = ImageTk.PhotoImage(img)
            state["photo"] = photo
            canvas.delete("spectrum")
            canvas.create_image(0, 0, anchor="nw", image=photo, tags="spectrum")
            canvas.tag_raise("marker")

        render_spectrum(1.0)

        canvas.create_oval(-5, -5, 5, 5, outline="#ffffff", width=2, tags="marker")

        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=8, pady=(6, 4))

        color_swatch = tk.Canvas(info_frame, width=36, height=36,
                                  bg=f"#{color_list[0]:02x}{color_list[1]:02x}{color_list[2]:02x}",
                                  highlightthickness=1, highlightbackground="#444444")
        color_swatch.pack(side="left")

        info_right = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_right.pack(side="left", padx=(8, 0))
        color_label = ctk.CTkLabel(info_right, text=f"R:{color_list[0]}  G:{color_list[1]}  B:{color_list[2]}",
                                    font=("Consolas", 9, "bold"), text_color=C["text"])
        color_label.pack(anchor="w")
        hex_label = ctk.CTkLabel(info_right, text=f"#{color_list[0]:02x}{color_list[1]:02x}{color_list[2]:02x}",
                                  font=("Consolas", 10, "bold"), text_color=C["cyan"])
        hex_label.pack(anchor="w")

        sat_frame = ctk.CTkFrame(frame, fg_color="transparent")
        sat_frame.pack(fill="x", padx=8, pady=(2, 6))
        ctk.CTkLabel(sat_frame, text="SAT", font=("Consolas", 8, "bold"),
                     text_color=C["text3"]).pack(side="left")
        sat_slider = ctk.CTkSlider(sat_frame, from_=0, to=100, number_of_steps=100,
                                    fg_color=C["border"], progress_color=C["purple"],
                                    button_color=C["purple"], button_hover_color="#bb77ff")
        sat_slider.set(100)
        sat_slider.pack(side="left", fill="x", expand=True, padx=4)
        sat_val_lbl = ctk.CTkLabel(sat_frame, text="100%", font=("Consolas", 8),
                                    text_color=C["text3"], width=35)
        sat_val_lbl.pack(side="left")

        def update_color(x, y):
            x = max(0, min(picker_w - 1, x))
            y = max(0, min(picker_h - 1, y))
            hue = x / picker_w
            val = 1.0 - (y / picker_h)
            sat = state["sat"]
            r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
            color_list[0] = int(r * 255)
            color_list[1] = int(g * 255)
            color_list[2] = int(b * 255)
            hex_c = f"#{color_list[0]:02x}{color_list[1]:02x}{color_list[2]:02x}"
            color_swatch.configure(bg=hex_c)
            color_label.configure(text=f"R:{color_list[0]}  G:{color_list[1]}  B:{color_list[2]}")
            hex_label.configure(text=hex_c)
            canvas.delete("marker")
            canvas.create_oval(x - 6, y - 6, x + 6, y + 6, outline="#ffffff", width=2, tags="marker")
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, outline="#000000", width=1, tags="marker")
            if on_change:
                on_change(color_list)

        canvas.bind("<Button-1>", lambda e: update_color(e.x, e.y))
        canvas.bind("<B1-Motion>", lambda e: update_color(e.x, e.y))
        sat_slider.configure(command=lambda val: [
            state.update({"sat": val / 100.0}),
            sat_val_lbl.configure(text=f"{int(val)}%"),
            render_spectrum(val / 100.0)
        ])

        return frame
