"""Timeline Scene - QGraphicsScene com todos os elementos visuais."""

import logging
import math
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPolygonF, QPainterPath, QPainter

from makevid.qt.theme import C
from makevid.qt.timeline.clip_item import (
    ClipGraphicsItem,
    Z_BACKGROUND, Z_GRID, Z_TRACK_LAYER, Z_CLIP, Z_AUDIO_ITEM, Z_MARKER, Z_PLAYHEAD, Z_OVERLAY,
    ITEM_PAD_X, ITEM_PAD_Y,
)
from makevid.qt.timeline.track_item import TrackGraphicsItem
from makevid.qt.timeline.ruler import RulerItem
from makevid.qt.timeline.playhead import PlayheadItem
from makevid.qt.timeline.interaction import SceneInteraction
from makevid.qt.timeline.hover_controller import HoverController

_TRACKS = [
    ("video", "VIDEO", C["blue"],        3.0, "Track"),
    ("fx",    "FX",    C["track_fx"],    1.2, "Effects"),
    ("voice", "VOICE", C["track_voice"], 1.2, "TTS"),
    ("sfx",   "SFX",   C["track_sfx"],  1.2, "Foley"),
    ("music", "MUSIC", C["track_music"], 1.2, "Score"),
    ("audio", "AUDIO", C["track_audio"], 1.5, "Mix"),
]

_log = logging.getLogger("timeline")


# ── Background ────────────────────────────────────────────────────────────────

class _BgItem(QGraphicsItem):

    def __init__(self, x, y, w, h, color_even, tint_color, active=False):
        super().__init__()
        self._w = w
        self._h = h
        self._bg = QColor(color_even)
        self._tint = QColor(tint_color)
        self._active = active
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setAcceptHoverEvents(False)
        self.setZValue(Z_BACKGROUND)
        self.setPos(x, y)

    def set_hovered(self, hovered: bool):
        if self._hovered != hovered:
            self._hovered = hovered
            self.update()

    def boundingRect(self):
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        r = QRectF(0, 0, self._w, self._h)
        painter.setPen(Qt.NoPen)
        bg = QColor(self._bg)
        tint = QColor(self._tint)

        if self._active:
            bg.setAlpha(min(255, bg.alpha() + 14))
            tint.setAlpha(min(255, tint.alpha() + 16))

        painter.fillRect(r, bg)
        painter.fillRect(r, tint)

        if self._hovered:
            hv = QColor(tint)
            hv.setAlpha(min(255, tint.alpha() + 36))
            painter.fillRect(r, hv)
            edge = QColor(tint).lighter(130)
            edge.setAlpha(230)
            painter.setPen(QPen(edge, 1.6))
            painter.drawRect(r.adjusted(0.8, 0.8, -0.8, -0.8))


class _SepItem(QGraphicsItem):

    def __init__(self, x1, y, x2):
        super().__init__()
        self._len = x2 - x1
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(Z_GRID)
        self.setPos(x1, y)

    def boundingRect(self):
        return QRectF(0, -1, self._len, 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(QPen(QColor(255, 255, 255, 5), 1))
        painter.drawLine(QPointF(0, 0), QPointF(self._len, 0))


# ── Diamond ───────────────────────────────────────────────────────────────────

class _DiamondItem(QGraphicsItem):

    def __init__(self, x, cy, sz, position, marked=False):
        super().__init__()
        self._sz = sz
        self._position = position
        self._marked = marked
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(Z_MARKER)
        self.setPos(x, cy)

    def boundingRect(self):
        s = self._sz + 6
        return QRectF(-s, -s, s * 2, s * 2)

    def paint(self, painter: QPainter, option, widget=None):
        sz = self._sz
        if self._hovered:
            sz = min(12, sz + 4)
            painter.setPen(QPen(QColor("#bb77ff"), 2))
            painter.setBrush(QBrush(QColor("#3a1a6a")))
        elif self._marked:
            sz = 10
            painter.setPen(QPen(QColor("#00ffee"), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(QPolygonF([
                QPointF(-sz - 2, 0), QPointF(0, -sz - 2),
                QPointF(sz + 2, 0), QPointF(0, sz + 2)]))
            painter.setPen(QPen(QColor("#bb77ff"), 2))
            painter.setBrush(QBrush(QColor("#6b3fa0")))
        else:
            painter.setPen(QPen(QColor("#6b3fa0"), 2))
            painter.setBrush(QBrush(QColor("#2a1a4a")))
        painter.drawPolygon(QPolygonF([
            QPointF(-sz, 0), QPointF(0, -sz),
            QPointF(sz, 0), QPointF(0, sz)]))
        if self._marked:
            painter.setPen(QPen(QColor("#00ffee")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(QPointF(-4, 4), "✓")

    def hoverEnterEvent(self, event): self._hovered = True;  self.update()
    def hoverLeaveEvent(self, event): self._hovered = False; self.update()


# ── StoryboardBadge ───────────────────────────────────────────────────────────

class _StoryboardBadge(QGraphicsItem):

    def __init__(self, x, rh, index, scene_data):
        super().__init__()
        self._r = 8
        self._index = index
        self._scene_data = scene_data
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(Z_MARKER - 5)
        self.setPos(x, rh - 10)
        self.setToolTip(f"Cena {index + 1}: {scene_data.get('visual', '')[:40]}")

    def boundingRect(self):
        r = self._r + 4
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option, widget=None):
        r = self._r
        if self._hovered:
            painter.setPen(QPen(QColor("#00ffee"), 2)); painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(0, 0), r + 3, r + 3)
            painter.setPen(QPen(QColor("#00ffee"), 2))
            painter.setBrush(QBrush(QColor("#ffd700")))
            painter.drawEllipse(QPointF(0, 0), r + 1, r + 1)
        else:
            painter.setPen(QPen(QColor("#ffd700"), 1))
            painter.setBrush(QBrush(QColor("#c89b3c")))
            painter.drawEllipse(QPointF(0, 0), r, r)
        painter.setPen(QPen(QColor("#0a0a0f")))
        painter.setFont(QFont("Consolas", 8 if not self._hovered else 9, QFont.Bold))
        painter.drawText(QPointF(-4, 4), str(self._index + 1))

    def hoverEnterEvent(self, event): self._hovered = True;  self.setCursor(Qt.PointingHandCursor); self.update()
    def hoverLeaveEvent(self, event): self._hovered = False; self.setCursor(Qt.ArrowCursor);        self.update()


# ── FxItem ────────────────────────────────────────────────────────────────────

class _FxItem(QGraphicsItem):

    def __init__(self, track_item, x, y, w, h, color):
        super().__init__()
        self.track_item = track_item
        self._w = w
        self._h = h
        self._color = QColor(color)
        self._selected = False
        self._hovered = False
        import random
        self._beam_phase = random.uniform(0, 360)
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(False)
        self.setZValue(Z_AUDIO_ITEM)
        self.setPos(x, y)

    def boundingRect(self):
        return QRectF(-4, -4, self._w + 8, self._h + 8)

    def paint(self, painter: QPainter, option, widget=None):
        x, y, w, h = ITEM_PAD_X, ITEM_PAD_Y, self._w - ITEM_PAD_X * 2, self._h - ITEM_PAD_Y * 2
        if w < 2 or h < 2:
            return
        c = self._color
        r = 4.0

        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, w, h), r, r)

        painter.setPen(Qt.NoPen)
        painter.fillPath(path, QBrush(QColor("#1a0a2a")))

        if self._selected:
            self._paint_beam_border(painter, path)
        else:
            hover_pen = QColor(c).lighter(115)
            painter.setPen(QPen(hover_pen if self._hovered else c, 2 if self._hovered else 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        name = self.track_item.name.lower()
        ix1, ix2, mid = x + 4, x + w - 4, y + h / 2
        painter.setPen(QPen(c.darker(130), 1))
        if "fade in" in name:
            for i in range(0, int(ix2 - ix1), 3):
                if i / max(1, ix2 - ix1) < 0.8:
                    painter.drawLine(QPointF(ix1 + i, y + 2), QPointF(ix1 + i, y + h - 2))
        elif "fade out" in name:
            for i in range(0, int(ix2 - ix1), 3):
                if 1.0 - i / max(1, ix2 - ix1) < 0.8:
                    painter.drawLine(QPointF(ix1 + i, y + 2), QPointF(ix1 + i, y + h - 2))
        elif "flash" in name:
            cx = (ix1 + ix2) / 2
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                painter.drawLine(QPointF(cx, mid), QPointF(cx + 8 * math.cos(rad), mid + 6 * math.sin(rad)))
        elif "glitch" in name:
            import random
            rng = random.Random(hash(self.track_item.id))
            for gy in range(int(y + 3), int(y + h - 3), 4):
                gx = ix1 + rng.randint(0, max(1, int(ix2 - ix1) // 2))
                gw = rng.randint(4, min(12, int(ix2 - gx)))
                painter.drawLine(QPointF(gx, gy), QPointF(gx + gw, gy))
        elif "dissolve" in name or "cross" in name:
            painter.drawLine(QPointF(ix1, y + 2), QPointF(ix2, y + h - 2))
            painter.drawLine(QPointF(ix1, y + h - 2), QPointF(ix2, y + 2))
        else:
            for i in range(0, int(ix2 - ix1), 6):
                painter.drawLine(QPointF(ix1 + i, y + h - 2), QPointF(ix1 + i + 4, y + 2))

        painter.setPen(QPen(c))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(QPointF(x + 5, y + h - 4), self.track_item.name[:18])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(c))
        painter.drawRect(QRectF(x, y, 4, h))
        painter.drawRect(QRectF(x + w - 4, y, 4, h))

    def _paint_beam_border(self, painter, path):
        from makevid.qt.timeline.clip_item import ClipGraphicsItem
        from PySide6.QtGui import QConicalGradient, QPainterPathStroker
        angle = (ClipGraphicsItem._beam_angle + self._beam_phase) % 360

        stroker = QPainterPathStroker()
        stroker.setWidth(2.5)
        border_area = stroker.createStroke(path)

        stroker_glow = QPainterPathStroker()
        stroker_glow.setWidth(7.0)
        glow_area = stroker_glow.createStroke(path)

        cg = QConicalGradient(0.5, 0.5, angle)
        cg.setCoordinateMode(QConicalGradient.CoordinateMode.ObjectMode)
        cg.setColorAt(0.00, QColor(0,   220, 255, 255))
        cg.setColorAt(0.15, QColor(180,  80, 255, 255))
        cg.setColorAt(0.35, QColor(0,   120, 255, 255))
        cg.setColorAt(0.50, QColor(0,   220, 255, 255))
        cg.setColorAt(0.65, QColor(180,  80, 255, 255))
        cg.setColorAt(0.85, QColor(0,   120, 255, 255))
        cg.setColorAt(1.00, QColor(0,   220, 255, 255))

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setOpacity(0.35)
        painter.fillPath(glow_area, QBrush(cg))
        painter.setOpacity(1.0)
        painter.fillPath(border_area, QBrush(cg))
        painter.restore()


# ── SbLineItem ────────────────────────────────────────────────────────────────

class _SbLineItem(QGraphicsItem):

    def __init__(self, x, rh, vh):
        super().__init__()
        self._rh = rh
        self._len = vh - rh
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(Z_GRID + 5)
        self.setPos(x, rh)

    def boundingRect(self):
        return QRectF(-1, 0, 2, self._len)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(QPen(QColor(C["gold"]), 1, Qt.DashDotLine))
        painter.drawLine(QPointF(0, 0), QPointF(0, self._len))


# ── TimelineScene ─────────────────────────────────────────────────────────────

class TimelineScene(QGraphicsScene):

    def __init__(self, tl):
        super().__init__()
        self.tl = tl
        self._track_pos = {}
        self._label_pos = {}
        self._playhead = None
        self._track_items = {}   # id → QGraphicsItem
        self._clip_items = {}    # clip.id → ClipGraphicsItem
        self._bg_items = {}      # key → _BgItem
        self._track_layers = {}  # key → bounds dict (não mais QGraphicsItem)
        self._interaction = SceneInteraction(self)
        self._hover = HoverController(self)
        self.setBackgroundBrush(QColor(8, 12, 22, 235))
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

    # ── public ────────────────────────────────────────────────────────────────

    def rebuild_scene(self, project, zoom, ph_pos,
                      sel_track_id=None, sel_clip_id=None, active_track_key=None):
        """Reconstrução completa — apenas para mudanças estruturais."""
        self.clear()
        self._playhead = None
        self._track_items = {}
        self._clip_items = {}
        self._bg_items = {}
        self._track_layers = {}
        self._hover.reset()

        rh = self.tl.RULER_H
        vw = self.tl._view.viewport().width() or 900
        vh = self.tl._view.viewport().height() or 300

        total = max(project.total_duration(), 30)
        sw = max(vw, int(total * zoom) + 100)

        self.setSceneRect(0, 0, sw, vh)

        self._calc_positions(vh, rh)
        self._draw_backgrounds(sw, active_track_key)
        self._draw_ruler(sw, rh, zoom, total)
        self._draw_clips(project, zoom, sel_clip_id)
        self._draw_diamonds(project, zoom)
        self._draw_storyboard(project, zoom, vh, rh)
        self._draw_track_items(project, zoom, sel_track_id)

        self._playhead = PlayheadItem(ph_pos, zoom, vh)
        self._playhead._tl = self.tl
        self.addItem(self._playhead)

        if hasattr(self.tl, '_header'):
            self.tl._header.sync(self._track_pos, self._label_pos)

    def rebuild_empty(self):
        self.clear()
        self._playhead = None
        self._track_items = {}
        self._clip_items = {}
        self._bg_items = {}
        self._track_layers = {}
        self._hover.reset()

        rh = self.tl.RULER_H
        vw = self.tl._view.viewport().width() or 900
        vh = self.tl._view.viewport().height() or 300

        self.setSceneRect(0, 0, vw, vh)
        self._calc_positions(vh, rh)
        self._draw_backgrounds(vw)
        self._draw_ruler(vw, rh, self.tl.zoom, 30)

        if hasattr(self.tl, '_header'):
            self.tl._header.sync(self._track_pos, self._label_pos)

    def refresh_visual_state(self, sel_track_id=None, sel_clip_id=None, active_track_key=None):
        """Atualiza apenas estado visual (seleção, hover, active track) sem rebuild."""
        # Atualiza seleção de clips
        for cid, gi in self._clip_items.items():
            selected = cid == sel_clip_id
            if gi._selected != selected:
                gi._selected = selected
                gi.update()

        # Atualiza seleção de track items
        for tid, gi in self._track_items.items():
            selected = tid == sel_track_id
            if gi._selected != selected:
                gi._selected = selected
                gi.update()

        # Atualiza background ativo
        for key, bg in self._bg_items.items():
            is_active = key == active_track_key
            if bg._active != is_active:
                bg._active = is_active
                bg.update()

    def update_playhead(self, pos, zoom):
        if self._playhead:
            self._playhead.set_position(pos, zoom)

    def select_track_item(self, item_id):
        self.refresh_visual_state(
            sel_track_id=item_id,
            sel_clip_id=self.tl.selection.selected_clip_id,
            active_track_key=self.tl.selection.active_track_key,
        )

    # ── layout ────────────────────────────────────────────────────────────────

    def _calc_positions(self, vh, rh):
        gap = self.tl.TRACK_GAP
        collapsed = getattr(self.tl, 'collapsed_tracks', set())
        visible = [t for t in _TRACKS if t[0] not in collapsed]
        n = len(visible)
        available = vh - rh - 2 - gap * (len(_TRACKS) - 1) - 2
        total_weight = sum(t[3] for t in visible)
        y = rh + 2
        self._track_pos = {}
        self._label_pos = {}

        if total_weight > 0 and n > 0:
            heights = [max(1, int(available * t[3] / total_weight)) for t in visible]
            diff = available - sum(heights)
            order = sorted(range(n), key=lambda i: visible[i][3], reverse=True)
            for i in range(abs(diff)):
                heights[order[i % n]] += 1 if diff > 0 else -1
            for (key, *_), h in zip(visible, heights):
                self._track_pos[key] = (y, h)
                y += h + gap

        lbl_y = rh + 2
        lbl_gap = 4
        lbl_h_collapsed = 14
        if n > 0 and total_weight > 0:
            lbl_available = vh - rh - 2 - lbl_gap * (len(_TRACKS) - 1) - lbl_h_collapsed * len(collapsed)
            for t in _TRACKS:
                key = t[0]
                if key in collapsed:
                    self._label_pos[key] = (lbl_y, lbl_h_collapsed)
                    lbl_y += lbl_h_collapsed + lbl_gap
                else:
                    h = max(lbl_h_collapsed, int(lbl_available * t[3] / total_weight))
                    self._label_pos[key] = (lbl_y, h)
                    lbl_y += h + lbl_gap
        else:
            for t in _TRACKS:
                self._label_pos[t[0]] = (lbl_y, lbl_h_collapsed)
                lbl_y += lbl_h_collapsed + lbl_gap

    # ── draw ──────────────────────────────────────────────────────────────────

    def _draw_backgrounds(self, sw, active_track_key=None):
        for i, (key, _, color, _, _) in enumerate(_TRACKS):
            if key not in self._track_pos:
                continue
            y, h = self._track_pos[key]
            is_active = key == active_track_key
            bg_alpha = 82 if is_active else 62
            tint_alpha = 88 if is_active else 58
            bg = QColor(14, 22, 42, bg_alpha) if i % 2 == 0 else QColor(7, 11, 20, bg_alpha)
            tint = QColor(color)
            tint.setAlpha(tint_alpha)
            bg_item = _BgItem(0, y, sw, h, bg, tint, active=is_active)
            self._bg_items[key] = bg_item
            self.addItem(bg_item)
            self.addItem(_SepItem(0, y, sw))
            self._track_layers[key] = {"x": 0, "y": y, "w": sw, "h": h}

    def _draw_ruler(self, sw, rh, zoom, total):
        self._ruler_item = RulerItem(sw, rh, zoom, total)
        self.addItem(self._ruler_item)

    def _draw_clips(self, project, zoom, sel_clip_id=None):
        if "video" not in self._track_pos:
            return
        if "video" in getattr(self.tl, 'collapsed_tracks', set()):
            return
        vy, vh = self._track_pos["video"]
        t = 0.0
        ia = self._interaction
        drag_id = ia._drag_target.id if ia._drag_mode == "clip_move" and ia._drag_target else None
        for clip in sorted(project.clips, key=lambda c: c.position):
            x = int(t * zoom)
            w = int(clip.duration * zoom)
            is_drag = clip.id == drag_id
            item = ClipGraphicsItem(clip, x, vy, w, vh,
                                    selected=is_drag or clip.id == sel_clip_id)
            self._clip_items[clip.id] = item
            self.addItem(item)
            if is_drag:
                ia._drag_clip_item = item
                item.setZValue(Z_OVERLAY)
            t += clip.duration

    def _draw_diamonds(self, project, zoom):
        if "fx" not in self._track_pos:
            return
        if "fx" in getattr(self.tl, 'collapsed_tracks', set()):
            return
        ty, th = self._track_pos["fx"]
        cy = ty + th / 2
        sz = min(8, max(4, int(th / 2 - 2)))
        marked = self._interaction._marked_diamonds
        t = 0.0
        for clip in sorted(project.clips, key=lambda c: c.position):
            if clip.position > 0:
                dx = int(t * zoom)
                did = f"diamond_{clip.position}"
                self.addItem(_DiamondItem(dx, cy, sz, clip.position, did in marked))
            t += clip.duration

    def _draw_storyboard(self, project, zoom, vh, rh):
        if not getattr(project, "_storyboard_applied", False):
            return
        t = 0.0
        for i, scene in enumerate(getattr(project.world, "scenes", [])):
            dur = float(scene.get("duration", 5))
            x = int(t * zoom)
            self.addItem(_SbLineItem(x, rh, vh))
            self.addItem(_StoryboardBadge(x, rh, i, scene))
            t += dur

    def _draw_track_items(self, project, zoom, sel_track_id=None):
        collapsed = getattr(self.tl, 'collapsed_tracks', set())
        color_map = {t[0]: t[2] for t in _TRACKS}
        for name in ("fx", "voice", "sfx", "music", "audio"):
            if name in collapsed or name not in self._track_pos:
                continue
            ty, th = self._track_pos[name]
            color = color_map[name]
            items = sorted(project.get_track_items(name), key=lambda i: i.start_time)

            from collections import defaultdict
            groups = defaultdict(list)
            for ti in items:
                key = ti.clip_index if ti.clip_index >= 0 else ti.id
                groups[key].append(ti)

            for ti in items:
                x = int(ti.start_time * zoom)
                w = max(4, int(ti.duration * zoom))
                selected = ti.id == sel_track_id
                if name == "fx":
                    gi = _FxItem(ti, x, ty, w, th, color)
                    gi._selected = selected
                else:
                    group_key = ti.clip_index if ti.clip_index >= 0 else ti.id
                    gi = TrackGraphicsItem(ti, x, ty, w, th, color,
                                          selected=selected,
                                          group_names=groups[group_key])
                self._track_items[ti.id] = gi
                self.addItem(gi)

    # ── mouse (chamado pela view) ──────────────────────────────────────────────

    def on_mouse_press(self, pos, button):
        self._interaction.on_press(pos, button)

    def on_mouse_release(self, pos):
        self._interaction.on_release(pos)

    def on_mouse_move(self, pos, buttons=Qt.NoButton):
        self._interaction.on_move(pos, buttons)

    def update_hover(self, pos):
        self._hover.update(pos)

    def _track_key_at_pos(self, pos):
        if pos is None:
            return None
        for key, bounds in self._track_layers.items():
            if bounds["y"] <= pos.y() <= bounds["y"] + bounds["h"]:
                return key
        return None

    def _track_layer_contains(self, key, pos):
        b = self._track_layers.get(key)
        if not b:
            return False
        return b["x"] <= pos.x() <= b["x"] + b["w"] and b["y"] <= pos.y() <= b["y"] + b["h"]

    def mouseDoubleClickEvent(self, event):
        self._interaction._undo_last_diamond_toggle()
        if self._interaction.on_double_click(event.scenePos()):
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
