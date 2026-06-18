"""MAKEVID - App principal. Orquestra UI components e services."""

import customtkinter as ctk
from tkinter import messagebox
import time
import os
from pathlib import Path

from makevid.ui.theme import C
from makevid.ui.panel_generator import GeneratorPanel
from makevid.ui.panel_preview import PreviewPanel
from makevid.ui.timeline import TimelineWidget
from makevid.services.generation_service import GenerationService
from makevid.config import OUTPUTS_DIR, PROJECTS_DIR
from makevid.core.logger import log_error

import logging
_logger = logging.getLogger("ui")


class MakeVidApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Inicializar tkdnd se disponivel (sem mixin)
        try:
            from tkinterdnd2 import TkinterDnD
            self.TkdndVersion = TkinterDnD._require(self)
            self._has_dnd = True
        except Exception:
            self._has_dnd = False

        self.title("MAKEVID")
        self.geometry("1450x850")
        self.minsize(900, 600)
        self.configure(fg_color=C["bg"])
        ctk.set_appearance_mode("dark")

        # State
        self.project = None
        self.engine_var = ctk.StringVar(value="Local (CPU)")
        self._gen_service = GenerationService()

        self._load_project()
        self._build_ui()

    def report_callback_exception(self, exc_type, exc_value, exc_tb):
        """Captura exceções de callbacks tkinter e envia ao logger."""
        import traceback
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        _logger.error(f"Tkinter callback error:\n{tb_str}")
        log_error("tkinter", str(exc_value))

        # Atalho: spacebar no canvas da timeline = play/pause
        # (nao usar bind global pois bloqueia digitacao em campos de texto)

    def _toggle_playback(self, event=None):
        """Spacebar global: play/pause da timeline."""
        # Ignorar se foco esta em campo de texto
        focused = self.focus_get()
        if focused:
            import customtkinter as ctk
            widget = focused
            for _ in range(8):
                if widget is None or widget == self:
                    break
                if isinstance(widget, (ctk.CTkTextbox, ctk.CTkEntry)):
                    return
                widget = getattr(widget, 'master', None)
        player = self.preview_panel.player
        if player.is_playing:
            player.pause()
        elif player.is_paused:
            self.preview_panel._on_resume_click()
        else:
            self.preview_panel._on_play_click(lambda: player.play())

    def _load_project(self):
        from makevid.core.project import Project
        files = list(PROJECTS_DIR.glob("*.json"))
        if files:
            try:
                self.project = Project.load(files[0])
            except Exception:
                files[0].unlink(missing_ok=True)
                self.project = Project.create("meu_projeto")
                self.project.save(PROJECTS_DIR)
        else:
            self.project = Project.create("meu_projeto")
            self.project.save(PROJECTS_DIR)

    # ============================================================
    # UI BUILD
    # ============================================================

    def _build_ui(self):
        self._build_topbar()

        # PanedWindow vertical: main (cima) + timeline (baixo)
        import tkinter as tk
        self._paned = tk.PanedWindow(self, orient="vertical", sashwidth=8,
                                      bg="#0a0a0f", bd=0, sashrelief="flat")
        self._paned.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Main (gerador + preview)
        self._main = ctk.CTkFrame(self._paned, fg_color="transparent")
        self._paned.add(self._main, minsize=300, stretch="always")

        # Timeline
        self.timeline = TimelineWidget(self._paned, self)

        # Highlight do sash no hover
        def _sash_enter(e):
            self._paned.configure(bg="#c89b3c")
        def _sash_leave(e):
            self._paned.configure(bg="#0a0a0f")
        self._paned.bind("<Enter>", _sash_enter)
        self._paned.bind("<Leave>", _sash_leave)

        # PanedWindow horizontal: painel esquerdo + preview direito
        import tkinter as tk
        self._h_paned = tk.PanedWindow(self._main, orient="horizontal", sashwidth=6,
                                        bg="#0a0a0f", bd=0, sashrelief="flat")
        self._h_paned.pack(fill="both", expand=True)

        # Frame esquerdo (conteiner do generator_panel e fx_panel)
        self._left_pane = ctk.CTkFrame(self._h_paned, fg_color="transparent")
        self._h_paned.add(self._left_pane, minsize=250, width=300, stretch="never")

        # Frame direito (preview)
        self._right_pane = ctk.CTkFrame(self._h_paned, fg_color="transparent")
        self._h_paned.add(self._right_pane, minsize=400, stretch="always")

        # Highlight do sash horizontal no hover
        def _hsash_enter(e):
            self._h_paned.configure(bg=C["gold"])
        def _hsash_leave(e):
            self._h_paned.configure(bg="#0a0a0f")
        self._h_paned.bind("<Enter>", _hsash_enter)
        self._h_paned.bind("<Leave>", _hsash_leave)

        self.generator_panel = GeneratorPanel(self._left_pane, self)
        self.preview_panel = PreviewPanel(self._right_pane, self)

        # Mostrar preview da timeline ao iniciar (play button)
        self.after(200, self.preview_panel.show_timeline_preview)

    def _build_topbar(self):
        from makevid.ui.menus import build_topbar
        build_topbar(self)

    # ============================================================
    # ACTIONS (chamadas pelos components)
    # ============================================================

    def on_clip_selected(self, clip):
        """Chamado pela timeline quando clip e selecionado."""
        self.generator_panel.set_clip_data(clip)
        self.preview_panel.show_clip(clip, len(self.project.clips))

    def request_generation(self, prompt, duration, steps, guidance, seed, width, height, negative, ref_images, motion_ref_path=None, motion_mode="pose"):
        """Chamado pelo generator panel para iniciar geracao. Sempre cria novo clip na frente."""
        from makevid.core.logger import log_generation, log_clip_action

        # Sempre criar novo clip no final da timeline
        clip = self.project.add_clip(prompt=prompt)
        clip.duration = duration
        clip.status = "generating"

        log_clip_action("criar", clip.id, f"prompt='{prompt[:40]}'")
        log_generation(prompt, self.engine_var.get(), duration, "generating")

        # Mover playhead para o inicio do novo clip
        total_before = sum(c.duration for c in self.project.clips if c.position < clip.position)
        self.timeline.playhead_pos = total_before

        # Nao manter selecionado - campo deve ficar limpo durante geracao
        self.timeline.selected_clip_id = None

        self.project.save(PROJECTS_DIR)
        self.timeline.draw()

        def on_progress(msg):
            self.after(0, lambda: self.generator_panel.on_gen_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path
            clip.duration = dur
            clip.seed = seed_used
            clip.status = "done"
            self.project.save(PROJECTS_DIR)

            def _finalize():
                self.timeline.selected_clip_id = None
                self.timeline.invalidate_thumbnail(clip.id)
                self.timeline.draw()
                self.preview_panel.show_generated(clip)
                self.generator_panel.on_gen_done(clip)
                self.generator_panel._reset_fields()
                total_after = sum(c.duration for c in self.project.clips if c.position <= clip.position)
                self.timeline.playhead_pos = total_after
                self.timeline.draw()

            self.after(0, _finalize)

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
            self.after(0, lambda: self.generator_panel.on_gen_error(err))
            self.after(0, lambda: self.timeline.draw())

        self._gen_service.generate_clip(
            project_id=self.project.id,
            clip_id=clip.id,
            prompt=prompt,
            engine=self.engine_var.get(),
            duration=duration,
            steps=steps,
            guidance=guidance,
            seed=seed,
            width=width,
            height=height,
            fps=self.project.output_fps,
            negative_prompt=negative,
            ref_images=ref_images,
            motion_ref_path=motion_ref_path,
            motion_mode=motion_mode,
            on_progress=on_progress,
            on_done=on_done,
            on_error=on_error,
        )

        # Salvar referencia de imagem no clip
        if ref_images:
            clip.image_ref_path = ref_images[0]

    def duplicate_clip(self, clip):
        from makevid.core.logger import log_clip_action
        new = self.project.add_clip(prompt=clip.prompt, position=clip.position + 1)
        new.duration = clip.duration
        new.video_path = clip.video_path
        new.seed = clip.seed
        new.status = clip.status
        self.project.save(PROJECTS_DIR)
        self.timeline.selected_clip_id = new.id
        self.timeline.invalidate_thumbnail(new.id)
        self.timeline.draw()
        self.preview_panel.show_clip(new, len(self.project.clips))
        log_clip_action("duplicar", new.id, f"de clip={clip.id}")

    def regenerate_clip(self, clip):
        """Regera o clip. Se [IMG], gera nova imagem via HF API. Se video, regera video."""
        from makevid.core.logger import log_clip_action
        log_clip_action("regerar", clip.id, f"prompt='{clip.prompt[:40]}'")

        # Se eh clip de imagem, regenerar via HF API
        if clip.prompt.startswith("[IMG]"):
            self._regenerate_image_clip(clip)
            return

        clip.status = "generating"
        self.project.save(PROJECTS_DIR)
        self.timeline.draw()

        def on_progress(msg):
            self.after(0, lambda: self.generator_panel.on_gen_progress(msg))

        def on_done(path, dur, seed_used):
            clip.video_path = path
            clip.duration = dur
            clip.seed = seed_used
            clip.status = "done"
            self.project.save(PROJECTS_DIR)

            def _finalize():
                self.timeline.invalidate_thumbnail(clip.id)
                self.timeline.draw()
                self.preview_panel.show_clip(clip, len(self.project.clips))

            self.after(0, _finalize)

        def on_error(err):
            clip.status = "error"
            self.project.save(PROJECTS_DIR)
            self.after(0, lambda: self.generator_panel.on_gen_error(err))
            self.after(0, lambda: self.timeline.draw())

        self._gen_service.generate_clip(
            project_id=self.project.id,
            clip_id=clip.id,
            prompt=clip.prompt,
            engine=self.engine_var.get(),
            duration=clip.duration,
            steps=int(self.generator_panel.steps_var.get()),
            guidance=float(self.generator_panel.guidance_var.get()),
            seed=None,
            width=self.generator_panel._get_resolution()[0],
            height=self.generator_panel._get_resolution()[1],
            fps=self.project.output_fps,
            negative_prompt=self.generator_panel.neg_box.get("0.0", "end").strip(),
            ref_images=None,
            on_progress=on_progress,
            on_done=on_done,
            on_error=on_error,
        )

    def _regenerate_image_clip(self, clip):
        """Regenera clip de imagem via HF API."""
        import threading
        prompt = clip.prompt.replace("[IMG] ", "")

        self.generator_panel._img_status.configure(text="Regenerando imagem...", text_color=C["gold"])

        def run():
            try:
                img = self.generator_panel._gen_img_hf(prompt, False)
                if img:
                    def on_done():
                        self.generator_panel._save_and_add_to_timeline(img, prompt, clip.duration)
                        # Remover clip antigo
                        self.project.remove_clip(clip.id)
                        self.project.save(PROJECTS_DIR)
                        self.timeline.draw()
                        self.generator_panel._img_status.configure(text="Regenerado!", text_color=C["cyan"])
                    self.after(0, on_done)
            except Exception as e:
                self.after(0, lambda: self.generator_panel._img_status.configure(
                    text=f"Erro: {str(e)[:50]}", text_color="#ff4444"))

        threading.Thread(target=run, daemon=True).start()

    def split_clip(self, clip):
        ph = self.timeline.playhead_pos
        current = sum(c.duration for c in sorted(self.project.clips, key=lambda c: c.position) if c.position < clip.position)
        split = ph - current
        if split <= 0 or split >= clip.duration:
            split = clip.duration / 2
        if split < 0.5 or split > clip.duration - 0.5:
            messagebox.showinfo("Info", "Clip muito curto para dividir")
            return

        new = self.project.add_clip(prompt=clip.prompt, position=clip.position + 1)
        new.duration = round(clip.duration - split, 1)
        new.seed = clip.seed
        clip.duration = round(split, 1)
        self.project.save(PROJECTS_DIR)
        self.timeline.draw()

    def enter_split_mode(self):
        """Ativa modo corte na timeline - cursor muda e proximo click divide."""
        self.timeline.enter_split_mode()

    def delete_clip(self, clip):
        from makevid.core.logger import log_clip_action
        log_clip_action("remover", clip.id, f"prompt='{clip.prompt[:30]}'")
        self.project.remove_clip(clip.id)
        if self.timeline.selected_clip_id == clip.id:
            self.timeline.selected_clip_id = None
        self.project.save(PROJECTS_DIR)
        self.timeline.draw()
        self.preview_panel.clear()

    # ============================================================
    # EXPORT
    # ============================================================

    def _export_final(self):
        from makevid.core.timeline import concat_clips
        done = [c for c in sorted(self.project.clips, key=lambda x: x.position) if c.status == "done" and c.video_path]
        if not done:
            messagebox.showwarning("Aviso", "Nenhum clip pronto")
            return

        # Janela para pedir nome
        win = ctk.CTkToplevel(self)
        win.title("Exportar Video Final")
        win.geometry("400x180")
        win.configure(fg_color=C["panel"])
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="EXPORTAR VIDEO FINAL", font=("Segoe UI", 13, "bold"),
                     text_color=C["gold"]).pack(anchor="w", padx=15, pady=(15, 5))

        total_dur = sum(c.duration for c in done)
        ctk.CTkLabel(win, text=f"{len(done)} clips | {total_dur:.1f}s",
                     text_color=C["text3"], font=("Segoe UI", 10)).pack(anchor="w", padx=15)

        ctk.CTkLabel(win, text="Nome do video:", text_color=C["text2"],
                     font=("Segoe UI", 10)).pack(anchor="w", padx=15, pady=(10, 3))
        name_var = ctk.StringVar(value=self.project.name)
        ctk.CTkEntry(win, textvariable=name_var, fg_color=C["input"],
                     border_color=C["gold"], border_width=1, text_color=C["text"],
                     font=("Segoe UI", 11), width=350).pack(padx=15)

        status = ctk.CTkLabel(win, text="", text_color=C["text3"], font=("Segoe UI", 9))
        status.pack(anchor="w", padx=15, pady=3)

        def do_export():
            name = name_var.get().strip()
            if not name:
                return
            status.configure(text="Exportando...", text_color=C["gold"])
            win.update()
            try:
                import re
                safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
                if not safe_name:
                    safe_name = "video_final"

                # Salvar em Meus Videos (outputs)
                output_meus = OUTPUTS_DIR / self.project.id / f"{safe_name}.mp4"
                concat_clips([c.video_path for c in done], output_meus, fps=self.project.output_fps)

                # Copiar para Downloads
                downloads = Path.home() / "Downloads"
                output_dl = downloads / f"{safe_name}.mp4"
                import shutil
                shutil.copy2(str(output_meus), str(output_dl))

                status.configure(text=f"Salvo em Downloads e Meus Videos!", text_color=C["cyan"])
                win.after(1500, win.destroy)
            except Exception as e:
                status.configure(text=f"Erro: {str(e)[:60]}", text_color="#ff4444")

        ctk.CTkButton(win, text="EXPORTAR", command=do_export, height=36,
                      font=("Segoe UI", 12, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700").pack(fill="x", padx=15, pady=(8, 10))

    def _export_game_engine(self):
        from makevid.core.export import PRESETS, RESOLUTIONS, FPS_OPTIONS, export_video, get_preset_key
        from makevid.core.timeline import concat_clips

        done = [c for c in sorted(self.project.clips, key=lambda x: x.position) if c.status == "done" and c.video_path]
        if not done:
            messagebox.showwarning("Aviso", "Nenhum clip pronto")
            return

        win = ctk.CTkToplevel(self)
        win.title("Export Game Engine")
        win.geometry("420x380")
        win.configure(fg_color=C["panel"])
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Export Game Engine", font=("Segoe UI", 14, "bold"), text_color=C["gold"]).pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(win, text="Formato", text_color=C["text2"]).pack(anchor="w", padx=15, pady=(5, 2))
        preset_var = ctk.StringVar(value=list(PRESETS.values())[0]["label"])
        ctk.CTkOptionMenu(win, variable=preset_var, values=[p["label"] for p in PRESETS.values()],
                          fg_color=C["card"], button_color=C["gold"], text_color=C["text"], width=350).pack(padx=15, pady=2)

        ctk.CTkLabel(win, text="Resolucao", text_color=C["text2"]).pack(anchor="w", padx=15, pady=(8, 2))
        res_var = ctk.StringVar(value="1080p")
        ctk.CTkOptionMenu(win, variable=res_var, values=list(RESOLUTIONS.keys()),
                          fg_color=C["card"], button_color=C["gold"], text_color=C["text"], width=150).pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(win, text="FPS", text_color=C["text2"]).pack(anchor="w", padx=15, pady=(8, 2))
        fps_var = ctk.StringVar(value="30")
        ctk.CTkOptionMenu(win, variable=fps_var, values=[str(f) for f in FPS_OPTIONS],
                          fg_color=C["card"], button_color=C["gold"], text_color=C["text"], width=80).pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(win, text="Nome", text_color=C["text2"]).pack(anchor="w", padx=15, pady=(8, 2))
        name_var = ctk.StringVar(value=f"cinematic_{self.project.name}")
        ctk.CTkEntry(win, textvariable=name_var, fg_color=C["input"], border_color=C["border"], text_color=C["text"], width=300).pack(anchor="w", padx=15, pady=2)

        status = ctk.CTkLabel(win, text="", text_color=C["text3"])
        status.pack(anchor="w", padx=15, pady=5)

        def do_export():
            status.configure(text="Exportando...", text_color=C["gold"])
            win.update()
            try:
                tmp = OUTPUTS_DIR / self.project.id / "_tmp.mp4"
                concat_clips([c.video_path for c in done], tmp, fps=self.project.output_fps)
                res = RESOLUTIONS.get(res_var.get(), (1920, 1080)) or (1920, 1080)
                result = export_video(tmp, OUTPUTS_DIR / self.project.id / "export",
                                      name_var.get(), get_preset_key(preset_var.get()), res, int(fps_var.get()))
                tmp.unlink(missing_ok=True)
                status.configure(text=f"OK: {result.name}", text_color=C["cyan"])
            except Exception as e:
                status.configure(text=f"Erro: {str(e)[:60]}", text_color=C["red"])

        ctk.CTkButton(win, text="EXPORTAR", command=do_export, height=38, font=("Segoe UI", 12, "bold"),
                      fg_color=C["gold"], text_color="#0a0a0f", hover_color="#dbb042").pack(fill="x", padx=15, pady=(12, 10))
