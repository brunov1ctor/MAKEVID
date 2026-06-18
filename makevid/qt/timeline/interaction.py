"""Interaction Qt - Toda interação de mouse e teclado na timeline.

Porta 1:1 do makevid/ui/timeline/interaction.py para Qt.
"""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor, QFont
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem

from makevid.qt.timeline.clip_item import ClipGraphicsItem
from makevid.qt.timeline.track_item import TrackGraphicsItem


class SceneInteraction:
    """Gerencia toda interação do mouse com a timeline scene.

    Estado:
        _drag_mode: None | "playhead" | "clip_move" | "clip_trim_left" | "clip_trim_right"
                    | "item_move" | "item_trim_left" | "item_trim_right"
        _drag_target: clip ou track_item sendo arrastado
        _drag_start_x: posição X do mouse no início do drag
        _drag_orig: valor original (duration, position, start_time)
        _drag_orig_start: start_time original (para trim_left de items)
        _drag_group: lista de (item, offset) para mover grupo junto
    """

    def __init__(self, scene):
        self.scene = scene
        self.tl = scene.tl
        self._reset_drag()
        # Callbacks (setados pelo app.py)
        self.item_clicked = None  # fn(track_item)
        self.clip_clicked = None  # fn(clip)
        self.label_clicked = None  # fn(track_name)
        self.track_empty_clicked = None  # fn(track_name)
        # Estado de diamonds marcados
        self._marked_diamonds = set()

    def _reset_drag(self):
        self._drag_mode = None
        self._drag_target = None
        self._drag_start_x = 0
        self._drag_orig = 0
        self._drag_orig_start = 0
        self._drag_group = None

    # ============================================================
    # DOUBLE-CLICK
    # ============================================================

    def on_double_click(self, pos):
        """Double-click: clip=abre no SO, FX track=toggle all diamonds."""
        lbl_w = self.tl.LBL_W
        if pos.x() < lbl_w:
            return False

        # FX track: seleciona/deseleciona todos diamonds
        track_positions = self.scene._track_positions
        if "fx" in track_positions:
            ty, th = track_positions["fx"]
            if ty <= pos.y() <= ty + th:
                project = self.tl.project
                clips = sorted(project.clips, key=lambda c: c.position)
                all_ids = {f"diamond_{c.position}" for c in clips if c.position > 0}
                if self._marked_diamonds:
                    self._marked_diamonds.clear()
                else:
                    self._marked_diamonds = set(all_ids)
                self.tl.redraw()
                return True

        return False

    # ============================================================
    # STORYBOARD MARKER CLICK
    # ============================================================

    def on_storyboard_marker_click(self, pos):
        """Verifica se clicou em storyboard marker e copia prompt."""
        lbl_w = self.tl.LBL_W
        ruler_h = self.tl.RULER_H
        zoom = self.tl.zoom
        project = self.tl.project

        if pos.y() > ruler_h or pos.x() < lbl_w:
            return False

        scenes = project.world.scenes
        if not scenes:
            return False

        current_time = 0.0
        for i, scene in enumerate(scenes):
            dur = float(scene.get("duration", 5))
            x = lbl_w + int(current_time * zoom)
            if abs(pos.x() - x) < 12:
                # Copiar prompt para clipboard
                visual = scene.get("visual", "")
                camera = scene.get("camera", "")
                prompt = f"{visual}, {camera}" if camera else visual
                from PySide6.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                clipboard.setText(prompt)
                return True
            current_time += dur

        return False

    # ============================================================
    # CLICK
    # ============================================================

    def on_press(self, pos, button):
        """Chamado pelo scene.mousePressEvent."""
        lbl_w = self.tl.LBL_W
        ruler_h = self.tl.RULER_H
        zoom = self.tl.zoom

        self._reset_drag()

        # Right-click = remover item
        if button == Qt.RightButton:
            self._on_right_click(pos)
            return True

        # Split mode: click divide clip ou item
        if getattr(self.tl, '_split_mode', False):
            self._do_split_at(pos)
            return True

        # Audio split mode: click divide track item
        if getattr(self.tl, '_audio_split_mode', None):
            self._do_audio_split_at(pos)
            return True

        # Click em labels laterais
        if pos.x() < lbl_w:
            if self.label_clicked:
                # Determinar qual track pelo Y
                track_positions = self.scene._track_positions
                for name, (ty, th) in track_positions.items():
                    if ty <= pos.y() <= ty + th:
                        self.label_clicked(name)
                        return True
            return False

        t = (pos.x() - lbl_w) / zoom

        # Click na ruler = check storyboard markers primeiro, depois move playhead
        if pos.y() < ruler_h:
            if self.on_storyboard_marker_click(pos):
                return True
            self.tl.set_playhead(max(0, t))
            self._drag_mode = "playhead"
            self._drag_start_x = pos.x()
            return True

        # Verificar se clicou em item interativo
        item = self.scene.itemAt(pos, self.tl._view.transform())
        # Navegar hierarquia para pegar parent item
        while item and item.parentItem():
            item = item.parentItem()
        # Ignorar items de background (nao-interativos)
        if item and not isinstance(item, (ClipGraphicsItem, TrackGraphicsItem)) and not hasattr(item, "_position") and not hasattr(item, "track_item"):
            item = None

        # Track item (audio/fx/voice/sfx/music)
        if item and (isinstance(item, TrackGraphicsItem) or hasattr(item, "track_item")):
            ti = item.track_item
            # Detectar zona: borda esquerda, borda direita, ou corpo
            if hasattr(item, "rect") and callable(getattr(item, "rect", None)):
                local_x = pos.x() - item.rect().x()
                item_w = item.rect().width()
            else:
                local_x = pos.x() - item.boundingRect().x()
                item_w = item.boundingRect().width()

            if local_x <= 6:
                self._drag_mode = "item_trim_left"
                self._drag_target = ti
                self._drag_start_x = pos.x()
                self._drag_orig = ti.duration
                self._drag_orig_start = ti.start_time
            elif (item_w - local_x) <= 6:
                self._drag_mode = "item_trim_right"
                self._drag_target = ti
                self._drag_start_x = pos.x()
                self._drag_orig = ti.duration
            else:
                self._drag_mode = "item_move"
                self._drag_target = ti
                self._drag_start_x = pos.x()
                self._drag_orig = ti.start_time
                # Capturar grupo (mesmo clip_index)
                self._drag_group = self._get_item_group(ti)
            return True

        # Clip de video
        if item and isinstance(item, ClipGraphicsItem):
            clip = item.clip
            local_x = pos.x() - item.rect().x()
            item_w = item.rect().width()

            if local_x <= 10:
                self._drag_mode = "clip_trim_left"
                self._drag_target = clip
                self._drag_start_x = pos.x()
                self._drag_orig = clip.duration
            elif (item_w - local_x) <= 10:
                self._drag_mode = "clip_trim_right"
                self._drag_target = clip
                self._drag_start_x = pos.x()
                self._drag_orig = clip.duration
            else:
                self._drag_mode = "clip_move"
                self._drag_target = clip
                self._drag_start_x = pos.x()
                self._drag_orig = clip.position
            return True

        # FX diamond
        if item and hasattr(item, '_position'):
            diamond_id = f"diamond_{item._position}"
            if diamond_id in self._marked_diamonds:
                self._marked_diamonds.discard(diamond_id)
            else:
                self._marked_diamonds.add(diamond_id)
            self.tl.redraw()
            return True

        # Click em area vazia de track = abrir menu da track
        # Mas primeiro verificar se ha item na posicao temporal (fallback)
        track_positions = self.scene._track_positions
        for name, (ty, th) in track_positions.items():
            if ty <= pos.y() <= ty + th:
                # Buscar item por tempo (fallback se itemAt falhou)
                found_item = self._find_item_at_time(t, name)
                if found_item:
                    self._drag_mode = "item_move"
                    self._drag_target = found_item
                    self._drag_start_x = pos.x()
                    self._drag_orig = found_item.start_time
                    self._drag_group = self._get_item_group(found_item)
                    return True
                if self.track_empty_clicked:
                    self.track_empty_clicked(name)
                return True

        # Area vazia fora de tracks = mover playhead
        self.tl.set_playhead(max(0, t))
        self._drag_mode = "playhead"
        self._drag_start_x = pos.x()
        return True

    # ============================================================
    # DRAG
    # ============================================================

    def on_move(self, pos):
        """Chamado pelo scene.mouseMoveEvent."""
        if not self._drag_mode:
            return False

        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        dx = pos.x() - self._drag_start_x

        if self._drag_mode == "playhead":
            t = max(0, (pos.x() - lbl_w) / zoom)
            self.tl.set_playhead(t)
            return True

        elif self._drag_mode == "clip_move":
            # Reordenar clips por deslocamento
            moved = int(dx / 60)
            if moved != 0:
                clip = self._drag_target
                project = self.tl.project
                new_pos = max(0, min(len(project.clips) - 1, int(self._drag_orig) + moved))
                if new_pos != clip.position:
                    project.move_clip(clip.id, new_pos)
                    self._drag_start_x = pos.x()
                    self._drag_orig = new_pos
                    self.tl.redraw()
            return True

        elif self._drag_mode == "clip_trim_right":
            dt = dx / zoom
            clip = self._drag_target
            new_dur = max(1.0, self._drag_orig + dt)
            trim_amount = self._drag_orig - new_dur
            clip.duration = new_dur
            # Trim preview visual (hachura)
            if trim_amount > 0:
                self._show_trim_preview(clip, "right", trim_amount)
            else:
                self._remove_trim_preview()
            self.tl.redraw()
            return True

        elif self._drag_mode == "clip_trim_left":
            dt = dx / zoom
            clip = self._drag_target
            trim = max(0, min(self._drag_orig - 1.0, dt))
            clip.duration = max(1.0, self._drag_orig - trim)
            # Trim preview visual
            if trim > 0:
                self._show_trim_preview(clip, "left", trim)
            else:
                self._remove_trim_preview()
            self.tl.redraw()
            return True

        elif self._drag_mode == "item_move":
            dt = dx / zoom
            new_start = max(0, self._drag_orig + dt)
            # Mover grupo inteiro
            if self._drag_group:
                for gi, offset in self._drag_group:
                    gi.start_time = max(0, round(new_start + offset, 2))
            else:
                self._drag_target.start_time = round(new_start, 2)

            # Drag guide visual
            self.tl.redraw()
            self._update_drag_guide(new_start)
            return True

        elif self._drag_mode == "item_trim_right":
            dt = dx / zoom
            ti = self._drag_target
            max_dur = self._get_wav_duration(ti) or self._drag_orig + 10
            ti.duration = max(0.5, min(max_dur, self._drag_orig + dt))
            self.tl.redraw()
            return True

        elif self._drag_mode == "item_trim_left":
            dt = dx / zoom
            ti = self._drag_target
            trim = max(0, min(self._drag_orig - 0.5, dt))
            ti.start_time = round(self._drag_orig_start + trim, 2)
            ti.duration = max(0.5, self._drag_orig - trim)
            self.tl.redraw()
            return True

        return False

    # ============================================================
    # RELEASE
    # ============================================================

    def on_release(self, pos):
        """Chamado pelo scene.mouseReleaseEvent."""
        if not self._drag_mode:
            return False

        dx_total = abs(pos.x() - self._drag_start_x)

        # Salvar projeto se houve mudanca real (movimento)
        if self._drag_mode != "playhead" and dx_total >= 3:
            from makevid.config import PROJECTS_DIR
            self.tl.project.save(PROJECTS_DIR)

        # Click sem movimento em item_move = abrir editor (futuro)
        if self._drag_mode == "item_move" and dx_total < 3:
            if self.item_clicked and self._drag_target:
                self.item_clicked(self._drag_target)
            # Marcar como selecionado para Delete
            self.tl._selected_track_item_id = self._drag_target.id if self._drag_target else None

        # Click sem movimento em clip = selecionar
        if self._drag_mode == "clip_move" and dx_total < 3:
            if self.clip_clicked and self._drag_target:
                self.clip_clicked(self._drag_target)

        self._remove_drag_guide()
        self._remove_trim_preview()
        self._reset_drag()
        self.tl.redraw()
        return True

    # ============================================================
    # TRIM PREVIEW (hachura vermelha)
    # ============================================================

    def _show_trim_preview(self, clip, side, amount):
        """Mostra hachura vermelha na area que sera cortada."""
        self._remove_trim_preview()
        scene = self.scene
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        track_positions = scene._track_positions
        if "video" not in track_positions:
            return
        vy, vh = track_positions["video"]

        # Calcular posicao do clip na timeline
        project = self.tl.project
        current = 0.0
        for c in sorted(project.clips, key=lambda c: c.position):
            if c.id == clip.id:
                break
            current += c.duration

        clip_x1 = lbl_w + int(current * zoom)
        clip_x2 = clip_x1 + int(clip.duration * zoom)
        trim_px = int(amount * zoom)

        if trim_px <= 0:
            return

        if side == "right":
            tx1 = clip_x2
            tx2 = clip_x2 + trim_px
        else:
            tx1 = clip_x1 - trim_px
            tx2 = clip_x1

        # Fundo semi-transparente
        from PySide6.QtGui import QBrush
        overlay = QGraphicsRectItem(tx1, vy + 2, tx2 - tx1, vh - 4)
        overlay.setPen(QPen(Qt.NoPen))
        overlay.setBrush(QBrush(QColor(180, 0, 0, 80)))
        overlay.setZValue(90)
        overlay._is_trim_preview = True
        scene.addItem(overlay)

        # Linhas diagonais (hachura)
        from PySide6.QtWidgets import QGraphicsLineItem as LI
        for hx in range(int(tx1), int(tx2), 8):
            line = LI(hx, vy + 2, hx + 12, vy + vh - 2)
            line.setPen(QPen(QColor("#ff3333"), 1))
            line.setZValue(91)
            line._is_trim_preview = True
            scene.addItem(line)

        # Linha de corte
        cut_x = tx1 if side == "right" else tx2
        cut_line = QGraphicsLineItem(cut_x, vy + 2, cut_x, vy + vh - 2)
        cut_line.setPen(QPen(QColor("#ff3333"), 2, Qt.DashLine))
        cut_line.setZValue(92)
        cut_line._is_trim_preview = True
        scene.addItem(cut_line)

        # Label com quantidade
        label = QGraphicsTextItem(f"-{amount:.1f}s")
        label.setFont(QFont("Consolas", 9, QFont.Bold))
        label.setDefaultTextColor(QColor("#ff6666"))
        label.setPos(cut_x + 4 if side == "right" else cut_x - 40, vy + vh // 2 - 8)
        label.setZValue(93)
        label._is_trim_preview = True
        scene.addItem(label)

    def _remove_trim_preview(self):
        """Remove overlay de trim."""
        scene = self.scene
        for item in list(scene.items()):
            if getattr(item, '_is_trim_preview', False):
                scene.removeItem(item)

    # ============================================================
    # RIGHT-CLICK (remove item)
    # ============================================================

    def _on_right_click(self, pos):
        """Right-click desabilitado - usar Delete para remover."""
        pass

    # ============================================================
    # KEYBOARD
    # ============================================================

    def on_key(self, key):
        """Chamado para teclas."""
        if key == Qt.Key_Space:
            # Futuro: play/pause
            pass
        elif key == Qt.Key_Delete:
            # Futuro: delete selecionado
            pass

    # ============================================================
    # SPLIT MODE
    # ============================================================

    def _do_split_at(self, pos):
        """Split mode: divide clip de video na posicao clicada."""
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        project = self.tl.project

        if pos.x() < lbl_w:
            self.tl._exit_split_mode()
            return

        t = (pos.x() - lbl_w) / zoom

        # Encontrar clip na posicao
        current_time = 0.0
        clips = sorted(project.clips, key=lambda c: c.position)
        for clip in clips:
            end = current_time + clip.duration
            if current_time <= t <= end:
                split_point = t - current_time
                if split_point < 0.5 or split_point > clip.duration - 0.5:
                    break  # muito perto da borda
                # Dividir
                new_clip = project.add_clip(prompt=clip.prompt, position=clip.position + 1)
                new_clip.duration = round(clip.duration - split_point, 1)
                new_clip.seed = clip.seed
                new_clip.status = clip.status
                new_clip.video_path = clip.video_path
                clip.duration = round(split_point, 1)
                from makevid.config import PROJECTS_DIR
                project.save(PROJECTS_DIR)
                break
            current_time = end

        self.tl._exit_split_mode()
        self.tl.redraw()

    def _do_audio_split_at(self, pos):
        """Audio split mode: divide track items na posicao clicada."""
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        project = self.tl.project
        track_name = getattr(self.tl, '_audio_split_mode', None)

        if not track_name or pos.x() < lbl_w:
            self.tl._exit_split_mode()
            return

        t = (pos.x() - lbl_w) / zoom

        # Verificar se pos.y esta na track correta
        track_positions = self.scene._track_positions
        if track_name in track_positions:
            ty, th = track_positions[track_name]
            if not (ty <= pos.y() <= ty + th):
                self.tl._exit_split_mode()
                return

        # Encontrar items sobrepostos
        items = [i for i in project.get_track_items(track_name)
                 if i.start_time < t < i.start_time + i.duration]

        for item in items:
            cut_point = t - item.start_time
            if cut_point <= 0.1 or cut_point >= item.duration - 0.1:
                continue
            new_dur = item.duration - cut_point
            project.add_track_item(
                name=item.name, track=item.track,
                start_time=t, duration=new_dur,
                file_path=item.file_path, params=dict(item.params))
            item.duration = cut_point

        from makevid.config import PROJECTS_DIR
        project.save(PROJECTS_DIR)
        self.tl._exit_split_mode()
        self.tl.redraw()

    # ============================================================
    # HELPERS
    # ============================================================

    def _get_item_group(self, item):
        """Retorna lista de (track_item, offset_relativo) do grupo."""
        project = self.tl.project
        if item.clip_index >= 0:
            group_items = [i for i in project.get_track_items(item.track)
                          if i.clip_index == item.clip_index]
        else:
            group_items = [i for i in project.get_track_items(item.track)
                          if abs(i.start_time - item.start_time) < 0.05]
        return [(i, i.start_time - item.start_time) for i in group_items]

    def _find_item_at_time(self, t, track_name):
        """Encontra item na posicao temporal t (fallback quando itemAt falha)."""
        candidates = [i for i in self.tl.project.get_track_items(track_name)
                      if i.start_time <= t <= i.start_time + i.duration]
        if not candidates:
            return None
        return min(candidates, key=lambda i: abs((i.start_time + i.duration / 2) - t))

    def _get_wav_duration(self, item):
        """Duração real do arquivo WAV."""
        from pathlib import Path
        if not item.file_path or not Path(item.file_path).exists():
            return 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            return get_audio_duration(item.file_path)
        except Exception:
            return 0

    def _update_drag_guide(self, time_val):
        """Atualiza linha guia + badge durante drag."""
        self._remove_drag_guide()
        scene = self.scene
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        guide_x = lbl_w + int(time_val * zoom)
        scene_h = scene.sceneRect().height()

        # Linha pontilhada
        line = QGraphicsLineItem(guide_x, self.tl.RULER_H, guide_x, scene_h)
        line.setPen(QPen(QColor("#00ccff"), 1, Qt.DashLine))
        line.setZValue(50)
        line._is_drag_guide = True
        scene.addItem(line)

        # Badge
        m, s = int(time_val) // 60, time_val % 60
        txt_str = f"{m:02d}:{s:04.1f}"

        bg = QGraphicsRectItem(guide_x - 26, 1, 52, 18)
        bg.setPen(QPen(QColor("#005577")))
        bg.setBrush(QColor("#00ccff"))
        bg.setZValue(51)
        bg._is_drag_guide = True
        scene.addItem(bg)

        txt = QGraphicsTextItem(txt_str)
        txt.setFont(QFont("Consolas", 8, QFont.Bold))
        txt.setDefaultTextColor(QColor("#0a0a0f"))
        txt.setPos(guide_x - 22, -1)
        txt.setZValue(52)
        txt._is_drag_guide = True
        scene.addItem(txt)

    def _remove_drag_guide(self):
        """Remove guia visual."""
        scene = self.scene
        for item in list(scene.items()):
            if getattr(item, '_is_drag_guide', False):
                scene.removeItem(item)
