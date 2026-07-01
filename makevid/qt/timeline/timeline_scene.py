"""Timeline Scene - QGraphicsScene com rendering completo (paridade com tkinter)."""

import math
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem,
    QGraphicsTextItem, QGraphicsItem
)
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPolygonF, QPainterPath, QPainter

from makevid.qt.theme import C
from makevid.qt.timeline.clip_item import ClipGraphicsItem
from makevid.qt.timeline.track_item import TrackGraphicsItem
from makevid.qt.timeline.ruler import RulerItem
from makevid.qt.timeline.playhead import PlayheadItem
from makevid.qt.timeline.interaction import SceneInteraction


def _track_config():
    return [
        # (key, label, color, weight, sub_label)
        ("video", "VIDEO", C["blue"],         3.0, "Track"),
        ("fx",    "FX",    C["track_fx"],     1.2, "Effects"),
        ("voice", "VOICE", C["track_voice"],  1.2, "TTS"),
        ("sfx",   "SFX",   C["track_sfx"],   1.2, "Foley"),
        ("music", "MUSIC", C["track_music"],  1.2, "Score"),
        ("audio", "AUDIO", C["track_audio"],  1.5, "Mix"),
    ]

TRACK_CONFIG = _track_config()


class TimelineScene(QGraphicsScene):
    """Scene completa com todos os elementos visuais da timeline."""

    def __init__(self, timeline_widget):
        super().__init__()
        self.tl = timeline_widget
        self.setBackgroundBrush(QColor(C["bg"]))

        self._playhead_item = None
        self._ruler_item = None
        self._track_positions = {}
        self._interaction = SceneInteraction(self)

    # ============================================================
    # REBUILD (rendering completo)
    # ============================================================

    def rebuild(self, project, zoom, playhead_pos):
        """Reconstroi toda a scene."""
        self.clear()
        self._playhead_item = None
        self._drag_guide_line = None
        # Atualizar config com cores atuais do tema
        global TRACK_CONFIG
        TRACK_CONFIG = _track_config()

        lbl_w = self.tl.LBL_W
        ruler_h = self.tl.RULER_H
        view_h = self.tl._view.viewport().height() or 300
        view_w = self.tl._view.viewport().width() or 900

        total_dur = max(project.total_duration(), 30)
        scene_w = max(view_w, lbl_w + int(total_dur * zoom) + 100)
        scene_h = view_h

        self.setSceneRect(0, 0, scene_w, scene_h)
        self.setBackgroundBrush(QColor(C["dark"]))

        # Calcular posicoes das tracks
        self._calc_track_positions(scene_h, ruler_h)

        # Desenhar backgrounds e separadores
        self._draw_all_track_bgs(lbl_w, scene_w, scene_h)

        # Centerline na track AUDIO (DAW style) — muito sutil
        ay, ah = self._track_positions["audio"]
        mid_audio = ay + ah // 2
        cl = QGraphicsLineItem(lbl_w, mid_audio, scene_w, mid_audio)
        cl.setPen(QPen(QColor(C["ruler_line"]), 1, Qt.DashLine))
        cl.setZValue(-8)
        self.addItem(cl)

        # Ruler
        self._ruler_item = RulerItem(lbl_w, scene_w, ruler_h, zoom, total_dur)
        self.addItem(self._ruler_item)

        # Clips de video
        self._draw_clips(project, zoom, lbl_w)

        # Diamonds (losangos FX entre clips)
        self._draw_diamonds(project, zoom, lbl_w)

        # Storyboard markers
        self._draw_storyboard_markers(project, zoom, lbl_w, scene_h)

        # Track items (audio, fx, etc)
        self._draw_track_items(project, zoom, lbl_w)

        # Playhead
        self._playhead_item = PlayheadItem(playhead_pos, zoom, lbl_w, scene_h)
        self._playhead_item._tl = self.tl
        self.addItem(self._playhead_item)

        # Labels laterais (por cima de tudo)
        self._draw_labels(scene_h, project)

    def update_playhead(self, pos, zoom):
        if self._playhead_item:
            self._playhead_item.set_position(pos, zoom, self.tl.LBL_W)

    # ============================================================
    # TRACK POSITIONS
    # ============================================================

    def _calc_track_positions(self, scene_h, ruler_h):
        available = scene_h - ruler_h - 4
        weights = [cfg[3] for cfg in TRACK_CONFIG]
        total_weight = sum(weights)
        gap = self.tl.TRACK_GAP
        track_space = max(96, available - gap * (len(TRACK_CONFIG) - 1))

        y = ruler_h + 2
        self._track_positions = {}
        for name, _, _, weight, _ in TRACK_CONFIG:
            h = max(14, int(track_space * weight / total_weight))
            self._track_positions[name] = (y, h)
            y += h + gap

    # ============================================================
    # TRACK BACKGROUNDS + SEPARATORS
    # ============================================================

    def _draw_all_track_bgs(self, lbl_w, scene_w, scene_h):
        for i, (name, _, color, _, _) in enumerate(TRACK_CONFIG):
            y, h = self._track_positions[name]
            bg_color = QColor(C["panel"]) if i % 2 == 0 else QColor(C["bg"])

            bg = QGraphicsRectItem(lbl_w, y, scene_w - lbl_w, h)
            bg.setPen(QPen(Qt.NoPen))
            bg.setBrush(QBrush(bg_color))
            bg.setZValue(-10)
            self.addItem(bg)

            # Tint colorido sutil da cor da track
            tint = QColor(color)
            tint.setAlpha(28)
            tint_item = QGraphicsRectItem(lbl_w, y, scene_w - lbl_w, h)
            tint_item.setPen(QPen(Qt.NoPen))
            tint_item.setBrush(QBrush(tint))
            tint_item.setZValue(-9)
            self.addItem(tint_item)

            # Linha separadora superior
            sep = QGraphicsLineItem(lbl_w, y, scene_w, y)
            sep.setPen(QPen(QColor(255, 255, 255, 10), 1))
            sep.setZValue(-8)
            self.addItem(sep)

    # ============================================================
    # LABELS LATERAIS (com volume %)
    # ============================================================

    def _draw_labels(self, scene_h, project):
        lbl_w = self.tl.LBL_W
        ruler_h = self.tl.RULER_H

        # Fundo do painel lateral — mesmo glass da interface
        bg = QGraphicsRectItem(0, 0, lbl_w, scene_h)
        bg.setPen(QPen(Qt.NoPen))
        bg.setBrush(QBrush(QColor(C["glass"])))
        bg.setZValue(5)
        self.addItem(bg)

        # Borda direita sutil
        border = QGraphicsLineItem(lbl_w - 1, ruler_h, lbl_w - 1, scene_h)
        border.setPen(QPen(QColor(C["glass_border"]), 1))
        border.setZValue(6)
        self.addItem(border)

        # ⏱ na ruler
        ruler_icon = QGraphicsTextItem("\u23f1")
        ruler_icon.setFont(QFont("Segoe UI", 10))
        ruler_icon.setDefaultTextColor(QColor(C["primary"]))
        ruler_icon.setPos(lbl_w // 2 - 8, ruler_h // 2 - 10)
        ruler_icon.setZValue(8)
        self.addItem(ruler_icon)

        # Linha inferior da ruler
        ruler_border = QGraphicsLineItem(0, ruler_h - 1, lbl_w, ruler_h - 1)
        ruler_border.setPen(QPen(QColor(C["glass_border"]), 1))
        ruler_border.setZValue(6)
        self.addItem(ruler_border)

        # Cada track
        for name, label, color, _, sub in TRACK_CONFIG:
            if name not in self._track_positions:
                continue
            y, h = self._track_positions[name]
            cy = y + h / 2

            # Barra lateral colorida
            bar = QGraphicsRectItem(0, y + 2, 4, h - 4)
            bar.setPen(QPen(Qt.NoPen))
            bar.setBrush(QBrush(QColor(color)))
            bar.setZValue(7)
            self.addItem(bar)

            # Nome da track
            txt = QGraphicsTextItem(label)
            txt.setFont(QFont("Segoe UI", 7, QFont.Bold))
            txt.setDefaultTextColor(QColor(C["text2"]))
            txt.setPos(7, cy - 12)
            txt.setZValue(7)
            self.addItem(txt)

            # Sub-label ou volume %
            track_key = {"VIDEO": None, "FX": None, "VOICE": "voice",
                         "SFX": "sfx", "MUSIC": "music", "AUDIO": "audio"}.get(label)
            if track_key and hasattr(project, 'track_volumes'):
                vol = project.track_volumes.get(track_key, 1.0)
                sub_txt = QGraphicsTextItem(f"{int(vol * 100)}%")
                sub_txt.setFont(QFont("Consolas", 6, QFont.Bold))
                sub_txt.setDefaultTextColor(QColor(C["text3"]))
            else:
                sub_txt = QGraphicsTextItem(sub)
                sub_txt.setFont(QFont("Segoe UI", 6))
                sub_txt.setDefaultTextColor(QColor(C["text3"]))
            sub_txt.setPos(7, cy + 1)
            sub_txt.setZValue(7)
            self.addItem(sub_txt)

    # ============================================================
    # CLIPS DE VIDEO
    # ============================================================

    def _draw_clips(self, project, zoom, lbl_w):
        vy, vh = self._track_positions["video"]
        current_time = 0.0
        clips = sorted(project.clips, key=lambda c: c.position)
        drag = self._interaction
        dragging_id = drag._drag_target.id if drag._drag_mode == "clip_move" and drag._drag_target else None
        selected_id = getattr(self.tl, '_selected_clip_id', None)

        for clip in clips:
            x = lbl_w + int(current_time * zoom)
            w = int(clip.duration * zoom)
            is_dragging = (clip.id == dragging_id)
            is_selected = is_dragging or (clip.id == selected_id)
            item = ClipGraphicsItem(clip, x, vy, w, vh, selected=is_selected)
            self.addItem(item)
            if is_dragging:
                drag._drag_clip_item = item
                item.setZValue(10)
            current_time += clip.duration

    # ============================================================
    # DIAMONDS (losangos FX entre clips)
    # ============================================================

    def _draw_diamonds(self, project, zoom, lbl_w):
        """Desenha losangos na track FX entre cada par de clips (dentro da faixa)."""
        ty, th = self._track_positions["fx"]
        tcy = ty + th / 2
        clips = sorted(project.clips, key=lambda c: c.position)
        current_time = 0.0
        marked = self._interaction._marked_diamonds if hasattr(self, '_interaction') else set()
        # Tamanho do losango limitado a metade da altura da faixa
        max_sz = max(4, int(th / 2 - 2))
        sz = min(8, max_sz)

        for clip in clips:
            if clip.position > 0:
                dx = lbl_w + int(current_time * zoom)
                diamond_id = f"diamond_{clip.position}"
                is_marked = diamond_id in marked
                diamond = _DiamondItem(dx, tcy, sz, clip.position, is_marked)
                self.addItem(diamond)
            current_time += clip.duration

    # ============================================================
    # STORYBOARD MARKERS
    # ============================================================

    def _draw_storyboard_markers(self, project, zoom, lbl_w, scene_h):
        """Desenha checkpoints do storyboard como marcadores na ruler."""
        if not getattr(project, '_storyboard_applied', False):
            return
        scenes = project.world.scenes
        if not scenes:
            return

        ruler_h = self.tl.RULER_H
        current_time = 0.0

        for i, scene in enumerate(scenes):
            dur = float(scene.get("duration", 5))
            x = lbl_w + int(current_time * zoom)

            # Linha vertical pontilhada
            line = QGraphicsLineItem(x, ruler_h, x, scene_h)
            line.setPen(QPen(QColor(C["gold"]), 1, Qt.DashDotLine))
            line.setZValue(-5)
            self.addItem(line)

            # Badge circular com hover
            badge = _StoryboardBadge(x, ruler_h, i, scene)
            self.addItem(badge)

            current_time += dur

    # ============================================================
    # TRACK ITEMS (audio, fx, voice, sfx, music)
    # ============================================================

    def _draw_track_items(self, project, zoom, lbl_w):
        selected_id = getattr(self.tl, '_selected_track_item_id', None)
        for track_name in ("fx", "voice", "sfx", "music", "audio"):
            ty, th = self._track_positions[track_name]
            color = next(c[2] for c in TRACK_CONFIG if c[0] == track_name)
            items = sorted(project.get_track_items(track_name), key=lambda i: i.start_time)

            for ti in items:
                x = lbl_w + int(ti.start_time * zoom)
                w = max(4, int(ti.duration * zoom))
                is_selected = (ti.id == selected_id)

                if track_name == "fx":
                    gitem = _FxTrackItem(ti, x, ty, w, th, color)
                else:
                    gitem = TrackGraphicsItem(ti, x, ty, w, th, color, selected=is_selected)
                self.addItem(gitem)

    # ============================================================
    # MOUSE — delegado para SceneInteraction
    # ============================================================

    def mouseDoubleClickEvent(self, event):
        pos = event.scenePos()
        # Undo o toggle do primeiro clique antes de selecionar todos
        self._interaction._undo_last_diamond_toggle()
        if self._interaction.on_double_click(pos):
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        pos = event.scenePos()
        if self._interaction.on_press(pos, event.button()):
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.scenePos()
        if self._interaction.on_move(pos):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        pos = event.scenePos()
        if self._interaction.on_release(pos):
            event.accept()
            return
        super().mouseReleaseEvent(event)


# ============================================================
# ITEMS AUXILIARES
# ============================================================

class _DiamondItem(QGraphicsItem):
    """Losango na track FX (marcador de transição entre clips)."""

    def __init__(self, x, cy, size, position, is_marked=False):
        super().__init__()
        self._x = x
        self._cy = cy
        self._sz = size
        self._position = position
        self._hovered = False
        self._marked = is_marked
        self.setAcceptHoverEvents(True)
        self.setZValue(3)

    def boundingRect(self):
        sz = self._sz + 4
        return QRectF(self._x - sz, self._cy - sz, sz * 2, sz * 2)

    def paint(self, painter: QPainter, option, widget=None):
        x, cy, sz = self._x, self._cy, self._sz
        if self._hovered:
            sz = min(12, sz + 4)
            painter.setPen(QPen(QColor("#bb77ff"), 2))
            painter.setBrush(QBrush(QColor("#3a1a6a")))
        elif self._marked:
            sz = 10
            # Glow externo neon
            painter.setPen(QPen(QColor("#00ffee"), 1))
            painter.setBrush(Qt.NoBrush)
            outer = QPolygonF([
                QPointF(x - sz - 2, cy), QPointF(x, cy - sz - 2),
                QPointF(x + sz + 2, cy), QPointF(x, cy + sz + 2),
            ])
            painter.drawPolygon(outer)
            # Preenchido
            painter.setPen(QPen(QColor("#bb77ff"), 2))
            painter.setBrush(QBrush(QColor("#6b3fa0")))
        else:
            painter.setPen(QPen(QColor("#6b3fa0"), 2))
            painter.setBrush(QBrush(QColor("#2a1a4a")))

        poly = QPolygonF([
            QPointF(x - sz, cy), QPointF(x, cy - sz),
            QPointF(x + sz, cy), QPointF(x, cy + sz),
        ])
        painter.drawPolygon(poly)

        # Ícone ✓ se marcado
        if self._marked:
            painter.setPen(QPen(QColor("#00ffee")))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(QPointF(x - 4, cy + 4), "\u2713")

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()


class _StoryboardBadge(QGraphicsItem):
    """Badge circular de storyboard com hover glow."""

    def __init__(self, x, ruler_h, index, scene):
        super().__init__()
        self._x = x
        self._r = 8
        self._cy = ruler_h - self._r - 2
        self._index = index
        self._scene_data = scene
        self._hovered = False
        self.setAcceptHoverEvents(True)
        self.setZValue(8)
        self.setToolTip(f"Cena {index+1}: {scene.get('visual', '')[:40]}")

    def boundingRect(self):
        r = self._r + 4
        return QRectF(self._x - r, self._cy - r, r * 2, r * 2)

    def paint(self, painter: QPainter, option, widget=None):
        x, cy, r = self._x, self._cy, self._r
        from PySide6.QtCore import QPointF as P

        if self._hovered:
            # Glow neon
            painter.setPen(QPen(QColor("#00ffee"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(P(x, cy), r + 3, r + 3)
            # Badge
            painter.setPen(QPen(QColor("#00ffee"), 2))
            painter.setBrush(QBrush(QColor("#ffd700")))
            painter.drawEllipse(P(x, cy), r + 1, r + 1)
        else:
            painter.setPen(QPen(QColor("#ffd700"), 1))
            painter.setBrush(QBrush(QColor("#c89b3c")))
            painter.drawEllipse(P(x, cy), r, r)

        # Número
        painter.setPen(QPen(QColor("#0a0a0f")))
        painter.setFont(QFont("Consolas", 8 if not self._hovered else 9, QFont.Bold))
        painter.drawText(P(x - 4, cy + 4), str(self._index + 1))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.ArrowCursor)
        self.update()


class _FxTrackItem(QGraphicsItem):
    """Item FX com efeitos visuais internos (fade, glitch, flash, etc)."""

    def __init__(self, track_item, x, y, w, h, color):
        super().__init__()
        self.track_item = track_item
        self._x = x
        self._y = y
        self._w = w
        self._h = h
        self._color = QColor(color)
        self._hovered = False
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

    def boundingRect(self):
        return QRectF(self._x, self._y, self._w, self._h)

    def paint(self, painter: QPainter, option, widget=None):
        x, y, w, h = self._x, self._y + 3, self._w, self._h - 6
        color = self._color

        # Fundo
        if self._hovered:
            painter.setPen(QPen(QColor("#00ffee"), 2))
        else:
            painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(QColor("#1a0a2a")))
        painter.drawRect(QRectF(x, y, w, h))

        # Efeito visual interno baseado no nome
        name = self.track_item.name.lower()
        ix1, ix2 = x + 4, x + w - 4
        mid_y = y + h / 2

        painter.setPen(QPen(color.darker(130), 1))

        if "fade in" in name:
            for i in range(0, int(ix2 - ix1), 3):
                alpha = i / max(1, ix2 - ix1)
                if alpha < 0.8:
                    painter.drawLine(QPointF(ix1 + i, y + 2), QPointF(ix1 + i, y + h - 2))
        elif "fade out" in name:
            for i in range(0, int(ix2 - ix1), 3):
                alpha = 1.0 - i / max(1, ix2 - ix1)
                if alpha < 0.8:
                    painter.drawLine(QPointF(ix1 + i, y + 2), QPointF(ix1 + i, y + h - 2))
        elif "flash" in name:
            cx = (ix1 + ix2) / 2
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                ex = cx + 8 * math.cos(rad)
                ey = mid_y + 6 * math.sin(rad)
                painter.drawLine(QPointF(cx, mid_y), QPointF(ex, ey))
        elif "glitch" in name:
            import random
            rng = random.Random(hash(self.track_item.id))
            for gy in range(int(y + 3), int(y + h - 3), 4):
                gx = ix1 + rng.randint(0, max(1, int(ix2 - ix1) // 2))
                gw = rng.randint(4, min(12, int(ix2 - gx)))
                painter.drawLine(QPointF(gx, gy), QPointF(gx + gw, gy))
        elif "wipe" in name:
            if "right" in name:
                painter.drawLine(QPointF(ix1, mid_y), QPointF(ix2, mid_y))
            else:
                painter.drawLine(QPointF(ix2, mid_y), QPointF(ix1, mid_y))
        elif "dissolve" in name or "cross" in name:
            painter.drawLine(QPointF(ix1, y + 2), QPointF(ix2, y + h - 2))
            painter.drawLine(QPointF(ix1, y + h - 2), QPointF(ix2, y + 2))
        else:
            for i in range(0, int(ix2 - ix1), 6):
                painter.drawLine(QPointF(ix1 + i, y + h - 2), QPointF(ix1 + i + 4, y + 2))

        # Label em baixo
        painter.setPen(QPen(color))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        painter.drawText(QPointF(x + 5, y + h - 4), self.track_item.name[:18])

        # Trim handles (bordas coloridas)
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(color))
        painter.drawRect(QRectF(x, y, 4, h))
        painter.drawRect(QRectF(x + w - 4, y, 4, h))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def hoverMoveEvent(self, event):
        """Cursor de resize nas bordas."""
        local_x = event.scenePos().x() - self._x
        if local_x <= 6 or (self._w - local_x) <= 6:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
