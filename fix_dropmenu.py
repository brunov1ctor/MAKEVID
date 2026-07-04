with open('makevid/qt/topbar.py', encoding='utf-8') as f:
    c = f.read()

old = '''class _DropMenu(QWidget):
    """
    Dropdown 100% Qt — sem janela nativa, sem flash.
    Filho do centralWidget da QMainWindow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropMenu")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#DropMenu {{ background: rgba(14,22,42,224); "
            f"border: 1px solid rgba(255,255,255,46); border-radius: 12px; }}"
        )
        self.hide()

        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(1)
        self._items = []'''

new = '''class _DropMenu(QWidget):
    """
    Dropdown 100% Qt — sem janela nativa, sem flash.
    Filho do centralWidget da QMainWindow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropMenu")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.hide()

        self._vbox = QVBoxLayout(self)
        self._vbox.setContentsMargins(6, 6, 6, 6)
        self._vbox.setSpacing(1)
        self._items = []'''

c2 = c.replace(old, new)
print('DropMenu init replaced:', c2 != c)

old2 = '''    def paintEvent(self, event):
        # Deixa o QSS cuidar do fundo; apenas garante o raise
        super().paintEvent(event)'''

new2 = '''    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 12, 12)
        p.fillPath(path, QColor(14, 22, 42, 230))
        p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
        p.drawPath(path)
        p.end()'''

c3 = c2.replace(old2, new2)
print('paintEvent replaced:', c3 != c2)

with open('makevid/qt/topbar.py', 'w', encoding='utf-8') as f:
    f.write(c3)
print('done')
