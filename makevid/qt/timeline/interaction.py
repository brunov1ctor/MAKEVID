"""Interaction - Toda interação de mouse na timeline scene."""

import logging
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor, QFont
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem
import shiboken6

from makevid.qt.timeline.clip_item import ClipGraphicsItem, Z_OVERLAY, Z_CLIP
from makevid.qt.timeline.track_item import TrackGraphicsItem
from makevid.qt.timeline.interaction_state import DragState
from makevid.qt.theme import C

_log = logging.getLogger("timeline")


class SceneInteraction:

    def __init__(self, scene):
        self.scene = scene
        self.tl = scene.tl
        self._drag = DragState()
        self._reset_drag()
        self.item_clicked = None
        self.item_moved = None
        self.clip_clicked = None
        self.label_clicked = None
        self.track_empty_clicked = None
        self._marked_diamonds = set()
        self._last_diamond_toggle = None

    # Compatibilidade: propriedades delegam ao DragState.
    @property
    def _drag_mode(self): return self._drag.mode
    @_drag_mode.setter
    def _drag_mode(self, v): self._drag.mode = v

    @property
    def _drag_target(self): return self._drag.target
    @_drag_target.setter
    def _drag_target(self, v): self._drag.target = v

    @property
    def _drag_start_x(self): return self._drag.start_x
    @_drag_start_x.setter
    def _drag_start_x(self, v): self._drag.start_x = v

    @property
    def _drag_orig(self): return self._drag.orig
    @_drag_orig.setter
    def _drag_orig(self, v): self._drag.orig = v

    @property
    def _drag_orig_start(self): return self._drag.orig_start
    @_drag_orig_start.setter
    def _drag_orig_start(self, v): self._drag.orig_start = v

    @property
    def _drag_group(self): return self._drag.group
    @_drag_group.setter
    def _drag_group(self, v): self._drag.group = v

    @property
    def _drag_ghost_pos(self): return self._drag.ghost_pos
    @_drag_ghost_pos.setter
    def _drag_ghost_pos(self, v): self._drag.ghost_pos = v

    @property
    def _drag_clip_item(self): return self._drag.clip_item
    @_drag_clip_item.setter
    def _drag_clip_item(self, v): self._drag.clip_item = v

    @property
    def _drag_clip_orig_x(self): return self._drag.clip_orig_x
    @_drag_clip_orig_x.setter
    def _drag_clip_orig_x(self, v): self._drag.clip_orig_x = v

    def _reset_drag(self):
        self._drag.reset()

    def _is_valid(self, obj):
        try:
            return obj is not None and shiboken6.isValid(obj)
        except Exception:
            return False

    # ── double-click ──────────────────────────────────────────────────────────

    def on_double_click(self, pos):
        tp = self.scene._track_pos

        if "fx" in tp:
            ty, th = tp["fx"]
            if ty <= pos.y() <= ty + th:
                project = self.tl.project
                all_ids = {f"diamond_{c.position}" for c in project.clips if c.position > 0}
                if all_ids:
                    self._marked_diamonds = set() if self._marked_diamonds else set(all_ids)
                    self.tl.rebuild_scene()
                    return True

        if "video" in tp:
            vy, vh = tp["video"]
            if vy <= pos.y() <= vy + vh:
                item = self._item_at(pos)
                if isinstance(item, ClipGraphicsItem) and item.clip.video_path:
                    if Path(item.clip.video_path).exists():
                        import os
                        os.startfile(item.clip.video_path)
                        return True

        return False

    # ── press ─────────────────────────────────────────────────────────────────

    def on_press(self, pos, button):
        ruler_h = self.tl.RULER_H
        zoom = self.tl.zoom

        self._reset_drag()

        if button == Qt.RightButton:
            return True
        if button != Qt.LeftButton:
            return False

        if getattr(self.tl, '_split_mode', False):
            self._do_split_at(pos)
            return True

        if getattr(self.tl, '_audio_split_mode', None):
            self._do_audio_split_at(pos)
            return True

        # Ruler → playhead
        if pos.y() < ruler_h:
            if self._check_storyboard_click(pos):
                return True
            if self.tl._selected_clip_id is not None:
                self.tl._selected_clip_id = None
                self.tl.refresh_visual_state()
            t = max(0, pos.x() / zoom)
            self.tl.set_playhead(t)
            self._drag_mode = "playhead"
            self._drag_start_x = pos.x()
            return True

        # Identifica a track sob o clique
        hit_track = None
        for name in self.scene._track_layers:
            if self.scene._track_layer_contains(name, pos):
                hit_track = name
                break

        if hit_track is None:
            if self.tl._selected_clip_id is not None:
                self.tl._selected_clip_id = None
                self.tl.refresh_visual_state()
            return False

        name = hit_track

        if name == "video":
            item = self._item_at(pos)
            if isinstance(item, ClipGraphicsItem):
                if not self._is_valid(item):
                    return False
                clip = item.clip
                local_x = pos.x() - item.pos().x()
                iw = item._w

                if local_x <= 10:
                    self._drag_mode = "clip_trim_left"
                    self._drag_orig = clip.duration
                elif (iw - local_x) <= 10:
                    self._drag_mode = "clip_trim_right"
                    self._drag_orig = clip.duration
                else:
                    self._drag_mode = "clip_move"
                    self._drag_orig = clip.position
                    self._drag_clip_orig_x = item.pos().x()
                    self._drag_clip_item = item
                    item._selected = True
                    item.setZValue(Z_OVERLAY)
                    item.update()

                self._drag_target = clip
                self._drag_start_x = pos.x()
                self.tl.set_active_track("video")
                # Limpa seleção de track item
                if self.tl._selected_track_item_id is not None:
                    self.tl._selected_track_item_id = None
                    self.tl.refresh_visual_state()
                return True
            # Clicou em área vazia da track de vídeo — deseleciona clip
            if self.tl._selected_clip_id is not None:
                self.tl._selected_clip_id = None
                self.tl.refresh_visual_state()
            return False

        if name == "fx":
            item = self._item_at(pos)
            if item and hasattr(item, '_position'):
                did = f"diamond_{item._position}"
                was = did in self._marked_diamonds
                if was:
                    self._marked_diamonds.discard(did)
                else:
                    self._marked_diamonds.add(did)
                self._last_diamond_toggle = (did, was)
                self.tl.rebuild_scene()
                return True

        gi = self._track_item_at(pos)
        if gi is not None:
            self.tl.set_active_track(name)
            # Limpa seleção de clip
            if self.tl._selected_clip_id is not None:
                self.tl._selected_clip_id = None
                self.tl.refresh_visual_state()
            found = gi.track_item
            ix1 = int(found.start_time * zoom)
            iw = int(found.duration * zoom)
            local_x = pos.x() - ix1
            if local_x <= 6:
                self._drag_mode = "item_trim_left"
                self._drag_orig = found.duration
                self._drag_orig_start = found.start_time
                self._drag_orig_file_offset = float(getattr(found, 'file_offset', 0.0))
            elif (iw - local_x) <= 6:
                self._drag_mode = "item_trim_right"
                self._drag_orig = found.duration
            else:
                self._drag_mode = "item_move"
                self._drag_orig = found.start_time
                self._drag_group = self._get_item_group(found)
            self._drag_target = found
            self._drag_start_x = pos.x()
            return True

        self.tl.set_active_track(name)
        # Clicou em área vazia de outra track — deseleciona tudo
        if self.tl._selected_clip_id is not None or self.tl._selected_track_item_id is not None:
            self.tl._selected_clip_id = None
            self.tl._selected_track_item_id = None
            self.tl.refresh_visual_state()
        cb = self.track_empty_clicked or self.label_clicked
        if cb:
            cb(name)
        return True

    # ── move ──────────────────────────────────────────────────────────────────

    def on_move(self, pos, buttons=Qt.NoButton):
        if buttons == Qt.NoButton and self._drag_mode in {
            "item_move", "item_trim_left", "item_trim_right",
            "clip_move", "clip_trim_left", "clip_trim_right", "playhead"
        }:
            self._cancel_stale_drag()
            return False

        if not self._drag_mode:
            return False

        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        dx = pos.x() - self._drag_start_x
        dt = dx / zoom

        if self._drag_mode == "playhead":
            self.tl.set_playhead(max(0, pos.x() / zoom))
            return True

        if self._drag_mode == "clip_move":
            if not self._is_valid(self._drag_clip_item):
                self._cancel_stale_drag(redraw=False)
                return False
            # Mover apenas o item visual — sem rebuild
            new_x = self._drag_clip_orig_x + dx
            self._drag_clip_item.setPos(new_x, self._drag_clip_item.pos().y())
            self._drag_ghost_pos = self._clip_drop_index(pos, self._drag_clip_item)
            return True

        if self._drag_mode == "clip_trim_right":
            self._drag_target.duration = max(1.0, self._drag_orig + dt)
            self.tl.rebuild_scene()
            return True

        if self._drag_mode == "clip_trim_left":
            trim = max(0.0, min(self._drag_orig - 1.0, dt))
            self._drag_target.duration = max(1.0, self._drag_orig - trim)
            self.tl.rebuild_scene()
            return True

        if self._drag_mode == "item_move":
            new_start = max(0.0, self._drag_orig + dt)
            if self._drag_group:
                for gi, offset in self._drag_group:
                    gi.start_time = max(0.0, round(new_start + offset, 2))
            else:
                self._drag_target.start_time = round(new_start, 2)
            self.tl.rebuild_scene()
            self._update_drag_guide(new_start)
            return True

        if self._drag_mode == "item_trim_right":
            max_dur = self._get_wav_duration(self._drag_target) or self._drag_orig + 60
            self._drag_target.duration = max(0.5, min(max_dur, self._drag_orig + dt))
            self.tl.rebuild_scene()
            return True

        if self._drag_mode == "item_trim_left":
            trim = max(0.0, min(self._drag_orig - 0.5, dt))
            self._drag_target.start_time = round(self._drag_orig_start + trim, 3)
            self._drag_target.file_offset = round(self._drag_orig_file_offset + trim, 3)
            self._drag_target.duration = max(0.5, round(self._drag_orig - trim, 3))
            self.tl.rebuild_scene()
            return True

        return False

    def _cancel_stale_drag(self, redraw=True):
        if self._drag_mode == "item_move" and self._drag_target:
            if self._drag_group:
                for gi, offset in self._drag_group:
                    gi.start_time = max(0.0, round(self._drag_orig + offset, 2))
            else:
                self._drag_target.start_time = max(0.0, round(self._drag_orig, 2))

        elif self._drag_mode == "item_trim_right" and self._drag_target:
            self._drag_target.duration = max(0.5, float(self._drag_orig))

        elif self._drag_mode == "item_trim_left" and self._drag_target:
            self._drag_target.start_time = max(0.0, round(self._drag_orig_start, 3))
            self._drag_target.file_offset = round(getattr(self, '_drag_orig_file_offset', 0.0), 3)
            self._drag_target.duration = max(0.5, float(self._drag_orig))

        elif self._drag_mode in ("clip_trim_left", "clip_trim_right") and self._drag_target:
            self._drag_target.duration = max(1.0, float(self._drag_orig))

        if self._drag_mode == "clip_move" and self._is_valid(self._drag_clip_item):
            self._drag_clip_item.setPos(self._drag_clip_orig_x, self._drag_clip_item.pos().y())
            self._drag_clip_item._selected = False
            self._drag_clip_item.setZValue(Z_CLIP)
            self._drag_clip_item.update()

        self._remove_drag_guide()
        self._reset_drag()
        if redraw:
            self.tl.rebuild_scene()

    # ── release ───────────────────────────────────────────────────────────────

    def on_release(self, pos):
        if not self._drag_mode:
            return False

        moved = abs(pos.x() - self._drag_start_x) >= 3

        if self._drag_mode == "item_move":
            if not moved:
                item_id = getattr(self._drag_target, 'id', None)
                self.tl._selected_clip_id = None
                self.tl._selected_track_item_id = item_id
                self.scene.select_track_item(item_id)
                if self.item_clicked and self._drag_target:
                    self.item_clicked(self._drag_target)
                self._remove_drag_guide()
                self._reset_drag()
                return True
            else:
                self.tl._selected_clip_id = None
                self.tl._selected_track_item_id = getattr(self._drag_target, 'id', None)
                self._save()
                if self.item_moved and self._drag_target:
                    self.item_moved(self._drag_target)

        elif self._drag_mode in ("item_trim_left", "item_trim_right"):
            if moved:
                self._save()
                if self.item_moved and self._drag_target:
                    self.item_moved(self._drag_target)

        elif self._drag_mode == "clip_move":
            if not moved:
                self.tl._selected_track_item_id = None
                self.tl._selected_clip_id = getattr(self._drag_target, 'id', None)
                if self.clip_clicked and self._drag_target:
                    self.clip_clicked(self._drag_target)
            else:
                self.tl._selected_track_item_id = None
                clip = self._drag_target
                orig_pos = int(self._drag_orig)
                new_pos = self._drag_ghost_pos if self._drag_ghost_pos is not None else orig_pos
                if new_pos != orig_pos:
                    self.tl.project.move_clip(clip.id, new_pos)
                    self._save()
                else:
                    self.tl._selected_clip_id = getattr(self._drag_target, 'id', None)

                if self._drag_ghost_pos is None:
                    self.tl._selected_clip_id = getattr(self._drag_target, 'id', None)

            # Restaura estado visual — rebuild vai reposicionar corretamente
            if self._is_valid(self._drag_clip_item):
                self._drag_clip_item.setZValue(Z_CLIP)
                self._drag_clip_item._selected = False

        elif self._drag_mode in ("clip_trim_left", "clip_trim_right"):
            if moved:
                self._save()

        self._remove_drag_guide()
        self._reset_drag()
        self.tl.rebuild_scene()
        return True

    def _clip_drop_index(self, pos, drag_item):
        item = self._item_at(pos)
        if not isinstance(item, ClipGraphicsItem):
            return None
        if item is drag_item:
            return int(getattr(item.clip, 'position', 0))

        clips = sorted(self.tl.project.clips, key=lambda c: c.position)
        target_pos = next((i for i, c in enumerate(clips) if c.id == item.clip.id), None)
        if target_pos is None:
            return None

        center_x = item.pos().x() + (item._w / 2)
        return target_pos if pos.x() < center_x else target_pos + 1

    # ── split ─────────────────────────────────────────────────────────────────

    def _do_split_at(self, pos):
        zoom = self.tl.zoom
        project = self.tl.project

        t = pos.x() / zoom
        cur = 0.0
        for clip in sorted(project.clips, key=lambda c: c.position):
            end = cur + clip.duration
            if cur <= t <= end:
                sp = t - cur
                if 0.5 <= sp <= clip.duration - 0.5:
                    new_clip = project.add_clip(prompt=clip.prompt, position=clip.position + 1)
                    new_clip.duration = round(clip.duration - sp, 1)
                    new_clip.seed = clip.seed
                    new_clip.status = clip.status
                    new_clip.video_path = clip.video_path
                    clip.duration = round(sp, 1)
                    self._save()
                break
            cur = end

        self.tl._exit_split_mode()
        self.tl.rebuild_scene()

    def _do_audio_split_at(self, pos):
        zoom = self.tl.zoom
        project = self.tl.project
        track_name = getattr(self.tl, '_audio_split_mode', None)

        if not track_name:
            self.tl._exit_split_mode()
            return

        t = pos.x() / zoom
        tp = self.scene._track_pos
        if track_name in tp:
            ty, th = tp[track_name]
            if not (ty <= pos.y() <= ty + th):
                self.tl._exit_split_mode()
                return

        for item in project.get_track_items(track_name):
            if item.start_time < t < item.start_time + item.duration:
                cut = t - item.start_time
                if 0.1 < cut < item.duration - 0.1:
                    project.add_track_item(
                        name=item.name, track=item.track,
                        start_time=t, duration=item.duration - cut,
                        file_path=item.file_path, params=dict(item.params))
                    item.duration = cut

        self._save()
        self.tl._exit_split_mode()
        self.tl.rebuild_scene()

    # ── storyboard ────────────────────────────────────────────────────────────

    def _check_storyboard_click(self, pos):
        zoom = self.tl.zoom
        project = self.tl.project

        if not getattr(project, '_storyboard_applied', False):
            return False

        scenes = getattr(project.world, 'scenes', [])
        cur = 0.0
        for scene in scenes:
            dur = float(scene.get("duration", 5))
            x = int(cur * zoom)
            if abs(pos.x() - x) < 12:
                visual = scene.get("visual", "")
                camera = scene.get("camera", "")
                prompt = f"{visual}, {camera}" if camera else visual
                from PySide6.QtWidgets import QApplication
                QApplication.clipboard().setText(prompt)
                return True
            cur += dur
        return False

    # ── diamond undo ──────────────────────────────────────────────────────────

    def _undo_last_diamond_toggle(self):
        if not self._last_diamond_toggle:
            return
        did, was = self._last_diamond_toggle
        if was:
            self._marked_diamonds.add(did)
        else:
            self._marked_diamonds.discard(did)
        self._last_diamond_toggle = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _item_at(self, pos):
        item = self.scene.itemAt(pos, self.tl._view.transform())
        while item and item.parentItem():
            item = item.parentItem()
        return item

    def _track_item_at(self, pos):
        for tid, gi in self.scene._track_items.items():
            ix = gi.pos().x()
            iy = gi.pos().y()
            if ix <= pos.x() <= ix + gi._w and iy <= pos.y() <= iy + gi._h:
                return gi
        return None

    def _find_item_at_time(self, t, track_name):
        candidates = [i for i in self.tl.project.get_track_items(track_name)
                      if i.start_time <= t <= i.start_time + i.duration]
        if not candidates:
            return None
        return min(candidates, key=lambda i: abs((i.start_time + i.duration / 2) - t))

    def _get_item_group(self, item):
        if item.clip_index < 0:
            return [(item, 0.0)]
        group = [i for i in self.tl.project.get_track_items(item.track)
                 if i.clip_index == item.clip_index]
        return [(i, i.start_time - item.start_time) for i in group]

    def _get_wav_duration(self, item):
        if not item.file_path or not Path(item.file_path).exists():
            return 0
        try:
            from makevid.core.audio_utils import get_audio_duration
            return get_audio_duration(item.file_path)
        except Exception:
            return 0

    def _save(self):
        from makevid.config import PROJECTS_DIR
        self.tl.project.save(PROJECTS_DIR)

    def _update_drag_guide(self, time_val):
        self._remove_drag_guide()
        zoom = self.tl.zoom
        gx = int(time_val * zoom)
        sh = self.scene.sceneRect().height()

        line = QGraphicsLineItem(gx, self.tl.RULER_H, gx, sh)
        line.setPen(QPen(QColor("#00ccff"), 1, Qt.DashLine))
        line.setZValue(Z_OVERLAY + 10)
        line._is_drag_guide = True
        self.scene.addItem(line)

        m, s = int(time_val) // 60, time_val % 60
        bg = QGraphicsRectItem(gx - 26, 1, 52, 18)
        bg.setPen(QPen(QColor("#005577")))
        bg.setBrush(QColor("#00ccff"))
        bg.setZValue(Z_OVERLAY + 11)
        bg._is_drag_guide = True
        self.scene.addItem(bg)

        txt = QGraphicsTextItem(f"{m:02d}:{s:04.1f}")
        txt.setFont(QFont("Consolas", 8, QFont.Bold))
        txt.setDefaultTextColor(QColor("#0a0a0f"))
        txt.setPos(gx - 22, -1)
        txt.setZValue(Z_OVERLAY + 12)
        txt._is_drag_guide = True
        self.scene.addItem(txt)

    def _remove_drag_guide(self):
        for item in list(self.scene.items()):
            if getattr(item, '_is_drag_guide', False):
                self.scene.removeItem(item)
