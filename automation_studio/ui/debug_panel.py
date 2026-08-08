import os
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPixmap, QCursor

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


class DebugPanel(QFrame):
    """
    HUD debugger panel showing a comprehensive diagnostic list of coordinates, resolutions, and timings.
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
        self.title = QLabel("<h3>🔍 Pipeline Diagnostic & Code Inspector</h3>")
        layout.addWidget(self.title)

        self.template_preview = QLabel("No template loaded.")
        self.template_preview.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.template_preview.setAlignment(Qt.AlignCenter)
        self.template_preview.setFixedSize(120, 100)

        info_sub_layout = QVBoxLayout()
        self.state_lbl = QLabel("<b>Rule Name:</b> --")
        self.size_lbl = QLabel("<b>Template Size:</b> --")
        self.topleft_lbl = QLabel("<b>Detected Top-Left:</b> --")
        self.center_lbl = QLabel("<b>Detected Center:</b> --")
        self.offset_lbl = QLabel("<b>User Offset:</b> --")
        self.calculated_lbl = QLabel("<b>Calculated Click:</b> --")
        self.dpi_lbl = QLabel("<b>DPI Scale Factor:</b> --")
        self.logical_lbl = QLabel("<b>Logical Resolution:</b> --")
        self.physical_lbl = QLabel("<b>Physical Resolution:</b> --")
        self.window_lbl = QLabel("<b>Window Origin/Size:</b> --")
        self.timing_lbl = QLabel("<b>Total Execution Time:</b> -- ms")

        info_sub_layout.addWidget(self.state_lbl)
        info_sub_layout.addWidget(self.size_lbl)
        info_sub_layout.addWidget(self.topleft_lbl)
        info_sub_layout.addWidget(self.center_lbl)
        info_sub_layout.addWidget(self.offset_lbl)
        info_sub_layout.addWidget(self.calculated_lbl)
        info_sub_layout.addWidget(self.dpi_lbl)
        info_sub_layout.addWidget(self.logical_lbl)
        info_sub_layout.addWidget(self.physical_lbl)
        info_sub_layout.addWidget(self.window_lbl)
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

        self.state_lbl.setText(f"<b>Rule Name:</b> Active Match ({state})")
        self.size_lbl.setText(f"<b>Match Confidence:</b> {conf}")
        self.topleft_lbl.setText(f"<b>Click Coordinates:</b> {click_coords}")
        self.window_lbl.setText(f"<b>Search Region:</b> {region_info}")
        self.timing_lbl.setText(f"<b>Total Execution Time:</b> {execution_time} ms")

        screen = QApplication.primaryScreen()
        if screen:
            self.dpi_lbl.setText(f"<b>DPI Scale Factor:</b> {screen.devicePixelRatio()}x")
            self.logical_lbl.setText(f"<b>Logical Resolution:</b> {screen.geometry().width()}x{screen.geometry().height()}")
            self.physical_lbl.setText(f"<b>Physical Resolution:</b> {int(screen.geometry().width() * screen.devicePixelRatio())}x{int(screen.geometry().height() * screen.devicePixelRatio())}")


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
