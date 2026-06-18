"""Inpaint Panel Qt - Editor de mascara para inpainting por regiao."""

import numpy as np
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (
    QPainter, QColor, QImage, QPixmap, QPen, QBrush, QCursor
)

from makevid.qt.theme import C


class MaskCanvas(QWidget):
    """Canvas para pintar mascara sobre o frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame_pixmap = None
        self._mask = None  # numpy (H,W) uint8
        self._brush_size = 30
        self._eraser = False
        self._painting = False
        self._last_pos = None
        self.setMinimumSize(320, 200)
        self.setCursor(Qt.CrossCursor)

    def set_frame(self, frame: np.ndarray):
        """Define frame RGB (H,W,3) como fundo."""
        h, w, _ = frame.shape
        img = QImage(frame.data, w, h, w * 3, QImage.Format_RGB888)
        self._frame_pixmap = QPixmap.fromImage(img)
        self._mask = np.zeros((h, w), dtype=np.uint8)
        self.update()

    def get_mask(self) -> np.ndarray:
        return self._mask if self._mask is not None else np.zeros((1, 1), dtype=np.uint8)

    def clear_mask(self):
        if self._mask is not None:
            self._mask[:] = 0
            self.update()

    def set_brush_size(self, size):
        self._brush_size = size

    def set_eraser(self, on):
        self._eraser = on

    def paintEvent(self, event):
        p = QPainter(self)
        if self._frame_pixmap:
            scaled = self._frame_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ox = (self.width() - scaled.width()) // 2
            oy = (self.height() - scaled.height()) // 2
            p.drawPixmap(ox, oy, scaled)

            # Overlay mask
            if self._mask is not None:
                h, w = self._mask.shape
                mask_img = QImage(w, h, QImage.Format_ARGB32)
                mask_img.fill(QColor(0, 0, 0, 0))
                for y in range(h):
                    for x in range(0, w, 4):  # skip pixels for speed
                        if self._mask[y, x] > 0:
                            mask_img.setPixelColor(x, y, QColor(255, 0, 0, 100))
                mask_pix = QPixmap.fromImage(mask_img).scaled(
                    scaled.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                p.drawPixmap(ox, oy, mask_pix)
        else:
            p.fillRect(self.rect(), QColor("#0a0c18"))
            p.setPen(QColor(C['text3']))
            p.drawText(self.rect(), Qt.AlignCenter, "Nenhum frame carregado")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._painting = True
            self._last_pos = event.position().toPoint()
            self._draw_at(self._last_pos)

    def mouseMoveEvent(self, event):
        if self._painting:
            pos = event.position().toPoint()
            self._draw_at(pos)
            self._last_pos = pos

    def mouseReleaseEvent(self, event):
        self._painting = False
        self._last_pos = None

    def _draw_at(self, pos):
        if self._mask is None or self._frame_pixmap is None:
            return
        # Map widget coords to mask coords
        scaled = self._frame_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ox = (self.width() - scaled.width()) // 2
        oy = (self.height() - scaled.height()) // 2
        mx = pos.x() - ox
        my = pos.y() - oy
        if mx < 0 or my < 0 or mx >= scaled.width() or my >= scaled.height():
            return
        h, w = self._mask.shape
        fx = int(mx * w / scaled.width())
        fy = int(my * h / scaled.height())
        r = max(1, int(self._brush_size * w / scaled.width()))
        y1, y2 = max(0, fy - r), min(h, fy + r)
        x1, x2 = max(0, fx - r), min(w, fx + r)
        if self._eraser:
            self._mask[y1:y2, x1:x2] = 0
        else:
            self._mask[y1:y2, x1:x2] = 255
        self.update()


class InpaintPanel(QWidget):
    """Painel de inpainting com canvas de mascara e prompt."""

    closed = Signal()
    inpaint_requested = Signal(dict)  # {frame, mask, prompt}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setStyleSheet(f"background: {C['panel']};")
        self._frame = None
        self._build_ui()

    def _build_ui(self):
        L = QVBoxLayout(self)
        L.setContentsMargins(8, 8, 8, 8)
        L.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        lbl = QLabel("\U0001f3a8 INPAINT")
        lbl.setStyleSheet(f"color: {C['gold']}; font-size: 12pt; font-weight: bold;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        close_btn = QPushButton("X")
        close_btn.setFixedSize(24, 20)
        close_btn.setStyleSheet(f"background: {C['card']}; color: {C['text3']}; font-weight: bold;")
        close_btn.clicked.connect(self.closed.emit)
        hdr.addWidget(close_btn)
        L.addLayout(hdr)

        # Canvas
        self._canvas = MaskCanvas()
        self._canvas.setFixedHeight(180)
        L.addWidget(self._canvas)

        # Tools
        tools = QHBoxLayout()
        self._btn_brush = QPushButton("\U0001f58c Pincel")
        self._btn_brush.setCheckable(True)
        self._btn_brush.setChecked(True)
        self._btn_brush.setStyleSheet(f"background: {C['card']}; color: {C['cyan']}; font-weight: bold; border: 1px solid {C['cyan']}; border-radius: 4px; padding: 4px 8px;")
        self._btn_brush.clicked.connect(lambda: self._set_tool(False))
        tools.addWidget(self._btn_brush)

        self._btn_eraser = QPushButton("\u2702 Borracha")
        self._btn_eraser.setCheckable(True)
        self._btn_eraser.setStyleSheet(f"background: {C['card']}; color: {C['text2']}; font-weight: bold; border: 1px solid {C['border']}; border-radius: 4px; padding: 4px 8px;")
        self._btn_eraser.clicked.connect(lambda: self._set_tool(True))
        tools.addWidget(self._btn_eraser)

        btn_clear = QPushButton("Limpar")
        btn_clear.setStyleSheet(f"background: {C['card']}; color: #ff4444; border: 1px solid #ff4444; border-radius: 4px; padding: 4px 8px;")
        btn_clear.clicked.connect(self._canvas.clear_mask)
        tools.addWidget(btn_clear)
        L.addLayout(tools)

        # Brush size
        sz_row = QHBoxLayout()
        sz_row.addWidget(QLabel("Tamanho:"))
        self._sz_slider = QSlider(Qt.Horizontal)
        self._sz_slider.setRange(5, 80)
        self._sz_slider.setValue(30)
        self._sz_slider.valueChanged.connect(self._canvas.set_brush_size)
        sz_row.addWidget(self._sz_slider)
        L.addLayout(sz_row)

        # Prompt
        L.addWidget(self._sub("Prompt (o que gerar na regiao):"))
        self._prompt = QTextEdit()
        self._prompt.setFixedHeight(50)
        self._prompt.setPlaceholderText("Descreva o que colocar na regiao pintada...")
        self._prompt.setStyleSheet(f"background: {C['input']}; color: {C['text']}; border: 2px solid {C['gold']}; border-radius: 6px; font-size: 10pt;")
        L.addWidget(self._prompt)

        # Generate
        gen_btn = QPushButton("INPAINT")
        gen_btn.setFixedHeight(36)
        gen_btn.setStyleSheet(f"background: {C['gold']}; color: #0a0a0f; font-size: 12pt; font-weight: bold; border-radius: 4px;")
        gen_btn.clicked.connect(self._do_inpaint)
        L.addWidget(gen_btn)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {C['text3']}; font-size: 9pt;")
        L.addWidget(self._status)
        L.addStretch()

    def set_frame(self, frame: np.ndarray):
        """Define frame RGB para editar."""
        self._frame = frame
        self._canvas.set_frame(frame)

    def _set_tool(self, eraser):
        self._canvas.set_eraser(eraser)
        self._btn_brush.setChecked(not eraser)
        self._btn_eraser.setChecked(eraser)

    def _do_inpaint(self):
        if self._frame is None:
            self._status.setText("Carregue um frame primeiro")
            return
        prompt = self._prompt.toPlainText().strip()
        if not prompt:
            self._status.setText("Digite um prompt")
            return
        mask = self._canvas.get_mask()
        if mask.max() == 0:
            self._status.setText("Pinte a regiao a editar")
            return
        self._status.setText("Processando...")
        self.inpaint_requested.emit({"frame": self._frame, "mask": mask, "prompt": prompt})

    def on_done(self, result_frame):
        self._frame = result_frame
        self._canvas.set_frame(result_frame)
        self._status.setText("\u2714 Inpaint concluido!")
        self._status.setStyleSheet(f"color: {C['cyan']}; font-size: 9pt;")

    def on_error(self, msg):
        self._status.setText(f"Erro: {msg[:40]}")
        self._status.setStyleSheet(f"color: #ff4444; font-size: 9pt;")

    def _sub(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; font-weight: bold;")
        return lbl
