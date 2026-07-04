"""Widgets compartilhados do Style Panel."""

from PySide6.QtWidgets import QFrame, QTextEdit, QSizePolicy
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen


class DraggableDivider(QFrame):
    """Divisoria vertical arrastavel entre colunas do grid."""

    def __init__(self, index, panel, parent=None):
        super().__init__(parent)
        self._index = index
        self._panel = panel
        self._dragging = False
        self._start_x = 0
        self._start_left_w = 0
        self._start_right_w = 0
        self.setMinimumWidth(4)
        self.setMaximumWidth(4)
        self.setMouseTracking(True)
        self.setCursor(Qt.SplitHCursor)
        self.setStyleSheet("background: #2a2a4a;")

    def enterEvent(self, event):
        if not self._dragging:
            self.setMinimumWidth(8)
            self.setMaximumWidth(8)
            self.setStyleSheet("background: #c89b3c;")

    def leaveEvent(self, event):
        if not self._dragging:
            self.setMinimumWidth(4)
            self.setMaximumWidth(4)
            self.setStyleSheet("background: #2a2a4a;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            data_cols = self._panel._data_cols
            left_idx = self._index - 1
            right_idx = self._index
            if left_idx < 0 or right_idx >= len(data_cols):
                return
            self._dragging = True
            self._start_x = event.globalPosition().x()
            self.setStyleSheet("background: #ffd700;")
            self.setMinimumWidth(8)
            self.setMaximumWidth(8)
            grid = self._panel._grid_ref
            self._left_idx = left_idx
            self._right_idx = right_idx
            self._start_left_w = grid.cellRect(0, data_cols[left_idx]).width() or 100
            self._start_right_w = grid.cellRect(0, data_cols[right_idx]).width() or 100

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        grid = self._panel._grid_ref
        data_cols = self._panel._data_cols
        dx = int(event.globalPosition().x() - self._start_x)
        new_left = max(40, int(self._start_left_w + dx))
        new_right = max(40, int(self._start_right_w - dx))
        grid.setColumnMinimumWidth(data_cols[self._left_idx], new_left)
        grid.setColumnMinimumWidth(data_cols[self._right_idx], new_right)
        grid.setColumnStretch(data_cols[self._left_idx], 0)
        grid.setColumnStretch(data_cols[self._right_idx], 0)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.setMinimumWidth(4)
        self.setMaximumWidth(4)
        self.setStyleSheet("background: #2a2a4a;")


class AutoResizeTextEdit(QTextEdit):
    """QTextEdit que quebra linha na borda e expande altura automaticamente."""

    def __init__(self, text="", color="#0ac8b9", border_color="#1a3a3a", parent=None):
        super().__init__(parent)

        self.setStyleSheet(
            f"QTextEdit {{ background: #080a14; color: {color}; "
            f"border: 2px solid {border_color}; border-radius: 4px; "
            f"font-family: Consolas; font-size: 9pt; font-weight: bold; "
            f"padding: 2px 4px; }}"
            f"QTextEdit:hover {{ border: 2px solid {color}; }}"
            f"QTextEdit:focus {{ border: 2px solid {color}; }}")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setTabChangesFocus(True)
        self.setAcceptRichText(False)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumWidth(40)
        self.setFixedHeight(28)
        self.document().documentLayout().documentSizeChanged.connect(self._on_doc_size)
        self.textChanged.connect(self._force_width)
        if text:
            self.setPlainText(text)

    def _force_width(self):
        w = self.viewport().width()
        if w > 0:
            self.document().setTextWidth(w)

    def _on_doc_size(self, size):
        m = self.document().documentMargin()
        h = int(size.height() + 2 * m)
        h = max(28, min(200, h))
        self.setFixedHeight(h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.viewport().width()
        if w > 0:
            self.document().setTextWidth(w)

    def get_text(self):
        return self.toPlainText().strip()


class FlexTextEdit(QTextEdit):
    """QTextEdit auto-resize para uso em QScrollArea/QVBoxLayout."""

    def __init__(self, text="", color="#0ac8b9", border_color="#1a3a3a",
                 font_size="9pt", font_weight="bold", bg="#080a14",
                 border_px="2px", border_radius="4px",
                 hover_color=None, focus_color=None, focus_px=None,
                 min_lines=4, parent=None):
        super().__init__(parent)
        self._border_color   = border_color
        self._hover_color    = hover_color or color
        self._focus_color    = focus_color or color
        self._border_radius  = int(''.join(filter(str.isdigit, border_radius)) or 4)
        self._border_w       = int(''.join(filter(str.isdigit, border_px)) or 2)
        self._is_focused     = False
        self._is_hovered     = False
        self.setStyleSheet(
            f"QTextEdit {{ background: {bg}; color: {color}; border: none; "
            f"border-radius: {border_radius}; "
            f"font-family: Consolas; font-size: {font_size}; font-weight: {font_weight}; "
            f"padding: 4px 6px; }}")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setTabChangesFocus(True)
        self.setAcceptRichText(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(self._on_doc_size)
        self.textChanged.connect(self._on_text_change)
        self._pending_text = text
        self._ready = False
        self._min_lines = min_lines
        self._min_h = 24
        self.setFixedHeight(24)

    def _current_border_color(self):
        if self._is_focused:
            return self._focus_color
        if self._is_hovered:
            return self._hover_color
        return self._border_color

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self.viewport())
        if not p.isActive():
            return
        p.setRenderHint(QPainter.Antialiasing)
        bw = self._border_w
        r  = self._border_radius
        rect = QRectF(self.viewport().rect()).adjusted(bw/2, bw/2, -bw/2, -bw/2)
        pen = QPen(QColor(self._current_border_color()), bw)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, r, r)
        p.end()

    def focusInEvent(self, event):
        self._is_focused = True
        self.viewport().update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._is_focused = False
        self.viewport().update()
        super().focusOutEvent(event)

    def enterEvent(self, event):
        self._is_hovered = True
        self.viewport().update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.viewport().update()
        super().leaveEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self._ready:
            return
        self._ready = True
        lh = self.fontMetrics().lineSpacing()
        self._min_h = lh * self._min_lines + 10
        self.setFixedHeight(self._min_h)
        if self._pending_text:
            self.setPlainText(self._pending_text)
            self._pending_text = ""

    def _on_text_change(self):
        w = self.viewport().width()
        if w > 0:
            self.document().setTextWidth(w)

    def _on_doc_size(self, size):
        if not self._ready:
            return
        m = self.document().documentMargin()
        h = int(size.height() + 2 * m)
        self.setFixedHeight(max(self._min_h, h))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.viewport().width()
        if w > 0:
            self.document().setTextWidth(w)

    def insertFromMimeData(self, source):
        self.insertPlainText(source.text())

    def get_text(self):
        return self.toPlainText().strip()
