"""Menus - Dropdowns customizados na topbar (sem tk.Menu nativo)."""

import customtkinter as ctk
import os
import time
from makevid.ui.theme import C
from makevid.config import OUTPUTS_DIR, PROJECTS_DIR


class _ToolTip:
    """Tooltip que aparece ao passar o mouse sobre um widget."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, event=None):
        if self.widget.winfo_exists():
            self._after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        if self._tip or not self.widget.winfo_exists():
            return
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 4
            y = self.widget.winfo_rooty()
            root = self.widget.winfo_toplevel()
            if not root.winfo_exists():
                return
            import tkinter as tk
            self._tip = tw = tk.Toplevel(root)
            tw.overrideredirect(True)
            tw.geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            tw.configure(bg=C["card"])
            frame = ctk.CTkFrame(tw, fg_color=C["card"], border_color=C["gold"],
                                 border_width=1, corner_radius=4)
            frame.pack(fill="both", expand=True)
            ctk.CTkLabel(frame, text=self.text, font=("Segoe UI", 9),
                         text_color=C["text2"], wraplength=250).pack(padx=8, pady=4)
        except Exception:
            self._tip = None

    def _hide(self, event=None):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


class DropdownMenu:
    """Menu dropdown que aparece abaixo do botao ao clicar."""

    def __init__(self, parent_btn, app, items, checkable_var=None):
        """items = [(label, command), ...] ou None para separador.
        checkable_var: se fornecido, mostra check ao lado do item cujo label corresponde ao valor."""
        self.app = app
        self.parent_btn = parent_btn
        self.items = items
        self.checkable_var = checkable_var
        self._popup = None
        parent_btn.configure(command=self.toggle)

    def toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return

        x = self.parent_btn.winfo_rootx()
        y = self.parent_btn.winfo_rooty() + self.parent_btn.winfo_height()

        self._popup = ctk.CTkToplevel(self.app)
        self._popup.overrideredirect(True)
        self._popup.geometry(f"+{x}+{y}")
        self._popup.configure(fg_color=C["card"])
        self._popup.attributes("-topmost", True)
        self._popup.bind("<FocusOut>", lambda e: self._close())

        frame = ctk.CTkFrame(self._popup, fg_color=C["card"], border_color=C["gold"],
                             border_width=1, corner_radius=4)
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        for item in self.items:
            if item is None:
                ctk.CTkFrame(frame, height=1, fg_color=C["border"]).pack(fill="x", padx=4, pady=2)
            else:
                label = item[0]
                cmd = item[1]
                tooltip = item[2] if len(item) > 2 else None
                # Check mark para item ativo
                prefix = ""
                if self.checkable_var and self.checkable_var.get() == label:
                    prefix = "\u2713 "
                btn = ctk.CTkButton(frame, text=f"{prefix}{label}", height=28, anchor="w",
                              font=("Segoe UI", 10), fg_color="transparent",
                              hover_color=C["card_hover"], text_color=C["text"],
                              command=lambda c=cmd: self._exec(c))
                btn.pack(fill="x", padx=4, pady=1)
                if tooltip:
                    _ToolTip(btn, tooltip)

        self._popup.after(100, lambda: self._popup.focus_set() if self._popup and self._popup.winfo_exists() else None)

    def _exec(self, cmd):
        self._close()
        cmd()

    def _close(self):
        if self._popup:
            try:
                if self._popup.winfo_exists():
                    self._popup.destroy()
            except Exception:
                pass
        self._popup = None


def build_topbar(app):
    """Constroi topbar com logo + menus dropdown customizados."""
    bar = ctk.CTkFrame(app, height=42, fg_color=C["panel"], corner_radius=0,
                       border_color=C["border"], border_width=1)
    bar.pack(fill="x")
    bar.pack_propagate(False)

    ctk.CTkLabel(bar, text="MAKE", font=("Segoe UI", 17, "bold"), text_color=C["gold"]).pack(side="left", padx=(12, 0))
    ctk.CTkLabel(bar, text="VID", font=("Segoe UI", 17, "bold"), text_color=C["cyan"]).pack(side="left")
    ctk.CTkFrame(bar, width=1, fg_color=C["border"]).pack(side="left", padx=10, fill="y", pady=8)

    def menu_btn(text):
        btn = ctk.CTkButton(bar, text=text, width=65, height=26, font=("Segoe UI", 10, "bold"),
                            fg_color="transparent", hover_color="#1a2a3a",
                            text_color=C["text2"], corner_radius=4,
                            border_width=1, border_color=C["panel"])
        btn.pack(side="left", padx=2)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(border_color=C["gold"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(border_color=C["panel"]))
        return btn

    btn_arquivo = menu_btn("\U0001f4c1 Arquivo")
    DropdownMenu(btn_arquivo, app, [
        ("Novo Projeto", lambda: _new_project(app)),
        None,
        ("Meus Videos", lambda: _open_video_browser(app)),
        ("Meus Audios", lambda: app.preview_panel.show_audio_browser()),
    ])

    btn_engine = menu_btn("\u2699 Engine")
    DropdownMenu(btn_engine, app, [
        ("Local (GPU)", lambda: app.engine_var.set("Local (GPU)"), "Roda localmente na GPU (precisa NVIDIA 12GB+)"),
        ("Local (CPU)", lambda: app.engine_var.set("Local (CPU)"), "Roda em CPU (MUITO lento, 32GB+ RAM)"),
        ("Wan 2.2 TI2V", lambda: app.engine_var.set("Wan 2.2 TI2V"), "Wan 2.2 5B local (NVIDIA 12GB+)"),
        None,
        ("VACE (Referencia)", lambda: app.engine_var.set("VACE (Referencia)"), "Consistencia de personagem (NVIDIA 12GB+)"),
        ("V2V (Refinar)", lambda: app.engine_var.set("V2V (Refinar)"), "Re-estiliza video existente (NVIDIA 12GB+)"),
        None,
        ("HuggingFace API", lambda: app.engine_var.set("HuggingFace API"), "Gera via internet (imagem e video se suportado)"),
    ], checkable_var=app.engine_var)

    btn_estilo = menu_btn("\U0001f3a8 Estilo")
    DropdownMenu(btn_estilo, app, [
        ("Storyboard", lambda: _open_style(app, "storyboard"), "Estilo global + cenas da historia com checkpoints na timeline"),
        ("Personagens", lambda: _open_style(app, "chars"), "Fichas de personagens com ref images para consistencia"),
        ("Ambientacao", lambda: _open_style(app, "ambience"), "Imagens de referencia visual para treinar ambientacao (Wan TI2V)"),
    ])

    btn_audio_ia = menu_btn("\u266b Audio IA")
    _ToolTip(btn_audio_ia, "Gera audio automaticamente para a cena.\nO audio sera gerado para o clip selecionado\nou onde a linha vermelha da timeline esta.\n\nInclui: Voz (TTS), SFX, Ambiencia e Musica.")
    DropdownMenu(btn_audio_ia, app, [
        ("Gerar Audio da Cena", lambda: _generate_scene_audio(app), "Gera voz + SFX + ambiencia da cena selecionada"),
        ("Gerar Audio de Todas as Cenas", lambda: _generate_all_audio(app), "Gera voz + SFX + ambiencia de TODAS as cenas do storyboard"),
    ])

    btn_logs = menu_btn("\U0001f4cb Logs")
    DropdownMenu(btn_logs, app, [
        ("Ver Logs", lambda: _open_logs(app)),
    ])

    app._engine_label = ctk.CTkLabel(bar, text="", text_color=C["text3"], font=("Consolas", 9))
    app._engine_label.pack(side="right", padx=12)
    _update_engine_label(app)
    app.engine_var.trace_add("write", lambda *_: _update_engine_label(app))


def _update_engine_label(app):
    app._engine_label.configure(text=app.engine_var.get())


def _new_project(app):
    from makevid.core.project import Project
    name = "projeto_" + str(int(time.time()))[-4:]
    app.project = Project.create(name)
    app.project.save(PROJECTS_DIR)
    app.timeline.selected_clip_id = None
    app.timeline.draw()


def _open_logs(app):
    from makevid.core.logger import get_log_content, clear_logs

    win = ctk.CTkToplevel(app)
    win.title("Logs - MAKEVID")
    win.geometry("750x450")
    win.configure(fg_color=C["panel"])
    win.transient(app)

    # Header
    header = ctk.CTkFrame(win, fg_color="transparent")
    header.pack(fill="x", padx=10, pady=(8, 4))
    ctk.CTkLabel(header, text="LOGS", font=("Segoe UI", 12, "bold"),
                 text_color=C["gold"]).pack(side="left")

    # Filtro
    filter_var = ctk.StringVar(value="Todos")
    ctk.CTkOptionMenu(header, variable=filter_var,
                      values=["Todos", "Erros", "Audio", "Export", "Clip", "Geracao"],
                      fg_color=C["card"], button_color=C["purple"],
                      text_color=C["text"], font=("Consolas", 9),
                      width=100, height=24).pack(side="right", padx=4)

    log_box = ctk.CTkTextbox(win, fg_color="#0a0c14", text_color="#88cc88",
                             font=("Consolas", 9), border_color=C["border"], border_width=1)
    log_box.pack(fill="both", expand=True, padx=10, pady=(0, 5))

    def _refresh():
        content = get_log_content(500)
        f = filter_var.get()
        if f == "Erros":
            content = "\n".join(l for l in content.split("\n") if "ERROR" in l or "FALHA" in l or "Erro" in l)
        elif f == "Audio":
            content = "\n".join(l for l in content.split("\n") if "audio" in l.lower() or "sound" in l.lower() or "tts" in l.lower())
        elif f == "Export":
            content = "\n".join(l for l in content.split("\n") if "export" in l.lower() or "Export" in l)
        elif f == "Clip":
            content = "\n".join(l for l in content.split("\n") if "clip" in l.lower())
        elif f == "Geracao":
            content = "\n".join(l for l in content.split("\n") if "gen" in l.lower() or "INICIO" in l or "OK [" in l)
        log_box.delete("0.0", "end")
        log_box.insert("0.0", content or "(nenhum log para este filtro)")
        log_box.see("end")

    _refresh()
    filter_var.trace_add("write", lambda *a: _refresh())

    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack(fill="x", padx=10, pady=(0, 8))
    ctk.CTkButton(btn_frame, text="Atualizar", height=26, fg_color=C["card"], text_color=C["text2"],
                  hover_color=C["card_hover"],
                  command=_refresh).pack(side="left", padx=4)
    ctk.CTkButton(btn_frame, text="Limpar Logs", height=26, fg_color="#2a0808", text_color="#ff4444",
                  border_width=1, border_color="#ff4444", hover_color="#3a1010",
                  command=lambda: [clear_logs(), _refresh()]).pack(side="left", padx=4)


def _open_style(app, tab):
    """Abre painel de estilo inline (World Bible ou Personagens)."""
    from makevid.ui.panel_style import StylePanel
    if not hasattr(app, '_style_panel'):
        app._style_panel = StylePanel(app)
    app._style_panel.show(tab)


def _open_video_browser(app):
    """Abre browser interno no lugar do display (preview panel)."""
    app.preview_panel.show_video_browser()


def _generate_scene_audio(app):
    """Gera audio da cena selecionada (storyboard ou prompt do clip)."""
    from makevid.services.audio_service import AudioService
    from makevid.core import freesound_provider
    from makevid.config import PROJECTS_DIR
    from tkinter import messagebox

    # Checar se Freesound key esta configurada
    if not freesound_provider.FREESOUND_API_KEY:
        app.generator_panel._show_freesound_prompt(on_saved=lambda: _generate_scene_audio(app))
        return

    scenes = app.project.world.scenes
    clips = sorted(app.project.clips, key=lambda c: c.position)

    if not scenes and not clips:
        messagebox.showinfo("Info", "Nenhum clip na timeline.")
        return

    # Determinar indice do clip selecionado ou na posicao do playhead
    idx = 0
    if app.timeline.selected_clip_id:
        clip = app.project.get_clip(app.timeline.selected_clip_id)
        if clip:
            idx = clip.position
    else:
        # Usar playhead para encontrar o clip
        ph = app.timeline.playhead_pos
        current = 0.0
        for c in clips:
            if current <= ph < current + c.duration:
                idx = c.position
                break
            current += c.duration

    # Usar storyboard SOMENTE se foi salvo/aplicado na timeline
    use_storyboard = (scenes and idx < len(scenes)
                      and getattr(app.project, '_storyboard_applied', False))
    if use_storyboard:
        scene = scenes[idx]
    else:
        idx = min(idx, len(clips) - 1)
        clip = clips[idx]
        prompt = clip.prompt or ""
        # Remover prefixo [IMG] se presente
        if prompt.startswith("[IMG] "):
            prompt = prompt[6:]
        scene = {
            "visual": prompt,
            "duration": str(clip.duration),
        }
        # Extrair dialogo do prompt (texto entre aspas ou apos "says:"/"fala:")
        import re
        dialogue = ""
        # Texto entre aspas
        quotes = re.findall(r'["\u201c]([^"\u201d]+)["\u201d]', prompt)
        if quotes:
            dialogue = "\n".join(quotes)
        else:
            # Padrao "personagem says/fala: texto"
            say_match = re.search(r'(?:says|fala|diz|whispers|grita|shouts)[:\s]+(.+?)(?:\.|$)', prompt, re.IGNORECASE)
            if say_match:
                dialogue = say_match.group(1).strip()
        if dialogue:
            scene["dialogue"] = dialogue
    svc = AudioService()

    # Mostrar loading no painel esquerdo
    gp = app.generator_panel
    # Garantir visibilidade
    if app.timeline.fx_panel._visible:
        app.timeline.fx_panel.hide()
    if gp._tab_var != "clip":
        gp._switch_tab("clip")
    gp.gen_btn.configure(state="disabled", text="\u266b GERANDO AUDIO...", fg_color="#3a2a0a")
    gp.status_label.configure(text=f"\u266b Cena {idx+1}: buscando sons...", text_color=C["gold"])
    gp.progress.set(0.15)
    # Scroll para baixo para mostrar status
    gp.scroll._parent_canvas.yview_moveto(1.0)

    def on_progress(msg):
        def _update():
            gp.status_label.configure(text=f"\u266b {msg}", text_color=C["gold"])
            gp.progress.set(min(0.9, gp.progress.get() + 0.15))
        app.after(0, _update)

    def on_done(plan, results):
        # Adicionar resultados como track items na timeline
        if use_storyboard:
            clip_start = sum(float(scenes[i].get("duration", 5)) for i in range(idx))
        else:
            clip_start = sum(c.duration for c in clips[:idx])

        if "voices" in results:
            for i, path in enumerate(results["voices"]):
                voice = plan.voices[i] if i < len(plan.voices) else None
                name = f"{voice.character}: {voice.text[:20]}" if voice else f"Voz {i+1}"
                start = clip_start + (voice.start if voice else 0)
                # Usar duracao real do arquivo
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(path) or ((voice.end - voice.start) if voice else 2.0)
                app.project.add_track_item(name=name, track="voice",
                                           start_time=start, duration=dur, file_path=path,
                                           clip_index=idx)

        if "ambience" in results:
            layers_str = plan.ambience.description if plan.ambience else ""
            from makevid.core.audio_utils import get_audio_duration
            dur = get_audio_duration(results["ambience"]) or plan.scene_duration
            app.project.add_track_item(
                name=f"Amb: {plan.ambience.description.split('|')[0][:20]}", track="sfx",
                start_time=clip_start, duration=dur,
                file_path=results["ambience"],
                params={"layers": layers_str}, clip_index=idx)

        if "sfx" in results:
            sfx_path = results["sfx"][0] if results["sfx"] else None
            if sfx_path:
                layers_str = getattr(svc, '_last_sfx_layers', '')
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(sfx_path) or plan.scene_duration
                app.project.add_track_item(
                    name=f"SFX: {layers_str.split('|')[0][:15]}", track="sfx",
                    start_time=clip_start, duration=dur,
                    file_path=sfx_path,
                    params={"layers": layers_str}, clip_index=idx)

        if "music" in results:
            from makevid.core.audio_utils import get_audio_duration
            dur = get_audio_duration(results["music"]) or plan.scene_duration
            app.project.add_track_item(
                name=f"Music: {plan.music.mood[:15]}", track="music",
                start_time=clip_start, duration=dur,
                file_path=results["music"], clip_index=idx)

        app.project.save(PROJECTS_DIR)
        def _done():
            gp.gen_btn.configure(state="normal", text="GERAR CLIP", fg_color=C["gold"])
            gp.status_label.configure(text="\u2714 Audio gerado!", text_color=C["cyan"])
            gp.progress.set(0)
            app.timeline.draw()
            # Habilitar play no preview
            clip = clips[idx] if idx < len(clips) else None
            if clip:
                app.timeline.selected_clip_id = clip.id
                app.preview_panel.show_clip(clip, len(app.project.clips))
        app.after(0, _done)

    def on_error(err):
        def _err():
            gp.gen_btn.configure(state="normal", text="GERAR CLIP", fg_color=C["gold"])
            gp.status_label.configure(text=f"Erro: {err[:50]}", text_color="#ff4444")
            gp.progress.set(0)
        app.after(0, _err)

    svc.generate_scene_audio(
        project_id=app.project.id,
        scene_metadata=scene,
        scene_index=idx,
        on_progress=on_progress,
        on_done=on_done,
        on_error=on_error,
        characters=app.project.characters,
    )


def _generate_all_audio(app):
    """Gera audio de todas as cenas - usa storyboard OU prompts dos clips na timeline."""
    from makevid.services.audio_service import AudioService
    from makevid.core import freesound_provider
    from makevid.config import PROJECTS_DIR
    from tkinter import messagebox

    # Checar se Freesound key esta configurada
    if not freesound_provider.FREESOUND_API_KEY:
        app.generator_panel._show_freesound_prompt(on_saved=lambda: _generate_all_audio(app))
        return

    scenes = app.project.world.scenes
    clips = sorted(app.project.clips, key=lambda c: c.position)

    # Se nao tem storyboard, gerar scenes a partir dos prompts dos clips
    if not scenes and not clips:
        messagebox.showinfo("Info", "Nenhuma cena no storyboard e nenhum clip na timeline.")
        return

    if not scenes:
        # Criar scenes virtuais a partir dos prompts dos clips
        scenes = []
        for clip in clips:
            scenes.append({
                "visual": clip.prompt or "",
                "duration": str(clip.duration),
            })

    svc = AudioService()

    gp = app.generator_panel
    gp.gen_btn.configure(state="disabled", text="\u266b GERANDO AUDIO...", fg_color="#3a2a0a")
    gp.status_label.configure(text=f"\u266b {len(scenes)} cenas: buscando sons...", text_color=C["gold"])
    gp.progress.set(0.1)
    gp.scroll._parent_canvas.yview_moveto(1.0)

    def on_progress(msg):
        def _update():
            gp.status_label.configure(text=f"\u266b {msg}", text_color=C["gold"])
            gp.progress.set(min(0.9, gp.progress.get() + 0.05))
        app.after(0, _update)

    def on_done(all_results):
        clip_start = 0.0
        for scene_idx, (plan, results) in enumerate(all_results):
            if "voices" in results:
                for i, path in enumerate(results["voices"]):
                    voice = plan.voices[i] if i < len(plan.voices) else None
                    name = f"{voice.character}: {voice.text[:20]}" if voice else f"Voz"
                    start = clip_start + (voice.start if voice else 0)
                    from makevid.core.audio_utils import get_audio_duration
                    dur = get_audio_duration(path) or ((voice.end - voice.start) if voice else 2.0)
                    app.project.add_track_item(name=name, track="voice",
                                               start_time=start, duration=dur, file_path=path,
                                               clip_index=scene_idx)
            if "ambience" in results:
                layers_str = plan.ambience.description if plan.ambience else ""
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(results["ambience"]) or plan.scene_duration
                app.project.add_track_item(
                    name=f"Amb: {plan.ambience.description.split('|')[0][:15]}", track="sfx",
                    start_time=clip_start, duration=dur,
                    file_path=results["ambience"],
                    params={"layers": layers_str}, clip_index=scene_idx)
            if "sfx" in results:
                sfx_path = results["sfx"][0] if results["sfx"] else None
                if sfx_path:
                    layers_str = getattr(svc, '_last_sfx_layers', '')
                    from makevid.core.audio_utils import get_audio_duration
                    dur = get_audio_duration(sfx_path) or plan.scene_duration
                    app.project.add_track_item(
                        name=f"SFX: {layers_str.split('|')[0][:15]}",
                        track="sfx", start_time=clip_start,
                        duration=dur, file_path=sfx_path,
                        params={"layers": layers_str}, clip_index=scene_idx)
            if "music" in results:
                from makevid.core.audio_utils import get_audio_duration
                dur = get_audio_duration(results["music"]) or plan.scene_duration
                app.project.add_track_item(
                    name=f"Music: {plan.music.mood[:15]}", track="music",
                    start_time=clip_start, duration=dur,
                    file_path=results["music"], clip_index=scene_idx)
            clip_start += plan.scene_duration

        app.project.save(PROJECTS_DIR)
        def _done():
            gp.gen_btn.configure(state="normal", text="GERAR CLIP", fg_color=C["gold"])
            gp.status_label.configure(text=f"\u2714 {len(all_results)} cenas prontas!", text_color=C["cyan"])
            gp.progress.set(0)
            app.timeline.draw()
            # Reativar play no preview
            clip = clips[0] if clips else None
            if clip:
                app.timeline.selected_clip_id = clip.id
                app.preview_panel.show_clip(clip, len(app.project.clips))
        app.after(0, _done)

    def on_error(err):
        def _err():
            gp.gen_btn.configure(state="normal", text="GERAR CLIP", fg_color=C["gold"])
            gp.status_label.configure(text=f"Erro: {err[:50]}", text_color="#ff4444")
            gp.progress.set(0)
        app.after(0, _err)

    svc.generate_all_scenes(
        project_id=app.project.id,
        scenes=scenes,
        on_progress=on_progress,
        on_done=on_done,
        on_error=on_error,
        characters=app.project.characters,
    )

