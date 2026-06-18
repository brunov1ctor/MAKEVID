"""Inpaint Editor - Modo de edicao por regiao no display (Angelo-style).

Quando ativado, mostra canvas overlay sobre o preview com:
- Ferramenta retangulo ou pincel livre
- Campo de prompt para a regiao
- Botao regenerar
- Preview do resultado antes de aplicar
"""

import tkinter as tk
import customtkinter as ctk
import numpy as np
from PIL import Image, ImageDraw, ImageTk
from makevid.ui.theme import C


class InpaintEditor:
    """Editor de inpainting inline no display."""

    def __init__(self, preview_panel):
        self.pp = preview_panel
        self.app = preview_panel.app
        self._active = False
        self._canvas = None
        self._toolbar = None
        self._mask_img = None
        self._frame_rgb = None
        self._tool = "rect"  # rect | brush
        self._brush_size = 20
        self._drawing = False
        self._rect_start = None
        self._img_offset = (0, 0)
        self._img_size = (0, 0)

    @property
    def is_active(self):
        return self._active

    def enter(self, frame_rgb: np.ndarray):
        """Entra no modo inpainting com o frame atual.

        Args:
            frame_rgb: Frame RGB numpy array (H, W, 3)
        """
        if self._active:
            return
        self._active = True
        self._frame_rgb = frame_rgb.copy()

        # Esconder play button e properties
        self.pp._hide_play_button()
        self.pp.properties.close()

        # Calcular dimensoes da imagem no display
        img = Image.fromarray(frame_rgb)
        img_fitted, w, h = self.pp._fit_image(img)
        self._img_size = (w, h)

        # Canvas overlay sobre o preview_frame
        pf = self.pp.preview_frame
        self._canvas = tk.Canvas(pf, bg="#050508", highlightthickness=0, cursor="crosshair")
        self._canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Mostrar imagem no canvas
        self._photo = ImageTk.PhotoImage(img_fitted)
        fw = pf.winfo_width()
        fh = pf.winfo_height()
        cx, cy = fw // 2, fh // 2
        self._img_offset = (cx - w // 2, cy - h // 2)
        self._canvas.create_image(cx, cy, image=self._photo, tags="bg_img")

        # Mascara transparente (mesmo tamanho da imagem fitted)
        self._mask_img = Image.new("L", (w, h), 0)
        self._mask_draw = ImageDraw.Draw(self._mask_img)

        # Overlay vermelho semi-transparente para mostrar mascara
        self._overlay_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self._overlay_draw = ImageDraw.Draw(self._overlay_img)

        # Binds de desenho
        self._canvas.bind("<Button-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Button-3>", self._on_clear_mask)

        # Toolbar no topo do canvas
        self._build_toolbar()

        # Info
        self.pp.clip_info.configure(
            text="✏️ MODO EDIÇÃO | Desenhe a região para regenerar | Click direito = limpar")

    def exit(self):
        """Sai do modo inpainting."""
        if not self._active:
            return
        self._active = False
        if self._canvas:
            self._canvas.destroy()
            self._canvas = None
        if self._toolbar:
            self._toolbar.destroy()
            self._toolbar = None
        self._mask_img = None
        self._frame_rgb = None
        self._photo = None
        self._overlay_photo = None
        # Restaurar preview
        self.pp.show_timeline_preview()

    def _build_toolbar(self):
        """Barra de ferramentas no topo do display."""
        self._toolbar = ctk.CTkFrame(self.pp.preview_frame, fg_color=C["card"],
                                      corner_radius=6, border_color=C["cyan"], border_width=1,
                                      height=36)
        self._toolbar.place(relx=0.5, rely=0, anchor="n", y=4)

        # Ferramentas
        self._btn_rect = ctk.CTkButton(
            self._toolbar, text="▭ Retângulo", width=90, height=26,
            font=("Segoe UI", 9, "bold"), fg_color=C["cyan"], text_color="#0a0a0f",
            hover_color="#00ffee", command=lambda: self._set_tool("rect"))
        self._btn_rect.pack(side="left", padx=(6, 2), pady=4)

        self._btn_brush = ctk.CTkButton(
            self._toolbar, text="🖌 Pincel", width=70, height=26,
            font=("Segoe UI", 9, "bold"), fg_color=C["card"],
            border_color=C["cyan"], border_width=1,
            text_color=C["cyan"], hover_color="#0a2a2a",
            command=lambda: self._set_tool("brush"))
        self._btn_brush.pack(side="left", padx=2, pady=4)

        # Brush size
        self._size_label = ctk.CTkLabel(self._toolbar, text="20px",
                                         font=("Consolas", 8), text_color=C["text3"])
        self._size_label.pack(side="left", padx=(8, 2), pady=4)
        self._size_slider = ctk.CTkSlider(
            self._toolbar, from_=5, to=80, number_of_steps=75,
            width=80, height=14, fg_color=C["border"],
            progress_color=C["cyan"], button_color=C["cyan"],
            command=self._on_size_change)
        self._size_slider.set(20)
        self._size_slider.pack(side="left", padx=2, pady=4)

        # Separador
        ctk.CTkFrame(self._toolbar, width=1, fg_color=C["border"]).pack(
            side="left", fill="y", padx=6, pady=6)

        # Prompt
        self._prompt_var = ctk.StringVar(value="")
        self._prompt_entry = ctk.CTkEntry(
            self._toolbar, textvariable=self._prompt_var, width=180, height=26,
            fg_color=C["input"], border_color=C["cyan"], border_width=1,
            text_color=C["cyan"], font=("Consolas", 9),
            placeholder_text="Prompt da região (opcional)")
        self._prompt_entry.pack(side="left", padx=4, pady=4)

        # Botoes de acao
        ctk.CTkButton(
            self._toolbar, text="✓ GERAR", width=70, height=26,
            font=("Segoe UI", 9, "bold"), fg_color=C["gold"],
            text_color="#0a0a0f", hover_color="#ffd700",
            command=self._do_inpaint).pack(side="left", padx=2, pady=4)

        ctk.CTkButton(
            self._toolbar, text="✕", width=28, height=26,
            font=("Segoe UI", 10, "bold"), fg_color=C["card"],
            text_color="#ff4444", hover_color="#2a0808",
            command=self.exit).pack(side="left", padx=(2, 6), pady=4)

    def _set_tool(self, tool):
        self._tool = tool
        if tool == "rect":
            self._btn_rect.configure(fg_color=C["cyan"], text_color="#0a0a0f")
            self._btn_brush.configure(fg_color=C["card"], text_color=C["cyan"])
            self._canvas.configure(cursor="crosshair")
        else:
            self._btn_rect.configure(fg_color=C["card"], text_color=C["cyan"])
            self._btn_brush.configure(fg_color=C["cyan"], text_color="#0a0a0f")
            self._canvas.configure(cursor="circle")

    def _on_size_change(self, val):
        self._brush_size = int(val)
        self._size_label.configure(text=f"{self._brush_size}px")

    def _to_img_coords(self, event_x, event_y):
        """Converte coords do canvas para coords da imagem."""
        ox, oy = self._img_offset
        w, h = self._img_size
        x = event_x - ox
        y = event_y - oy
        x = max(0, min(w - 1, x))
        y = max(0, min(h - 1, y))
        return x, y

    def _on_press(self, event):
        self._drawing = True
        x, y = self._to_img_coords(event.x, event.y)
        if self._tool == "rect":
            self._rect_start = (x, y)
        else:
            r = self._brush_size // 2
            self._mask_draw.ellipse([x - r, y - r, x + r, y + r], fill=255)
            self._overlay_draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 50, 50, 100))
            self._update_overlay()

    def _on_drag(self, event):
        if not self._drawing:
            return
        x, y = self._to_img_coords(event.x, event.y)
        if self._tool == "brush":
            r = self._brush_size // 2
            self._mask_draw.ellipse([x - r, y - r, x + r, y + r], fill=255)
            self._overlay_draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 50, 50, 100))
            self._update_overlay()
        elif self._tool == "rect" and self._rect_start:
            # Preview do retangulo
            self._canvas.delete("rect_preview")
            ox, oy = self._img_offset
            sx, sy = self._rect_start
            self._canvas.create_rectangle(
                sx + ox, sy + oy, event.x, event.y,
                outline="#00ffee", width=2, dash=(4, 4), tags="rect_preview")

    def _on_release(self, event):
        if not self._drawing:
            return
        self._drawing = False
        if self._tool == "rect" and self._rect_start:
            x, y = self._to_img_coords(event.x, event.y)
            sx, sy = self._rect_start
            x1, y1 = min(sx, x), min(sy, y)
            x2, y2 = max(sx, x), max(sy, y)
            if x2 - x1 > 5 and y2 - y1 > 5:
                self._mask_draw.rectangle([x1, y1, x2, y2], fill=255)
                self._overlay_draw.rectangle([x1, y1, x2, y2], fill=(255, 50, 50, 100))
            self._canvas.delete("rect_preview")
            self._rect_start = None
            self._update_overlay()

    def _on_clear_mask(self, event):
        """Click direito limpa mascara."""
        w, h = self._img_size
        self._mask_img = Image.new("L", (w, h), 0)
        self._mask_draw = ImageDraw.Draw(self._mask_img)
        self._overlay_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self._overlay_draw = ImageDraw.Draw(self._overlay_img)
        self._canvas.delete("overlay")
        self._canvas.delete("rect_preview")

    def _update_overlay(self):
        """Atualiza overlay vermelho que mostra a mascara."""
        self._canvas.delete("overlay")
        self._overlay_photo = ImageTk.PhotoImage(self._overlay_img)
        ox, oy = self._img_offset
        w, h = self._img_size
        self._canvas.create_image(ox + w // 2, oy + h // 2,
                                   image=self._overlay_photo, tags="overlay")

    def _do_inpaint(self):
        """Executa inpainting na regiao selecionada."""
        # Verificar se tem mascara
        mask_arr = np.array(self._mask_img)
        if mask_arr.max() == 0:
            self.pp.clip_info.configure(text="⚠️ Desenhe uma região primeiro!")
            return

        prompt = self._prompt_var.get().strip() or "high quality, detailed, sharp"

        # Converter mascara para resolucao original do frame
        orig_h, orig_w = self._frame_rgb.shape[:2]
        mask_full = np.array(
            Image.fromarray(mask_arr).resize((orig_w, orig_h), Image.NEAREST))

        # Feedback visual
        self.pp.clip_info.configure(text="🔄 Gerando região... aguarde")
        self._canvas.configure(cursor="watch")

        from makevid.services.inpainting_service import InpaintingService
        svc = InpaintingService()

        def on_progress(msg):
            self.app.after(0, lambda: self.pp.clip_info.configure(text=f"🔄 {msg}"))

        def on_done(result_frame):
            def _apply():
                self._frame_rgb = result_frame
                # Atualizar display com resultado
                img = Image.fromarray(result_frame)
                img_fitted, w, h = self.pp._fit_image(img)
                self._photo = ImageTk.PhotoImage(img_fitted)
                self._canvas.delete("bg_img")
                fw = self.pp.preview_frame.winfo_width()
                fh = self.pp.preview_frame.winfo_height()
                self._canvas.create_image(fw // 2, fh // 2, image=self._photo, tags="bg_img")
                self._canvas.tag_lower("bg_img")
                # Limpar mascara
                self._on_clear_mask(None)
                self._canvas.configure(cursor="crosshair")
                self.pp.clip_info.configure(text="✅ Região regenerada! Desenhe outra ou feche (✕)")
            self.app.after(0, _apply)

        def on_error(err):
            def _show():
                self._canvas.configure(cursor="crosshair")
                self.pp.clip_info.configure(text=f"❌ Erro: {err[:50]}")
            self.app.after(0, _show)

        svc.inpaint_region(
            frame=self._frame_rgb,
            mask=mask_full,
            prompt=prompt,
            project_id=self.app.project.id,
            on_progress=on_progress,
            on_done=on_done,
            on_error=on_error,
        )

    def get_current_frame(self) -> np.ndarray:
        """Retorna o frame atual (possivelmente editado)."""
        return self._frame_rgb
