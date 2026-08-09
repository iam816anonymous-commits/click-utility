from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QCursor

class MatchHighlightOverlay(QWidget):
    """
    Frameless transparent click-through overlay to temporarily draw green target highlights
    on-screen over matched locations.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.rects = []
        self.clear_timer = QTimer(self)
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self.clear_highlights)

    def highlight_matches(self, rects: list):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.rects = rects
        self.show()
        self.update()
        self.clear_timer.start(1000)

    def clear_highlights(self):
        self.rects = []
        self.hide()

    def paintEvent(self, event):
        if not self.rects:
            return
        painter = QPainter(self)
        pen = QPen(QColor(16, 185, 129), 3) # Emerald green
        painter.setPen(pen)
        painter.setBrush(QColor(16, 185, 129, 30))

        for (x, y, w, h) in self.rects:
            painter.drawRect(x, y, w, h)


class DebugOverlay(QWidget):
    """
    Stage 9 / Visual Debug HUD Overlay.
    Transparent, non-blocking click-through overlay showing green matched bounds,
    blue search region bounds, yellow centers, red click crosshairs, and purple cursor tracking dots.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.rects = []
        self.click_point = None
        self.meta_text = ""

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_overlay)

    def show_debug_info(self, rects: list, click_point: tuple, meta_text: str):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.rects = rects
        self.click_point = click_point
        self.meta_text = meta_text

        self.show()
        self.update()
        self.hide_timer.start(1500)

    def hide_overlay(self):
        self.rects = []
        self.click_point = None
        self.meta_text = ""
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))

        painter.setFont(QFont("Courier New", 9, QFont.Bold))

        pen_blue = QPen(QColor(59, 130, 246), 2, Qt.DashLine)
        painter.setPen(pen_blue)
        painter.setBrush(QColor(59, 130, 246, 10))
        painter.drawRect(5, 5, self.width() - 10, self.height() - 10)
        painter.drawText(15, self.height() - 25, "🟦 Search region bounds")

        pen_green = QPen(QColor(16, 185, 129), 3)
        painter.setPen(pen_green)
        painter.setBrush(QColor(16, 185, 129, 20))
        for (x, y, w, h) in self.rects:
            painter.drawRect(x, y, w, h)
            cx_center = x + w // 2
            cy_center = y + h // 2

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(253, 224, 71)) # Yellow
            painter.drawEllipse(QPoint(cx_center, cy_center), 6, 6)

            painter.setPen(QColor(253, 224, 71))
            painter.drawText(cx_center + 10, cy_center - 10, f"🟡 Center: ({cx_center}, {cy_center})")

            painter.setPen(pen_green)
            painter.drawText(x + 5, y + 20, f"🟩 Target Template: {w}x{h}")

        if self.click_point:
            cx, cy = self.click_point
            pen_red = QPen(QColor(239, 68, 68), 2)
            painter.setPen(pen_red)
            painter.drawLine(cx - 20, cy, cx + 20, cy)
            painter.drawLine(cx, cy - 20, cx, cy + 20)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(cx, cy), 8, 8)
            painter.drawText(cx + 15, cy + 15, f"❌ Target Click Point: ({cx}, {cy})")

        cursor_pos = QCursor.pos()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(168, 85, 247)) # Purple
        painter.drawEllipse(cursor_pos, 7, 7)
        painter.setPen(QColor(168, 85, 247))
        painter.drawText(cursor_pos.x() + 15, cursor_pos.y() - 10, f"🟪 Cursor position: ({cursor_pos.x()}, {cursor_pos.y()})")

        if self.meta_text:
            painter.setFont(QFont("Courier New", 10, QFont.Bold))
            fm = painter.fontMetrics()
            lines = self.meta_text.strip().split("\n")
            max_w = max(fm.horizontalAdvance(line) for line in lines)
            total_h = len(lines) * fm.height()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(17, 24, 39, 230))
            painter.drawRoundedRect(30, 40, max_w + 30, total_h + 30, 8, 8)

            painter.setPen(QColor(253, 224, 71))
            curr_y = 65
            for line in lines:
                painter.drawText(45, curr_y, line)
                curr_y += fm.height()
