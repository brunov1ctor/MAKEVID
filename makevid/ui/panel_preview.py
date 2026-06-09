"""Panel Preview - Display de video com play/pause. Coordena Player e Properties."""

import logging
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from makevid.ui.theme import C
from makevid.ui.player import TimelinePlayer
from makevid.ui.panel_properties import ClipProperties
from makevid.config import PROJECTS_DIR

log = logging.getLogger("preview")


class PreviewPanel:
    def __init__(self, parent, app):
        self.app = app

        panel = ctk.CTkFrame(parent, fg_color=C["panel"], border_color=C["border"], border_width=1, corner_radius=6)
        panel.pack(side="right", fill="both", expand=True, pady=4)
        panel.pack_propagate(False)
        self.panel = panel

        self.preview_frame = ctk.CTkFrame(panel, fg_color="#050508", border_color=C["border"], border_width=1, corner_radius=4)
        self.preview_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="",
                                          text_color=C["text3"], font=("Segoe UI", 12))
        self.preview_label.pack(expand=True)

        # Overlay invisivel para capturar clicks durante playback (CTkLabel perde binds ao atualizar imagem)
        import tkinter as tk
        self._click_overlay = tk.Frame(self.preview_frame, bg="", cursor="hand2")
        self._click_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._click_overlay.lower()  # Comeca escondido atras de tudo
        self._click_overlay.bind("<Button-1>", self._on_overlay_click)

        self.clip_info = ctk.CTkLabel(panel, text="", text_color=C["text2"], font=("Segoe UI", 10), anchor="w")
        self.clip_info.pack(fill="x", padx=10, pady=(0, 4))

        # Sub-components
        self.player = TimelinePlayer(self)
        self.properties = ClipProperties(self)
        self._preview_img_ref = None
        self._play_btn = None
        self._is_playing_mode = False

        # Resize
        self.preview_frame.bind("<Configure>", self._on_resize)

    # ============================================================
    # PUBLIC API
    # ============================================================

    def show_clip(self, clip, total_clips):
        """Mostra info do clip selecionado."""
        self.clip_info.configure(
            text=f"Clip {clip.position+1}/{total_clips} | {clip.duration:.1f}s | seed={clip.seed} | {clip.prompt[:40]}")

        if not self.preview_label.winfo_ismapped():
            self.preview_label.pack(expand=True)

        if clip.video_path and Path(clip.video_path).exists():
            self._show_thumbnail(clip.video_path)
        else:
            self._preview_img_ref = None
            self.preview_label.configure(image=None, text=f"Clip #{clip.position+1}\n\n(sem video gerado)")

        self._show_play_button(lambda: self.player.play(start_clip=clip))
        self.properties.show(clip, total_clips)

    def show_generated(self, clip):
        if hasattr(self, '_browser_frame') and self._browser_frame and self._browser_frame.winfo_exists():
            self._close_video_browser()
        if not self.preview_label.winfo_ismapped():
            self.preview_label.pack(expand=True)
        self.show_clip(clip, len(self.app.project.clips))

    def show_timeline_preview(self):
        """Mostra preview da timeline com play button."""
        clips = sorted(self.app.project.clips, key=lambda x: x.position)
        if not clips:
            self.preview_label.configure(image=None, text="")
            return

        # Mostrar frame na posicao do playhead
        playhead = self.app.timeline.playhead_pos
        target_clip = None
        current = 0.0
        for c in clips:
            if current + c.duration > playhead:
                target_clip = c
                break
            current += c.duration
        if not target_clip:
            target_clip = clips[0]

        if target_clip.status == "done" and target_clip.video_path and Path(target_clip.video_path).exists():
            self._show_thumbnail(target_clip.video_path)
        else:
            self._preview_img_ref = None
            self.preview_label.configure(image=None, text="")

        total_dur = self.app.project.total_duration()
        self.clip_info.configure(text=f"Timeline | {len(clips)} clips | {total_dur:.1f}s total")
        # Sempre mostrar play button se tem clips com video
        has_video = any(c.status == "done" and c.video_path for c in clips)
        if has_video:
            self._show_play_button(lambda: self.player.play())

    def clear(self):
        self._preview_img_ref = None
        self._hide_play_button()
        self.preview_label.configure(image=None, text="")
        self.clip_info.configure(text="")
        self.properties.close()

    # ============================================================
    # CALLBACKS DO PLAYER (chamados pelo TimelinePlayer)
    # ============================================================

    def _get_current_time(self):
        """Calcula tempo atual usando o playhead_pos que ja e atualizado pelo player."""
        return self.app.timeline.playhead_pos

    def _set_video_frame(self, frame):
        """Player chama isso pra mostrar um frame de video."""
        from makevid.core.fx_processor import apply_fx_to_frame
        from PIL import ImageTk

        frame_rgb = frame[:, :, ::-1]
        self._last_frame_shape = frame_rgb.shape

        # Aplicar efeitos FX ativos
        try:
            fx_items = self.app.project.get_track_items("fx")
            if fx_items:
                total_dur = self.app.project.total_duration()
                if total_dur > 0:
                    current_time = self._get_current_time()
                    frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, current_time, total_dur)
        except Exception as e:
            log.error(f"_set_video_frame FX error: {e}")

        img = Image.fromarray(frame_rgb)
        img, w, h = self._fit_image(img)

        # Log a cada 40 chamadas
        if not hasattr(self, '_svf_count'):
            self._svf_count = 0
        self._svf_count += 1
        if self._svf_count % 40 == 1:
            log.info(f"_set_video_frame #{self._svf_count}: size=({w},{h}) pixel[0,0]={frame_rgb[0,0].tolist()} time={self._get_current_time():.2f}s")

        # Usar PhotoImage nativo do Tk para garantir refresh a cada frame
        self._tk_photo = ImageTk.PhotoImage(img)
        if hasattr(self, '_playback_label') and self._playback_label:
            self._playback_label.configure(image=self._tk_photo)

    def _set_black_frame(self):
        """Player chama isso pra mostrar tela preta - aplica FX normalmente."""
        import numpy as np
        from makevid.core.fx_processor import apply_fx_to_frame
        from PIL import ImageTk

        if hasattr(self, '_last_frame_shape') and self._last_frame_shape is not None:
            h, w = self._last_frame_shape[0], self._last_frame_shape[1]
        else:
            w = self.app.project.output_width or 832
            h = self.app.project.output_height or 480
            self._last_frame_shape = (h, w, 3)

        frame_rgb = np.zeros((h, w, 3), dtype=np.uint8)

        try:
            fx_items = self.app.project.get_track_items("fx")
            if fx_items:
                total_dur = self.app.project.total_duration()
                if total_dur > 0:
                    current_time = self._get_current_time()
                    frame_rgb = apply_fx_to_frame(frame_rgb, fx_items, current_time, total_dur)
        except Exception:
            pass

        img = Image.fromarray(frame_rgb)
        img, iw, ih = self._fit_image(img)
        self._tk_photo = ImageTk.PhotoImage(img)
        if hasattr(self, '_playback_label') and self._playback_label:
            self._playback_label.configure(image=self._tk_photo)

    def _on_playback_ended(self):
        """Player chama isso quando termina."""
        self._is_playing_mode = False
        self._click_overlay.lower()
        self.preview_frame.unbind("<Button-1>")
        self.preview_label.unbind("<Button-1>")
        self.preview_frame.pack_propagate(True)
        if hasattr(self, '_playback_img_size'):
            del self._playback_img_size
        self._tk_photo = None
        self._svf_count = 0
        # Destruir label nativo e restaurar CTkLabel
        if hasattr(self, '_playback_label') and self._playback_label:
            self._playback_label.destroy()
            self._playback_label = None
        self.preview_label.pack(expand=True)
        self.show_timeline_preview()

    # ============================================================
    # PLAY/PAUSE UI
    # ============================================================

    def _show_play_button(self, command):
        self._hide_play_button()
        try:
            self.preview_label.configure(
                text="\u25b6", font=("Segoe UI", 50),
                text_color="#ffffff", compound="center", cursor="hand2"
            )
        except Exception:
            # Recriar preview_label se corrompido
            self._recreate_preview_label()
            self.preview_label.configure(
                text="\u25b6", font=("Segoe UI", 50),
                text_color="#ffffff", compound="center", cursor="hand2"
            )
        self.preview_label.bind("<Button-1>", lambda e: self._on_play_click(command))
        self.preview_label.bind("<Enter>", lambda e: self.preview_label.configure(
            font=("Segoe UI", 62), text_color="#ff0000"))
        self.preview_label.bind("<Leave>", lambda e: self.preview_label.configure(
            font=("Segoe UI", 50), text_color="#ffffff"))
        self._play_btn = True

    def _recreate_preview_label(self):
        """Recria o preview_label quando esta corrompido."""
        try:
            self.preview_label.destroy()
        except Exception:
            pass
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="",
                                          fg_color="transparent", font=("Segoe UI", 12))
        self.preview_label.pack(expand=True)

    def _on_play_click(self, command):
        """Inicia playback e configura pause."""
        import tkinter as tk
        self._hide_play_button()
        self._is_playing_mode = True
        # Travar tamanho do frame para nao expandir durante playback
        self.preview_frame.pack_propagate(False)
        # Esconder CTkLabel e usar tk.Label nativo (CTkLabel nao atualiza PhotoImage)
        self.preview_label.pack_forget()
        self._playback_label = tk.Label(self.preview_frame, bg="#050508", cursor="hand2")
        self._playback_label.pack(expand=True)
        # Garantir que properties fique por cima do playback label
        if self.properties.is_visible:
            self.properties._panel.lift()
        # Bind click direto no label de playback para pause (NAO usar overlay que cobre a imagem)
        self._click_overlay.lower()
        self._playback_label.bind("<Button-1>", lambda e: self._on_overlay_click(e))
        log.info(f"_on_play_click: playback_label created and bound for pause")
        command()

    def _on_pause_click(self):
        """Pausa e mostra play button de retomar."""
        if not self.player.is_playing:
            return
        self.player.pause()
        self._is_playing_mode = False
        # Destruir playback label e restaurar CTkLabel para mostrar play button
        if hasattr(self, '_playback_label') and self._playback_label:
            self._playback_label.destroy()
            self._playback_label = None
        self.preview_label.pack(expand=True)
        self.preview_label.configure(
            text="\u25b6", font=("Segoe UI", 50),
            text_color="#ffffff", compound="center", cursor="hand2"
        )
        self.preview_label.bind("<Button-1>", lambda e: self._on_resume_click())
        self.preview_label.bind("<Enter>", lambda e: self.preview_label.configure(
            font=("Segoe UI", 62), text_color="#ff0000"))
        self.preview_label.bind("<Leave>", lambda e: self.preview_label.configure(
            font=("Segoe UI", 50), text_color="#ffffff"))

    def _on_resume_click(self):
        """Retoma playback."""
        self.preview_label.configure(text="", cursor="hand2")
        self.preview_label.unbind("<Enter>")
        self.preview_label.unbind("<Leave>")
        self.preview_label.unbind("<Button-1>")
        self._is_playing_mode = True
        # Restaurar playback label se nao existe
        if not hasattr(self, '_playback_label') or not self._playback_label:
            import tkinter as tk
            self.preview_label.pack_forget()
            self._playback_label = tk.Label(self.preview_frame, bg="#050508", cursor="hand2")
            self._playback_label.pack(expand=True)
        self._playback_label.bind("<Button-1>", lambda e: self._on_overlay_click(e))
        self._click_overlay.lower()
        # Garantir z-order do properties
        if self.properties.is_visible:
            self.properties._panel.lift()
        self.player.play()  # resume via play (detecta _paused)

    def _hide_play_button(self):
        if self._play_btn:
            self.preview_label.configure(text="", cursor="", compound="top")
            self.preview_label.unbind("<Button-1>")
            self.preview_label.unbind("<Enter>")
            self.preview_label.unbind("<Leave>")
            self._play_btn = None

    def _on_overlay_click(self, event):
        """Click no overlay transparente durante playback = pause."""
        if self._is_playing_mode and self.player.is_playing:
            self._on_pause_click()
        elif self.player.is_paused:
            self._on_resume_click()

    # ============================================================
    # UTILS
    # ============================================================

    def _show_thumbnail(self, video_path):
        try:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame_rgb = frame[:, :, ::-1]
                img = Image.fromarray(frame_rgb)
                img, w, h = self._fit_image(img)
                self._preview_img_ref = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                self.preview_label.configure(image=self._preview_img_ref, text="", compound="center")
                return
        except Exception as e:
            log.warning(f"Thumbnail failed for {video_path}: {e}")
        self._preview_img_ref = None

    def _fit_image(self, img):
        # Tamanho fixo durante playback
        if hasattr(self, '_playback_img_size'):
            return img.resize(self._playback_img_size, Image.LANCZOS), self._playback_img_size[0], self._playback_img_size[1]
        # Calcular tamanho disponivel sem forcar relayout
        fw = self.preview_frame.winfo_width()
        fh = self.preview_frame.winfo_height()
        if fw < 50 or fh < 50:
            self.preview_frame.update_idletasks()
            fw = self.preview_frame.winfo_width()
            fh = self.preview_frame.winfo_height()
        max_w = max(fw - 12, 200)
        max_h = max(fh - 12, 150)
        ratio = min(max_w / img.width, max_h / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        if self.player.is_playing:
            self._playback_img_size = (new_w, new_h)
        return img.resize((new_w, new_h), Image.LANCZOS), new_w, new_h

    def _on_resize(self, event=None):
        if self.player.is_playing or self.player.is_paused:
            return
        clips = sorted(self.app.project.clips, key=lambda x: x.position)
        first = next((c for c in clips if c.status == "done" and c.video_path and Path(c.video_path).exists()), None)
        if first and self._preview_img_ref:
            self._show_thumbnail(first.video_path)

    # ============================================================
    # VIDEO BROWSER (mantido aqui por ser UI do panel)
    # ============================================================

    def show_video_browser(self):
        """Abre browser de videos."""
        import json
        import time as _time
        from makevid.config import OUTPUTS_DIR

        if self.player.is_playing:
            self.player.stop()
        self._hide_play_button()
        self.preview_label.pack_forget()
        self.clip_info.configure(text="")
        self.properties.close()

        if hasattr(self, '_browser_frame') and self._browser_frame and self._browser_frame.winfo_exists():
            self._browser_frame.destroy()

        self._browser_frame = ctk.CTkFrame(self.preview_frame, fg_color="#050508", corner_radius=0)
        self._browser_frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(self._browser_frame, fg_color=C["card"], height=32)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="MEUS VIDEOS", font=("Segoe UI", 11, "bold"),
                     text_color=C["gold"]).pack(side="left", padx=10)
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=self._close_video_browser).pack(side="right", padx=6)
        ctk.CTkButton(header, text="+ Importar", width=80, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color=C["card"],
                      border_color=C["gold"], border_width=1,
                      text_color=C["gold"], hover_color=C["card_hover"],
                      command=self._import_video).pack(side="right", padx=4)
        ctk.CTkButton(header, text="Remover Inutilizados", width=130, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color="#2a0808",
                      text_color="#ff4444", hover_color="#3a1010",
                      border_color="#ff4444", border_width=1,
                      command=self._remove_unused_videos).pack(side="right", padx=2)

        scroll = ctk.CTkScrollableFrame(self._browser_frame, fg_color="#050508",
                                         scrollbar_button_color=C["gold"],
                                         scrollbar_button_hover_color="#ffd700")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        videos = sorted(OUTPUTS_DIR.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not videos:
            ctk.CTkLabel(scroll, text="Nenhum video encontrado.",
                         text_color=C["text3"], font=("Segoe UI", 12)).pack(expand=True, pady=40)
            return

        self._browser_thumb_refs = []
        for vpath in videos:
            self._build_video_card(scroll, vpath)

    def _build_video_card(self, parent, vpath):
        import time as _time
        from makevid.core.timeline import get_video_duration

        card = ctk.CTkFrame(parent, fg_color=C["panel"], border_color=C["border"],
                            border_width=1, corner_radius=6)
        card.pack(fill="x", pady=3, padx=2)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=6)

        # Thumbnail
        try:
            import cv2
            cap = cv2.VideoCapture(str(vpath))
            ret, frame = cap.read()
            cap.release()
            if ret:
                img = Image.fromarray(frame[:, :, ::-1])
                img.thumbnail((120, 68))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 68))
                self._browser_thumb_refs.append(ctk_img)
                ctk.CTkLabel(row, image=ctk_img, text="").pack(side="left", padx=(0, 8))
        except Exception:
            pass

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        name = vpath.stem[:30]
        name_var = ctk.StringVar(value=vpath.stem[:30])
        name_entry = ctk.CTkEntry(info, textvariable=name_var, fg_color="transparent",
                         border_color=C["border"], border_width=0, text_color=C["text"],
                         font=("Segoe UI", 10, "bold"), height=22)
        name_entry.pack(anchor="w", fill="x")
        name_entry.bind("<Return>", lambda e, p=vpath, v=name_var: self._rename_video(p, v.get()))
        name_entry.bind("<FocusOut>", lambda e, p=vpath, v=name_var: self._rename_video(p, v.get()))
        size_mb = vpath.stat().st_size / 1e6
        mtime = _time.strftime("%d/%m %H:%M", _time.localtime(vpath.stat().st_mtime))
        ctk.CTkLabel(info, text=f"{size_mb:.1f} MB | {mtime}", font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w")

        btns = ctk.CTkFrame(info, fg_color="transparent")
        btns.pack(anchor="w", pady=(4, 0))

        def add_to_timeline():
            dur = get_video_duration(vpath)
            if dur <= 0:
                dur = 5.0
            clip = self.app.project.add_clip(prompt=vpath.stem, position=len(self.app.project.clips))
            clip.video_path = str(vpath)
            clip.duration = dur
            clip.status = "done"
            self.app.project.save(PROJECTS_DIR)
            self.app.timeline.invalidate_thumbnail(clip.id)
            self.app.timeline.draw()

        ctk.CTkButton(btns, text="+ Timeline", width=80, height=22,
                      font=("Segoe UI", 9, "bold"), fg_color=C["gold"],
                      text_color="#0a0a0f", hover_color="#ffd700",
                      command=add_to_timeline).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btns, text="Deletar", width=60, height=22,
                      font=("Segoe UI", 9, "bold"), fg_color="#2a0808",
                      text_color="#ff4444", hover_color="#3a1010",
                      border_color="#ff4444", border_width=1,
                      command=lambda: [vpath.unlink(), card.destroy()]).pack(side="left")

    def _remove_unused_videos(self):
        """Remove videos nao usados na timeline + projetos orfaos e suas pastas."""
        import shutil
        from makevid.config import OUTPUTS_DIR, PROJECTS_DIR, AUDIO_DIR
        from pathlib import Path

        current_id = self.app.project.id
        removed_count = 0

        # 1. Remover videos e imagens nao usados do projeto atual
        used = set()
        for c in self.app.project.clips:
            if c.video_path:
                used.add(str(Path(c.video_path).resolve()))

        current_output = OUTPUTS_DIR / current_id
        if current_output.exists():
            for f in current_output.rglob("*"):
                if f.is_file() and f.suffix.lower() in ('.mp4', '.png', '.jpg', '.jpeg', '.webp', '.gif'):
                    if str(f.resolve()) not in used:
                        try:
                            f.unlink()
                            removed_count += 1
                        except Exception:
                            pass

        # 2. Remover projetos orfaos (que nao sao o atual)
        for proj_file in PROJECTS_DIR.glob("*.json"):
            proj_id = proj_file.stem
            if proj_id == current_id:
                continue
            # Remover JSON do projeto
            try:
                proj_file.unlink()
                removed_count += 1
            except Exception:
                pass
            # Remover pasta de outputs do projeto
            orphan_output = OUTPUTS_DIR / proj_id
            if orphan_output.exists():
                try:
                    shutil.rmtree(str(orphan_output))
                    removed_count += 1
                except Exception:
                    pass
            # Remover pasta de audio do projeto
            orphan_audio = AUDIO_DIR / proj_id
            if orphan_audio.exists():
                try:
                    shutil.rmtree(str(orphan_audio))
                    removed_count += 1
                except Exception:
                    pass

        # 3. Remover pastas de outputs orfas (sem projeto correspondente)
        if OUTPUTS_DIR.exists():
            for d in OUTPUTS_DIR.iterdir():
                if d.is_dir() and d.name != current_id:
                    try:
                        shutil.rmtree(str(d))
                        removed_count += 1
                    except Exception:
                        pass

        # Refresh
        self._close_video_browser()
        self.show_video_browser()

    def _import_video(self):
        """Importa video/imagem do PC para Meus Videos."""
        from tkinter import filedialog
        from makevid.config import OUTPUTS_DIR
        import shutil

        paths = filedialog.askopenfilenames(
            filetypes=[("Midia", "*.mp4 *.avi *.mov *.mkv *.png *.jpg *.jpeg *.webp")])
        for p in paths:
            from pathlib import Path
            src = Path(p)
            dest = OUTPUTS_DIR / self.app.project.id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                # Se imagem, converter pra MP4 estatico
                if src.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                    from makevid.core.video import frames_to_mp4
                    img = Image.open(str(src)).convert("RGB")
                    img_resized = img.resize(
                        (self.app.project.output_width, self.app.project.output_height), Image.LANCZOS)
                    fps = self.app.project.output_fps or 16
                    frames = [img_resized] * int(5 * fps)
                    dest = dest.with_suffix('.mp4')
                    frames_to_mp4(frames, dest, fps=fps)
                else:
                    shutil.copy2(str(src), str(dest))
        # Refresh
        self._close_video_browser()
        self.show_video_browser()

    def _rename_video(self, vpath, new_name):
        """Renomeia video no disco."""
        from pathlib import Path
        new_name = new_name.strip()
        if not new_name or new_name == vpath.stem:
            return
        new_path = vpath.parent / f"{new_name}{vpath.suffix}"
        if not new_path.exists():
            vpath.rename(new_path)
            # Atualizar referencia em clips
            for clip in self.app.project.clips:
                if clip.video_path == str(vpath):
                    clip.video_path = str(new_path)
            self.app.project.save(PROJECTS_DIR)

    def _close_video_browser(self):
        if hasattr(self, '_browser_frame') and self._browser_frame and self._browser_frame.winfo_exists():
            self._browser_frame.destroy()
            self._browser_frame = None
        self.preview_label.pack(expand=True)
        self.show_timeline_preview()

    # Compat aliases

    def show_audio_browser(self):
        """Mostra browser de audios no display (mesmo padrao de Meus Videos)."""
        import time as _time
        import wave
        from makevid.config import AUDIO_DIR
        from pathlib import Path

        if self.player.is_playing:
            self.player.stop()
        self._hide_play_button()
        self.preview_label.pack_forget()
        self.clip_info.configure(text="")
        self.properties.close()

        if hasattr(self, '_browser_frame') and self._browser_frame and self._browser_frame.winfo_exists():
            self._browser_frame.destroy()

        self._browser_frame = ctk.CTkFrame(self.preview_frame, fg_color="#050508", corner_radius=0)
        self._browser_frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(self._browser_frame, fg_color=C["card"], height=32)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="MEUS AUDIOS", font=("Segoe UI", 11, "bold"),
                     text_color=C["cyan"]).pack(side="left", padx=10)
        ctk.CTkButton(header, text="X", width=28, height=22, fg_color=C["card"],
                      text_color=C["text3"], hover_color="#3a1010", font=("Segoe UI", 10, "bold"),
                      command=self._close_video_browser).pack(side="right", padx=6)
        ctk.CTkButton(header, text="Remover Inutilizados", width=140, height=22,
                      font=("Segoe UI", 8, "bold"), fg_color="#2a0808",
                      text_color="#ff4444", hover_color="#3a1010",
                      border_color="#ff4444", border_width=1,
                      command=self._remove_unused_audios).pack(side="right", padx=2)

        scroll = ctk.CTkScrollableFrame(self._browser_frame, fg_color="#050508",
                                         scrollbar_button_color=C["cyan"],
                                         scrollbar_button_hover_color="#00ffee")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        audios = sorted(
            [f for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac") for f in AUDIO_DIR.rglob(ext)],
            key=lambda p: p.stat().st_mtime, reverse=True)

        if not audios:
            ctk.CTkLabel(scroll, text="Nenhum audio.\nGrave pelo painel Audio na timeline.",
                         text_color=C["text3"], font=("Segoe UI", 11)).pack(expand=True, pady=40)
            return

        for apath in audios:
            card = ctk.CTkFrame(scroll, fg_color=C["panel"], border_color=C["border"],
                                border_width=1, corner_radius=6)
            card.pack(fill="x", pady=3, padx=2)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=6)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            try:
                with wave.open(str(apath), "r") as wf:
                    dur = wf.getnframes() / wf.getframerate()
            except Exception:
                dur = 0

            ctk.CTkLabel(info, text=apath.stem[:25], font=("Segoe UI", 10, "bold"),
                         text_color=C["text"]).pack(anchor="w")
            size_kb = apath.stat().st_size / 1024
            mtime = _time.strftime("%d/%m %H:%M", _time.localtime(apath.stat().st_mtime))
            ctk.CTkLabel(info, text=f"{dur:.1f}s | {size_kb:.0f}KB | {mtime}",
                         font=("Consolas", 8), text_color=C["text3"]).pack(anchor="w")

            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right")

            def play_audio(p=apath):
                try:
                    import sounddevice as sd
                    import numpy as np
                    with wave.open(str(p), "r") as wf2:
                        frames = wf2.readframes(wf2.getnframes())
                        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                        sd.play(audio, samplerate=wf2.getframerate())
                except Exception:
                    pass

            def add_to_timeline(p=apath, d=dur):
                tl = self.app.timeline
                existing = self.app.project.get_track_items("audio")
                if existing:
                    last = max(existing, key=lambda i: i.start_time + i.duration)
                    start = last.start_time + last.duration
                else:
                    start = tl.playhead_pos
                self.app.project.add_track_item(
                    name=f"{p.stem} ({d:.1f}s)", track="audio",
                    start_time=start, duration=d, file_path=str(p))
                self.app.project.save(PROJECTS_DIR)
                tl.draw()

            ctk.CTkButton(btns, text="\u25b6", width=28, height=24,
                          font=("Segoe UI", 10), fg_color=C["card"],
                          border_color=C["cyan"], border_width=1,
                          text_color=C["cyan"], hover_color="#0a2a2a",
                          command=play_audio).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="+ Timeline", width=70, height=24,
                          font=("Segoe UI", 8, "bold"), fg_color=C["gold"],
                          text_color="#0a0a0f", hover_color="#ffd700",
                          command=add_to_timeline).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="X", width=24, height=24,
                          font=("Segoe UI", 9, "bold"), fg_color="#2a0808",
                          text_color="#ff4444", hover_color="#3a1010",
                          command=lambda p=apath, c=card: [p.unlink(), c.destroy()]).pack(side="left", padx=2)

    def _remove_unused_audios(self):
        """Remove audios que nao estao sendo usados em nenhuma track."""
        from makevid.config import AUDIO_DIR
        from pathlib import Path

        # Coletar todos os file_paths usados nas tracks
        used = set()
        for item in self.app.project.track_items:
            if item.file_path:
                used.add(str(Path(item.file_path).resolve()))

        # Remover todos os formatos de audio nao usados
        removed = 0
        audio_dir = AUDIO_DIR / self.app.project.id
        extensions = ("*.wav", "*.mp3", "*.ogg", "*.flac")
        if audio_dir.exists():
            for ext in extensions:
                for f in audio_dir.rglob(ext):
                    if str(f.resolve()) not in used:
                        try:
                            f.unlink()
                            removed += 1
                        except Exception:
                            pass
            # Remover subdiretorios vazios
            for d in sorted(audio_dir.rglob("*"), reverse=True):
                if d.is_dir():
                    try:
                        d.rmdir()  # so remove se vazio
                    except Exception:
                        pass

        # Tambem limpar pasta de audio de projetos orfaos
        if AUDIO_DIR.exists():
            for d in AUDIO_DIR.iterdir():
                if d.is_dir() and d.name != self.app.project.id:
                    import shutil
                    try:
                        shutil.rmtree(str(d))
                        removed += 1
                    except Exception:
                        pass

        # Refresh
        self._close_video_browser()
        self.show_audio_browser()
