from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QPen, QColor

class TeachOverlay(QWidget):
    """
    Full-screen semi-transparent overlay to select a custom crop region for visual targets.
    """
    region_selected = Signal(int, int, int, int) # x, y, w, h

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.end_pos = None

    def show_overlay(self):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.start_pos = None
        self.end_pos = None
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.end_pos = self.start_pos
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.end_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x1 - x2)
            h = abs(y1 - y2)
            self.hide()
            if w > 5 and h > 5:
                self.region_selected.emit(x, y, w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            pen = QPen(QColor(168, 85, 247), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(168, 85, 247, 30))
            painter.drawRect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))
