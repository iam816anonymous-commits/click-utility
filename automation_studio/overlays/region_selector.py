from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QFont

from automation_studio.capture.capture_engine import CaptureEngine

class CoordinateCaptureOverlay(QWidget):
    """
    Transparent fullscreen overlay that follows the mouse cursor, showing a crosshair,
    a magnifier/snipping visual hint, and the current coordinates. Click to capture.
    """
    coordinate_captured = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.cursor_pos = None

    def show_overlay(self):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.cursor_pos = None
        self.show()

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.globalPosition().toPoint()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.globalPosition().toPoint()
            self.hide()
            self.coordinate_captured.emit(pos.x(), pos.y())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 50))

        if self.cursor_pos:
            cx, cy = self.cursor_pos.x(), self.cursor_pos.y()

            # Draw crosshairs
            pen = QPen(QColor(239, 68, 68), 1, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(0, cy, self.width(), cy)
            painter.drawLine(cx, 0, cx, self.height())

            # Target ring
            painter.drawEllipse(cx - 10, cy - 10, 20, 20)

            # Magnifier visual card
            box_w, box_h = 160, 60
            bx = cx + 15 if cx + 15 + box_w < self.width() else cx - 15 - box_w
            by = cy + 15 if cy + 15 + box_h < self.height() else cy - 15 - box_h

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(17, 24, 39, 220))
            painter.drawRoundedRect(bx, by, box_w, box_h, 4, 4)

            painter.setPen(QColor(253, 224, 71))
            painter.setFont(QFont("Courier New", 9, QFont.Bold))
            painter.drawText(bx + 10, by + 20, f"X: {cx}")
            painter.drawText(bx + 10, by + 35, f"Y: {cy}")
            painter.drawText(bx + 10, by + 50, "Click to Capture")
