"""Timeline Scene - QGraphicsScene com todos os elementos visuais."""

import logging
import math
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPolygonF, QPainterPath, QPainter, QLinearGradient

from makevid.qt.theme import C
from makevid.qt.timeline.clip_item import ClipGraphicsItem
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


# ── itens de background (sem QGraphicsRectItem nativo) ────────────────────────

class _BgItem(QGraphicsItem):
    """Fundo de uma faixa — nunca selecionável pelo Qt."""

    def __init__(self, x, y, w, h, color_even, tint_color, active=False):
        super().__init__()
        self._x, self._y, self._w, self._h = x, y, w, h
        self._bg = QColor(color_even)
        self._tint = QColor(tint_color)
        self._active = active
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setAcceptHoverEvents(False)
        self.setZValue(-10)

    def set_hovered(self, hovered: bool):
        if self._hovered != hovered:
            self._hovered = hovered
            self.update()

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        r = QRectF(self._x, self._y, self._w, self._h)
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
    """Linha separadora entre faixas."""

    def __init__(self, x1, y, x2):
        super().__init__()
        self._x1, self._y, self._x2 = x1, y, x2
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(-8)

    def boundingRect(self):
        return QRectF(self._x1, self._y - 1, self._x2 - self._x1, 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(QPen(QColor(255, 255, 255, 5), 1))
        painter.drawLine(QPointF(self._x1, self._y), QPointF(self._x2, self._y))


class _LabelBgItem(QGraphicsItem):
    """Painel esquerdo dos labels."""

    def __init__(self, w, h):
        super().__init__()
        self._w, self._h = w, h
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(5)

    def boundingRect(self):
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(Qt.NoPen)
        painter.fillRect(QRectF(0, 0, self._w, self._h), QColor(28, 46, 74, 70))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.drawLine(QPointF(self._w - 1, 0), QPointF(self._w - 1, self._h))


# ── Diamond ───────────────────────────────────────────────────────────────────

class _DiamondItem(QGraphicsItem):

    def __init__(self, x, cy, sz, position, marked=False):
        super().__init__()
        self._x, self._cy, self._sz = x, cy, sz
        self._position = position
        self._marked = marked
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(3)

    def boundingRect(self):
        s = self._sz + 6
        return QRectF(self._x - s, self._cy - s, s * 2, s * 2)

    def paint(self, painter: QPainter, option, widget=None):
        x, cy, sz = self._x, self._cy, self._sz
        if self._hovered:
            sz = min(12, sz + 4)
            painter.setPen(QPen(QColor("#bb77ff"), 2))
            painter.setBrush(QBrush(QColor("#3a1a6a")))
        elif self._marked:
            sz = 10
            painter.setPen(QPen(QColor("#00ffee"), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(QPolygonF([
                QPointF(x - sz - 2, cy), QPointF(x, cy - sz - 2),
                QPointF(x + sz + 2, cy), QPointF(x, cy + sz + 2)]))
            painter.setPen(QPen(QColor("#bb77ff"), 2))
            painter.setBrush(QBrush(QColor("#6b3fa0")))
        else:
            painter.setPen(QPen(QColor("#6b3fa0"), 2))
            painter.setBrush(QBrush(QColor("#2a1a4a")))
        painter.drawPolygon(QPolygonF([
            QPointF(x - sz, cy), QPointF(x, cy - sz),
            QPointF(x + sz, cy), QPointF(x, cy + sz)]))
        if self._marked:
            painter.setPen(QPen(QColor("#00ffee")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(QPointF(x - 4, cy + 4), "✓")

    def hoverEnterEvent(self, event): self._hovered = True;  self.update()
    def hoverLeaveEvent(self, event): self._hovered = False; self.update()


# ── StoryboardBadge ───────────────────────────────────────────────────────────

class _StoryboardBadge(QGraphicsItem):

    def __init__(self, x, rh, index, scene):
        super().__init__()
        self._x, self._r, self._cy = x, 8, rh - 10
        self._index = index
        self._scene_data = scene
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(8)
        self.setToolTip(f"Cena {index + 1}: {scene.get('visual', '')[:40]}")

    def boundingRect(self):
        r = self._r + 4
        return QRectF(self._x - r, self._cy - r, r * 2, r * 2)

    def paint(self, painter: QPainter, option, widget=None):
        x, cy, r = self._x, self._cy, self._r
        if self._hovered:
            painter.setPen(QPen(QColor("#00ffee"), 2)); painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(x, cy), r + 3, r + 3)
            painter.setPen(QPen(QColor("#00ffee"), 2))
            painter.setBrush(QBrush(QColor("#ffd700")))
            painter.drawEllipse(QPointF(x, cy), r + 1, r + 1)
        else:
            painter.setPen(QPen(QColor("#ffd700"), 1))
            painter.setBrush(QBrush(QColor("#c89b3c")))
            painter.drawEllipse(QPointF(x, cy), r, r)
        painter.setPen(QPen(QColor("#0a0a0f")))
        painter.setFont(QFont("Consolas", 8 if not self._hovered else 9, QFont.Bold))
        painter.drawText(QPointF(x - 4, cy + 4), str(self._index + 1))

    def hoverEnterEvent(self, event): self._hovered = True;  self.setCursor(Qt.PointingHandCursor); self.update()
    def hoverLeaveEvent(self, event): self._hovered = False; self.setCursor(Qt.ArrowCursor);        self.update()


# ── FxItem ────────────────────────────────────────────────────────────────────

class _FxItem(QGraphicsItem):

    def __init__(self, track_item, x, y, w, h, color):
        super().__init__()
        self.track_item = track_item
        self._x, self._y, self._w, self._h = x, y, w, h
        self._color = QColor(color)
        self._selected = False
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        x, y, w, h = self._x, self._y + 3, self._w, self._h - 6
        c = self._color
        hover_pen = QColor(c)
        hover_pen = hover_pen.lighter(115)
        if self._selected:
            painter.setPen(QPen(QColor("#00ffee"), 2))
        else:
            painter.setPen(QPen(hover_pen if self._hovered else c, 2 if self._hovered else 1))
        painter.setBrush(QBrush(QColor("#1a0a2a")))
        painter.drawRect(QRectF(x, y, w, h))

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

    def hoverEnterEvent(self, event): self._hovered = True;  self.update()
    def hoverLeaveEvent(self, event): self._hovered = False; self.update()
    def hoverMoveEvent(self, event):
        lx = event.scenePos().x() - self._x
        self.setCursor(Qt.SizeHorCursor if lx <= 6 or (self._w - lx) <= 6 else Qt.ArrowCursor)


# ── EyeItem ───────────────────────────────────────────────────────────────────

class _EyeItem(QGraphicsItem):

    def __init__(self, track_key, x, y, size, visible, tl):
        super().__init__()
        self._track_key = track_key
        self._size = size
        self._visible = visible
        self._tl = tl
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setEnabled(True)
        self.setZValue(9)
        self.setPos(x, y)
        self.setToolTip("Colapsar track" if visible else "Expandir track")

    def boundingRect(self):
        s = self._size
        return QRectF(-1, -1, s + 2, s + 2)

    def paint(self, painter: QPainter, option, widget=None):
        s = self._size
        alpha = 220 if self._hovered else 150
        color = QColor(255, 255, 255, alpha) if self._visible else QColor(180, 180, 200, alpha)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        if self._visible:
            poly = QPolygonF([QPointF(0, 0), QPointF(0, s), QPointF(s, s / 2)])
        else:
            poly = QPolygonF([QPointF(0, 0), QPointF(s, 0), QPointF(s / 2, s)])
        painter.drawPolygon(poly)

    def hoverEnterEvent(self, event): self._hovered = True;  self.setCursor(Qt.PointingHandCursor); self.update()
    def hoverLeaveEvent(self, event): self._hovered = False; self.setCursor(Qt.ArrowCursor);        self.update()

    def mousePressEvent(self, event):
        self._toggle_collapsed()
        if event is not None:
            event.accept()

    def _toggle_collapsed(self):
        collapsed = self._tl.collapsed_tracks
        if self._track_key in collapsed:
            collapsed.discard(self._track_key)
        else:
            collapsed.add(self._track_key)
        self._tl.redraw()


# ── TimelineScene ─────────────────────────────────────────────────────────────

class TimelineScene(QGraphicsScene):

    def __init__(self, tl):
        super().__init__()
        self.tl = tl
        self._track_pos = {}
        self._label_pos = {}
        self._playhead = None
        self._track_items = {}
        self._bg_items = {}
        self._interaction = SceneInteraction(self)
        self._hover = HoverController(self)
        self.setBackgroundBrush(QColor(8, 12, 22, 235))
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

    # ── public ────────────────────────────────────────────────────────────────

    def rebuild(self, project, zoom, ph_pos, sel_track_id=None, sel_clip_id=None, active_track_key=None):
        self.clear()
        self._playhead = None
        self._track_items = {}
        self._bg_items = {}
        self._hover.reset()

        lw = self.tl.LBL_W
        rh = self.tl.RULER_H
        vw = self.tl._view.viewport().width() or 900
        vh = self.tl._view.viewport().height() or 300

        total = max(project.total_duration(), 30)
        sw = max(vw, lw + int(total * zoom) + 100)

        self.setSceneRect(0, 0, sw, vh)

        self._calc_positions(vh, rh)
        self._draw_backgrounds(lw, sw, active_track_key)
        self._draw_ruler(lw, sw, rh, zoom, total)
        self._draw_clips(project, zoom, lw, sel_clip_id)
        self._draw_diamonds(project, zoom, lw)
        self._draw_storyboard(project, zoom, lw, vh, rh)
        self._draw_track_items(project, zoom, lw, sel_track_id)
        self._draw_labels(lw, vh, rh, project)

        self._playhead = PlayheadItem(ph_pos, zoom, lw, vh)
        self._playhead._tl = self.tl
        self.addItem(self._playhead)

    def rebuild_empty(self):
        self.clear()
        self._playhead = None
        self._track_items = {}
        self._bg_items = {}
        self._hover.reset()

        lw = self.tl.LBL_W
        rh = self.tl.RULER_H
        vw = self.tl._view.viewport().width() or 900
        vh = self.tl._view.viewport().height() or 300

        self.setSceneRect(0, 0, vw, vh)
        self._calc_positions(vh, rh)
        self._draw_backgrounds(lw, vw)
        self._draw_ruler(lw, vw, rh, self.tl.zoom, 30)
        self._draw_labels(lw, vh, rh, None)

    def update_playhead(self, pos, zoom):
        if self._playhead:
            self._playhead.set_position(pos, zoom, self.tl.LBL_W)

    def select_track_item(self, item_id):
        for tid, gi in self._track_items.items():
            selected = tid == item_id
            if gi._selected != selected:
                gi._selected = selected
                gi.update()

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

    def _draw_backgrounds(self, lw, sw, active_track_key=None):
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
            bg_item = _BgItem(lw, y, sw - lw, h, bg, tint, active=is_active)
            self._bg_items[key] = bg_item
            self.addItem(bg_item)
            self.addItem(_SepItem(lw, y, sw))

    def _draw_ruler(self, lw, sw, rh, zoom, total):
        self._ruler_item = RulerItem(lw, sw, rh, zoom, total)
        self.addItem(self._ruler_item)

    def _draw_labels(self, lw, vh, rh, project):
        self.addItem(_LabelBgItem(lw, vh))

        collapsed = getattr(self.tl, 'collapsed_tracks', set())
        for key, label, color, _, sub in _TRACKS:
            if key not in self._label_pos:
                continue
            y, h = self._label_pos[key]
            is_collapsed = key in collapsed
            cy = y + h / 2

            self.addItem(_EyeItem(key, 1, cy - 4, 7, not is_collapsed, self.tl))

            bar = _BarItem(10, y + 2, 4, h - (2 if is_collapsed else 4), color)
            self.addItem(bar)

            t1 = _TextItem(label, 16, cy - (12 if not is_collapsed else 6), 7, bold=True,
                           color=C["text2"] if not is_collapsed else C["text3"])
            self.addItem(t1)

            if not is_collapsed:
                vol_map = {"VOICE": "voice", "SFX": "sfx", "MUSIC": "music", "AUDIO": "audio"}
                tk = vol_map.get(label)
                if tk and project and hasattr(project, "track_volumes"):
                    txt2 = f"{int(project.track_volumes.get(tk, 1.0) * 100)}%"
                    t2 = _TextItem(txt2, 16, cy + 1, 6, bold=True, color=C["text3"], mono=True)
                else:
                    t2 = _TextItem(sub, 16, cy + 1, 6, color=C["text3"])
                self.addItem(t2)

    def _draw_clips(self, project, zoom, lw, sel_clip_id=None):
        if "video" not in self._track_pos:
            return
        if "video" in getattr(self.tl, 'collapsed_tracks', set()):
            return
        vy, vh = self._track_pos["video"]
        t = 0.0
        ia = self._interaction
        drag_id = ia._drag_target.id if ia._drag_mode == "clip_move" and ia._drag_target else None
        for clip in sorted(project.clips, key=lambda c: c.position):
            x = lw + int(t * zoom)
            w = int(clip.duration * zoom)
            is_drag = clip.id == drag_id
            item = ClipGraphicsItem(clip, x, vy, w, vh, selected=is_drag or clip.id == sel_clip_id)
            self.addItem(item)
            if is_drag:
                ia._drag_clip_item = item
                item.setZValue(10)
            t += clip.duration

    def _draw_diamonds(self, project, zoom, lw):
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
                dx = lw + int(t * zoom)
                did = f"diamond_{clip.position}"
                self.addItem(_DiamondItem(dx, cy, sz, clip.position, did in marked))
            t += clip.duration

    def _draw_storyboard(self, project, zoom, lw, vh, rh):
        if not getattr(project, "_storyboard_applied", False):
            return
        t = 0.0
        for i, scene in enumerate(getattr(project.world, "scenes", [])):
            dur = float(scene.get("duration", 5))
            x = lw + int(t * zoom)
            self.addItem(_SbLineItem(x, rh, vh))
            self.addItem(_StoryboardBadge(x, rh, i, scene))
            t += dur

    def _draw_track_items(self, project, zoom, lw, sel_track_id=None):
        collapsed = getattr(self.tl, 'collapsed_tracks', set())
        color_map = {t[0]: t[2] for t in _TRACKS}
        for name in ("fx", "voice", "sfx", "music", "audio"):
            if name in collapsed or name not in self._track_pos:
                continue
            ty, th = self._track_pos[name]
            color = color_map[name]
            items = sorted(project.get_track_items(name), key=lambda i: i.start_time)
            for ti in items:
                x = lw + int(ti.start_time * zoom)
                w = max(4, int(ti.duration * zoom))
                if name == "fx":
                    selected = ti.id == sel_track_id
                    gi = _FxItem(ti, x, ty, w, th, color)
                    gi._selected = selected
                    self._track_items[ti.id] = gi
                    self.addItem(gi)
                else:
                    selected = ti.id == sel_track_id
                    gi = TrackGraphicsItem(ti, x, ty, w, th, color, selected=selected)
                    self._track_items[ti.id] = gi
                    self.addItem(gi)

    # ── mouse direto (chamado pela view, sem processamento Qt de seleção) ──────

    def on_mouse_press(self, pos, button):
        # EyeItem precisa receber o press via Qt normal
        item = self.itemAt(pos, self.tl._view.transform())
        if isinstance(item, _EyeItem):
            item._toggle_collapsed()
            return
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
        for key, (ty, th) in self._track_pos.items():
            if ty <= pos.y() <= ty + th:
                return key
        return None

    def _update_item_cursor(self, item, pos):
        if isinstance(item, (TrackGraphicsItem, ClipGraphicsItem, _FxItem)):
            lx = pos.x() - item._x
            item.setCursor(Qt.SizeHorCursor if lx <= 6 or (item._w - lx) <= 6 else Qt.ArrowCursor)
            return
        if isinstance(item, (_EyeItem, _StoryboardBadge)):
            item.setCursor(Qt.PointingHandCursor)
            return
        item.setCursor(Qt.ArrowCursor)

    # ── double-click ainda via Qt (não causa seleção) ─────────────────────────

    def mouseDoubleClickEvent(self, event):
        self._interaction._undo_last_diamond_toggle()
        if self._interaction.on_double_click(event.scenePos()):
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


# ── helpers de texto/barra ────────────────────────────────────────────────────

class _TextItem(QGraphicsItem):

    def __init__(self, text, x, y, size, bold=False, color=None, mono=False):
        super().__init__()
        self._text = text
        self._x, self._y = x, y
        self._size = size
        self._bold = bold
        self._color = QColor(color) if color else QColor(C["text"])
        self._mono = mono
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(7)

    def boundingRect(self):
        return QRectF(self._x, self._y, 200, 16)

    def paint(self, painter: QPainter, option, widget=None):
        weight = QFont.Bold if self._bold else QFont.Normal
        family = "Consolas" if self._mono else "Segoe UI"
        painter.setFont(QFont(family, self._size, weight))
        painter.setPen(self._color)
        painter.drawText(QPointF(self._x, self._y + self._size + 2), self._text)


class _BarItem(QGraphicsItem):

    def __init__(self, x, y, w, h, color):
        super().__init__()
        self._x, self._y, self._w, self._h = x, y, w, h
        self._color = QColor(color)
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(7)

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRect(QRectF(self._x, self._y, self._w, self._h))


class _SbLineItem(QGraphicsItem):

    def __init__(self, x, rh, vh):
        super().__init__()
        self._x, self._rh, self._vh = x, rh, vh
        self.setFlags(QGraphicsItem.GraphicsItemFlag(0))
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(-5)

    def boundingRect(self):
        return QRectF(self._x - 1, self._rh, 2, self._vh - self._rh)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(QPen(QColor(C["gold"]), 1, Qt.DashDotLine))
        painter.drawLine(QPointF(self._x, self._rh), QPointF(self._x, self._vh))
