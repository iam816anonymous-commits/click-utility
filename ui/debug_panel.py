import os
import sys
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QApplication
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPixmap

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
        """
        Expects rects to be a list of Tuples (x, y, w, h)
        """
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.rects = rects
        self.show()
        self.update()
        self.clear_timer.start(1500)

    def clear_highlights(self):
        self.rects = []
        self.hide()

    def paintEvent(self, event):
        if not self.rects:
            return
        painter = QPainter(self)
        pen = QPen(QColor(16, 185, 129), 3) # Emerald green box outline
        painter.setPen(pen)
        painter.setBrush(QColor(16, 185, 129, 30)) # Translucent fill

        for (x, y, w, h) in self.rects:
            painter.drawRect(x, y, w, h)


class DebugPanel(QFrame):
    """
    HUD debugger panel showing matched states, template, coordinates, and execution timings.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
            "QLabel { color: #E5E7EB; font-family: 'Segoe UI'; font-size: 11px; }"
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.title = QLabel("<h3>🔍 Live Match & Rule Debugger</h3>")
        layout.addWidget(self.title)

        self.template_preview = QLabel("No template loaded.")
        self.template_preview.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.template_preview.setAlignment(Qt.AlignCenter)
        self.template_preview.setFixedSize(120, 100)

        info_sub_layout = QVBoxLayout()
        self.state_lbl = QLabel("<b>Status:</b> Idle")
        self.conf_lbl = QLabel("<b>Match Confidence:</b> --%")
        self.coord_lbl = QLabel("<b>Target Click Coords:</b> --")
        self.region_lbl = QLabel("<b>Restricted Search Area:</b> Full Screen")
        self.timing_lbl = QLabel("<b>Execution Time:</b> -- ms")

        info_sub_layout.addWidget(self.state_lbl)
        info_sub_layout.addWidget(self.conf_lbl)
        info_sub_layout.addWidget(self.coord_lbl)
        info_sub_layout.addWidget(self.region_lbl)
        info_sub_layout.addWidget(self.timing_lbl)

        row = QHBoxLayout()
        row.addWidget(self.template_preview)
        row.addLayout(info_sub_layout)
        layout.addLayout(row)

    def update_debug_view(self, template_path, state, conf, click_coords, region_info, execution_time):
        if template_path and os.path.exists(template_path):
            pix = QPixmap(template_path)
            self.template_preview.setPixmap(pix.scaled(120, 100, Qt.KeepAspectRatio))
        else:
            self.template_preview.setText("No Image")

        self.state_lbl.setText(f"<b>Status:</b> {state}")
        self.conf_lbl.setText(f"<b>Match Confidence:</b> {conf}%")
        self.coord_lbl.setText(f"<b>Target Click Coords:</b> {click_coords}")
        self.region_lbl.setText(f"<b>Restricted Search Area:</b> {region_info}")
        self.timing_lbl.setText(f"<b>Execution Time:</b> {execution_time} ms")


class DebugOverlay(QWidget):
    """
    Transparent fullscreen overlay rendering green template bounding boxes,
    and precise red clicks crosshairs on actual screen coordinates.
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
        self.hide_timer.start(1000)

    def hide_overlay(self):
        self.rects = []
        self.click_point = None
        self.meta_text = ""
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))

        # Draw bounding boxes (Emerald Green)
        pen_green = QPen(QColor(16, 185, 129), 3)
        painter.setPen(pen_green)
        painter.setBrush(QColor(16, 185, 129, 20))
        for (x, y, w, h) in self.rects:
            painter.drawRect(x, y, w, h)

        # Draw target click point (Red Crosshair)
        if self.click_point:
            cx, cy = self.click_point
            pen_red = QPen(QColor(239, 68, 68), 3)
            painter.setPen(pen_red)
            painter.drawLine(cx - 15, cy, cx + 15, cy)
            painter.drawLine(cx, cy - 15, cx, cy + 15)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(cx - 6, cy - 6, 12, 12)

        # Print Metadata Panel
        if self.meta_text:
            painter.setFont(QFont("Courier New", 10, QFont.Bold))
            fm = painter.fontMetrics()
            lines = self.meta_text.strip().split("\n")
            max_w = max(fm.horizontalAdvance(line) for line in lines)
            total_h = len(lines) * fm.height()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(17, 24, 39, 220))
            painter.drawRoundedRect(20, 20, max_w + 30, total_h + 30, 6, 6)

            painter.setPen(QColor(253, 224, 71))
            curr_y = 40
            for line in lines:
                painter.drawText(35, curr_y, line)
                curr_y += fm.height()
