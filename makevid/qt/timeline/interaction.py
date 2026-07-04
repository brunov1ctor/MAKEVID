"""Interaction - Toda interação de mouse na timeline scene."""

import logging
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor, QFont
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem

from makevid.qt.timeline.clip_item import ClipGraphicsItem
from makevid.qt.timeline.track_item import TrackGraphicsItem
from makevid.qt.theme import C

_log = logging.getLogger("timeline")


class SceneInteraction:

    def __init__(self, scene):
        self.scene = scene
        self.tl = scene.tl
        self._reset_drag()
        self.item_clicked = None
        self.clip_clicked = None
        self.label_clicked = None
        self.track_empty_clicked = None
        self._marked_diamonds = set()
        self._last_diamond_toggle = None

    def _reset_drag(self):
        self._drag_mode = None
        self._drag_target = None
        self._drag_start_x = 0
        self._drag_orig = 0
        self._drag_orig_start = 0
        self._drag_group = None
        self._drag_ghost_pos = None
        self._drag_clip_item = None

    # ── double-click ──────────────────────────────────────────────────────────

    def on_double_click(self, pos):
        lbl_w = self.tl.LBL_W
        if pos.x() < lbl_w:
            return False

        tp = self.scene._track_pos

        if "fx" in tp:
            ty, th = tp["fx"]
            if ty <= pos.y() <= ty + th:
                project = self.tl.project
                all_ids = {f"diamond_{c.position}" for c in project.clips if c.position > 0}
                if all_ids:
                    self._marked_diamonds = set() if self._marked_diamonds else set(all_ids)
                    self.tl.redraw()
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
        lbl_w = self.tl.LBL_W
        ruler_h = self.tl.RULER_H
        zoom = self.tl.zoom

        self._reset_drag()

        if button == Qt.RightButton:
            return True

        if getattr(self.tl, '_split_mode', False):
            self._do_split_at(pos)
            return True

        if getattr(self.tl, '_audio_split_mode', None):
            self._do_audio_split_at(pos)
            return True

        # Labels laterais
        if pos.x() < lbl_w:
            from makevid.qt.timeline.timeline_scene import _TRACKS
            collapsed = self.tl.collapsed_tracks

            for key, *_ in _TRACKS:
                if key not in self.scene._label_pos:
                    continue
                y, h = self.scene._label_pos[key]
                cy = y + h / 2
                if 1 <= pos.x() <= 9 and cy - 4 <= pos.y() <= cy + 3:
                    if key in collapsed:
                        collapsed.discard(key)
                    else:
                        collapsed.add(key)
                    self.tl.redraw()
                    return True

            for name, (ty, th) in self.scene._track_pos.items():
                if ty <= pos.y() <= ty + th:
                    self.tl.set_active_track(name)
                    cb = self.label_clicked or self.track_empty_clicked
                    if cb:
                        cb(name)
                    return True
            return False

        # Ruler → playhead
        if pos.y() < ruler_h:
            if self._check_storyboard_click(pos):
                return True
            t = max(0, (pos.x() - lbl_w) / zoom)
            self.tl.set_playhead(t)
            self._drag_mode = "playhead"
            self._drag_start_x = pos.x()
            return True

        # Tracks de audio/fx/voice/sfx/music — hit-test direto no item visual
        for name, (ty, th) in self.scene._track_pos.items():
            if name == "video":
                continue
            if not (ty <= pos.y() <= ty + th):
                continue

            # Tenta achar o item visual diretamente
            gi = self._track_item_at(pos)
            _log.debug(f"on_press track={name} pos=({pos.x():.0f},{pos.y():.0f}) gi={'None' if gi is None else gi.track_item.id}")
            if gi is not None:
                self.tl.set_active_track(name)
                found = gi.track_item
                ix1 = lbl_w + int(found.start_time * zoom)
                iw = int(found.duration * zoom)
                local_x = pos.x() - ix1
                if local_x <= 6:
                    self._drag_mode = "item_trim_left"
                    self._drag_orig = found.duration
                    self._drag_orig_start = found.start_time
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

            # Diamond?
            item = self._item_at(pos)
            if item and hasattr(item, '_position'):
                did = f"diamond_{item._position}"
                was = did in self._marked_diamonds
                if was:
                    self._marked_diamonds.discard(did)
                else:
                    self._marked_diamonds.add(did)
                self._last_diamond_toggle = (did, was)
                self.tl.redraw()
                return True

            # Área vazia → menu da track
            _log.debug(f"on_press track={name} area_vazia → track_empty_clicked sel_track={self.tl._selected_track_item_id}")
            self.tl.set_active_track(name)
            cb = self.track_empty_clicked or self.label_clicked
            if cb:
                cb(name)
            return True

        # Clip de video
        item = self._item_at(pos)
        if isinstance(item, ClipGraphicsItem):
            self.tl.set_active_track("video")
            clip = item.clip
            local_x = pos.x() - item._x
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
                self._drag_clip_item = item
                item._orig_x = item._x
                item._selected = True
                item.setZValue(10)
            self._drag_target = clip
            self._drag_start_x = pos.x()
            return True

        # Área vazia → playhead
        t = max(0, (pos.x() - lbl_w) / zoom)
        self.tl.set_playhead(t)
        self._drag_mode = "playhead"
        self._drag_start_x = pos.x()
        return True

    # ── move ──────────────────────────────────────────────────────────────────

    def on_move(self, pos):
        if not self._drag_mode:
            return False

        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        dx = pos.x() - self._drag_start_x
        dt = dx / zoom

        if self._drag_mode == "playhead":
            self.tl.set_playhead(max(0, (pos.x() - lbl_w) / zoom))
            return True

        if self._drag_mode == "clip_move":
            if self._drag_clip_item:
                item = self._drag_clip_item
                item._x = item._orig_x + dx
                item.prepareGeometryChange()
                item.update()
            t = max(0, (pos.x() - lbl_w) / zoom)
            clips = sorted(self.tl.project.clips, key=lambda c: c.position)
            cur = 0.0
            new_pos = len(clips) - 1
            for i, c in enumerate(clips):
                if t < cur + c.duration:
                    new_pos = i
                    break
                cur += c.duration
            self._drag_ghost_pos = max(0, min(len(clips) - 1, new_pos))
            return True

        if self._drag_mode == "clip_trim_right":
            self._drag_target.duration = max(1.0, self._drag_orig + dt)
            self.tl.redraw()
            return True

        if self._drag_mode == "clip_trim_left":
            trim = max(0.0, min(self._drag_orig - 1.0, dt))
            self._drag_target.duration = max(1.0, self._drag_orig - trim)
            self.tl.redraw()
            return True

        if self._drag_mode == "item_move":
            new_start = max(0.0, self._drag_orig + dt)
            if self._drag_group:
                for gi, offset in self._drag_group:
                    gi.start_time = max(0.0, round(new_start + offset, 2))
            else:
                self._drag_target.start_time = round(new_start, 2)
            self.tl.redraw()
            self._update_drag_guide(new_start)
            return True

        if self._drag_mode == "item_trim_right":
            max_dur = self._get_wav_duration(self._drag_target) or self._drag_orig + 60
            self._drag_target.duration = max(0.5, min(max_dur, self._drag_orig + dt))
            self.tl.redraw()
            return True

        if self._drag_mode == "item_trim_left":
            trim = max(0.0, min(self._drag_orig - 0.5, dt))
            self._drag_target.start_time = round(self._drag_orig_start + trim, 2)
            self._drag_target.duration = max(0.5, self._drag_orig - trim)
            self.tl.redraw()
            return True

        return False

    # ── release ───────────────────────────────────────────────────────────────

    def on_release(self, pos):
        if not self._drag_mode:
            return False

        moved = abs(pos.x() - self._drag_start_x) >= 3

        if self._drag_mode == "item_move":
            if not moved:
                item_id = getattr(self._drag_target, 'id', None)
                _log.debug(f"on_release item_click id={item_id} → select+item_clicked")
                self.tl._selected_track_item_id = item_id
                self.scene.select_track_item(item_id)
                if self.item_clicked and self._drag_target:
                    self.item_clicked(self._drag_target)
                self._remove_drag_guide()
                self._reset_drag()
                return True
            else:
                _log.debug(f"on_release item_move drag id={getattr(self._drag_target,'id',None)}")
                self.tl._selected_track_item_id = getattr(self._drag_target, 'id', None)
                self._save()

        elif self._drag_mode in ("item_trim_left", "item_trim_right"):
            if moved:
                self._save()

        elif self._drag_mode == "clip_move":
            if not moved:
                self.tl._selected_clip_id = getattr(self._drag_target, 'id', None)
                if self.clip_clicked and self._drag_target:
                    self.clip_clicked(self._drag_target)
            else:
                clip = self._drag_target
                orig_pos = int(self._drag_orig)
                new_pos = self._drag_ghost_pos if self._drag_ghost_pos is not None else orig_pos
                if new_pos != orig_pos:
                    self.tl.project.move_clip(clip.id, new_pos)
                self._save()
                self.tl._selected_clip_id = None

            if self._drag_clip_item:
                self._drag_clip_item._x = self._drag_clip_item._orig_x
                self._drag_clip_item.setZValue(1)
                self._drag_clip_item._selected = False

        elif self._drag_mode in ("clip_trim_left", "clip_trim_right"):
            if moved:
                self._save()

        self._remove_drag_guide()
        self._reset_drag()
        _log.debug(f"on_release final redraw sel_track={self.tl._selected_track_item_id}")
        self.tl.redraw()
        return True

    # ── split ─────────────────────────────────────────────────────────────────

    def _do_split_at(self, pos):
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        project = self.tl.project

        if pos.x() < lbl_w:
            self.tl._exit_split_mode()
            return

        t = (pos.x() - lbl_w) / zoom
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
        self.tl.redraw()

    def _do_audio_split_at(self, pos):
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        project = self.tl.project
        track_name = getattr(self.tl, '_audio_split_mode', None)

        if not track_name or pos.x() < lbl_w:
            self.tl._exit_split_mode()
            return

        t = (pos.x() - lbl_w) / zoom
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
        self.tl.redraw()

    # ── storyboard ────────────────────────────────────────────────────────────

    def _check_storyboard_click(self, pos):
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        project = self.tl.project

        if not getattr(project, '_storyboard_applied', False):
            return False

        scenes = getattr(project.world, 'scenes', [])
        cur = 0.0
        for scene in scenes:
            dur = float(scene.get("duration", 5))
            x = lbl_w + int(cur * zoom)
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
        """Retorna o TrackGraphicsItem sob pos, ou None."""
        for tid, gi in self.scene._track_items.items():
            hit = gi._x <= pos.x() <= gi._x + gi._w and gi._y <= pos.y() <= gi._y + gi._h
            _log.debug(f"hit_test id={tid} pos=({pos.x():.0f},{pos.y():.0f}) item=({gi._x:.0f},{gi._y:.0f},{gi._w:.0f},{gi._h:.0f}) hit={hit}")
            if hit:
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
        lbl_w = self.tl.LBL_W
        zoom = self.tl.zoom
        gx = lbl_w + int(time_val * zoom)
        sh = self.scene.sceneRect().height()

        line = QGraphicsLineItem(gx, self.tl.RULER_H, gx, sh)
        line.setPen(QPen(QColor("#00ccff"), 1, Qt.DashLine))
        line.setZValue(50)
        line._is_drag_guide = True
        self.scene.addItem(line)

        m, s = int(time_val) // 60, time_val % 60
        bg = QGraphicsRectItem(gx - 26, 1, 52, 18)
        bg.setPen(QPen(QColor("#005577")))
        bg.setBrush(QColor("#00ccff"))
        bg.setZValue(51)
        bg._is_drag_guide = True
        self.scene.addItem(bg)

        txt = QGraphicsTextItem(f"{m:02d}:{s:04.1f}")
        txt.setFont(QFont("Consolas", 8, QFont.Bold))
        txt.setDefaultTextColor(QColor("#0a0a0f"))
        txt.setPos(gx - 22, -1)
        txt.setZValue(52)
        txt._is_drag_guide = True
        self.scene.addItem(txt)

    def _remove_drag_guide(self):
        for item in list(self.scene.items()):
            if getattr(item, '_is_drag_guide', False):
                self.scene.removeItem(item)
