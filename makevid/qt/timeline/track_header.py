"""Track Header Widget - Painel fixo de labels laterais da timeline.

Completamente separado da QGraphicsScene. Não participa de hover,
drag ou colisão. Sincroniza altura das tracks com a cena.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient

from makevid.qt.theme import C

# Faixas de audio que tem medidor de nivel
_METER_TRACKS = {"voice", "sfx", "music", "audio"}
# Largura da barra de nivel em pixels
_METER_W = 6


class TrackHeaderWidget(QWidget):
    """Coluna esquerda fixa com os labels VIDEO, FX, VOICE, etc."""

    def __init__(self, tl, parent=None):
        super().__init__(parent)
        self.tl = tl
        self._track_pos = {}   # {key: (y, h)} — sincronizado com a cena
        self._label_pos = {}   # idem
        # Niveis suavizados por faixa (dBFS, -60..0)
        self._levels: dict = {"voice": -60.0, "sfx": -60.0, "music": -60.0, "audio": -60.0}
        self.setFixedWidth(tl.LBL_W)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Timer que le os niveis do player e agenda repaint
        self._meter_timer = QTimer(self)
        self._meter_timer.setInterval(33)  # ~30fps
        self._meter_timer.timeout.connect(self._update_levels)
        self._meter_timer.start()

    def sync(self, track_pos: dict, label_pos: dict):
        """Recebe as posições calculadas pela cena e agenda repaint."""
        self._track_pos = track_pos
        self._label_pos = label_pos
        self.update()

    def _update_levels(self):
        """Le os niveis do player e suaviza com decay para o medidor."""
        try:
            app = self.window()
            player = app.preview.player
            raw = player.track_levels
        except Exception:
            raw = {}

        changed = False
        for track in _METER_TRACKS:
            target = raw.get(track, -60.0)
            current = self._levels.get(track, -60.0)
            # Ataque rapido, decay lento
            if target > current:
                new = target
            else:
                new = current - 3.0  # decay ~3 dB por frame a 30fps
            new = max(-60.0, new)
            if abs(new - current) > 0.1:
                self._levels[track] = new
                changed = True

        if changed:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        rh = self.tl.RULER_H

        # Fundo do painel
        painter.setPen(Qt.NoPen)
        painter.fillRect(0, 0, w, h, QColor(28, 46, 74, 180))

        # Borda direita
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.drawLine(w - 1, 0, w - 1, h)

        # Área do ruler (vazia, só fundo)
        painter.fillRect(0, 0, w, rh, QColor(13, 16, 32, 200))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.drawLine(0, rh - 1, w, rh - 1)

        from makevid.qt.timeline.timeline_scene import _TRACKS
        collapsed = getattr(self.tl, 'collapsed_tracks', set())

        for key, label, color, _, sub in _TRACKS:
            if key not in self._label_pos:
                continue
            y, lh = self._label_pos[key]
            is_collapsed = key in collapsed
            cy = y + lh / 2

            # Barra colorida
            bar_color = QColor(color)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_color)
            painter.drawRect(10, int(y + 2), 4, int(lh - (2 if is_collapsed else 4)))

            # Botão colapsar (triângulo)
            arrow_color = QColor(255, 255, 255, 150)
            painter.setBrush(arrow_color)
            painter.setPen(Qt.NoPen)
            ax, ay = 2, int(cy - 3)
            if not is_collapsed:
                pts = [(ax, ay), (ax, ay + 7), (ax + 6, ay + 3)]
            else:
                pts = [(ax, ay), (ax + 7, ay), (ax + 3, ay + 6)]
            from PySide6.QtGui import QPolygon
            from PySide6.QtCore import QPoint
            painter.drawPolygon([QPoint(x, y_) for x, y_ in pts])

            # Label principal
            painter.setPen(QPen(QColor(C["text2"] if not is_collapsed else C["text3"])))
            font = QFont("Segoe UI", 7, QFont.Bold)
            painter.setFont(font)
            label_y = cy - (12 if not is_collapsed else 6)
            painter.drawText(16, int(label_y + 9), label)

            # Sub-label / volume
            if not is_collapsed:
                vol_map = {"VOICE": "voice", "SFX": "sfx", "MUSIC": "music", "AUDIO": "audio"}
                tk = vol_map.get(label)
                project = self.tl.project
                if tk and project and hasattr(project, "track_volumes"):
                    sub_txt = f"{int(project.track_volumes.get(tk, 1.0) * 100)}%"
                else:
                    sub_txt = sub
                painter.setPen(QPen(QColor(C["text3"])))
                painter.setFont(QFont("Segoe UI", 6))
                painter.drawText(16, int(cy + 9), sub_txt)

                # Medidor de nivel dB
                if tk in _METER_TRACKS:
                    db = self._levels.get(tk, -60.0)
                    # Normaliza -60..0 dBFS para 0..1
                    ratio = max(0.0, min(1.0, (db + 60.0) / 60.0))
                    bar_h = int((lh - 8) * ratio)
                    bar_x = w - _METER_W - 2
                    bar_top = int(y + 4)
                    bar_bot = int(y + lh - 4)

                    # Fundo da barra
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(0, 0, 0, 80))
                    painter.drawRect(bar_x, bar_top, _METER_W, bar_bot - bar_top)

                    # Gradiente verde -> amarelo -> vermelho
                    if bar_h > 0:
                        grad = QLinearGradient(bar_x, bar_bot, bar_x, bar_bot - (bar_bot - bar_top))
                        grad.setColorAt(0.0,  QColor(0, 200, 80))
                        grad.setColorAt(0.7,  QColor(220, 200, 0))
                        grad.setColorAt(1.0,  QColor(220, 40, 40))
                        painter.setBrush(QBrush(grad))
                        painter.drawRect(bar_x, bar_bot - bar_h, _METER_W, bar_h)

                    # Valor em dB
                    painter.setPen(QPen(QColor(C["text3"])))
                    painter.setFont(QFont("Consolas", 5))
                    db_txt = f"{int(db)}" if db > -60 else "-∞"
                    painter.drawText(bar_x - 1, bar_bot + 8, db_txt)

        painter.end()

    def mousePressEvent(self, event):
        """Clique no header: colapsar/expandir track ou ativar track."""
        pos = event.pos()
        from makevid.qt.timeline.timeline_scene import _TRACKS
        collapsed = self.tl.collapsed_tracks

        for key, *_ in _TRACKS:
            if key not in self._label_pos:
                continue
            y, lh = self._label_pos[key]
            cy = y + lh / 2
            # Área do botão colapsar
            if 0 <= pos.x() <= 10 and cy - 6 <= pos.y() <= cy + 6:
                if key in collapsed:
                    collapsed.discard(key)
                else:
                    collapsed.add(key)
                self.tl.rebuild_scene()
                return
            # Área do label → ativa track
            if y <= pos.y() <= y + lh:
                self.tl.set_active_track(key)
                return

        super().mousePressEvent(event)
