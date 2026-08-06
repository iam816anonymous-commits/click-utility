import sys
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QTextEdit,
    QSlider, QDialog, QLineEdit, QComboBox, QCheckBox, QStyle, QGroupBox,
    QFileDialog
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont

class TeachOverlay(QWidget):
    """
    Full-screen semi-transparent overlay to select a custom crop region for visual targets.
    """
    region_selected = Signal(int, int, int, int) # x, y, w, h

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.end_pos = None

    def show_overlay(self):
        # Span all monitors
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
        # Translucent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            # Bounding box selection
            pen = QPen(QColor(168, 85, 247), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(168, 85, 247, 30))
            painter.drawRect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))


class SaveTargetDialog(QDialog):
    """
    Modal window to name and configure the newly captured template target.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Macro Automation Rule")
        self.resize(320, 280)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Target Name
        layout.addWidget(QLabel("Target / Rule Name:"))
        self.name_input = QLineEdit("My Macro Button")
        layout.addWidget(self.name_input)

        # Trigger Type
        layout.addWidget(QLabel("Trigger Mechanism:"))
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(["Image Template Match", "OCR Text Match"])
        layout.addWidget(self.trigger_combo)

        # Click Action
        layout.addWidget(QLabel("Mouse Click Action:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Left Click", "Double Click", "Right Click"])
        layout.addWidget(self.action_combo)

        # Cooldown Slider
        layout.addWidget(QLabel("Cooldown delay (Seconds):"))
        self.cooldown_combo = QComboBox()
        self.cooldown_combo.addItems(["2", "3", "5", "8", "10", "15"])
        layout.addWidget(self.cooldown_combo)

        # Confidence Slider
        layout.addWidget(QLabel("Confidence threshold:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 99)
        self.conf_slider.setValue(85)
        layout.addWidget(self.conf_slider)

        self.conf_label = QLabel("85%")
        layout.addWidget(self.conf_label)
        self.conf_slider.valueChanged.connect(lambda v: self.conf_label.setText(f"{v}%"))

        # Save & Cancel Buttons
        btns_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Rule")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns_layout.addWidget(self.cancel_btn)
        btns_layout.addWidget(self.save_btn)
        layout.addLayout(btns_layout)


class NativeDashboard(QMainWindow):
    """
    Main Application Dashboard Window for PySide6.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoClicker AI - Native Desktop Controller")
        self.resize(800, 500)
        self.init_ui()

    def init_ui(self):
        # Main Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Column: Targets & Controls
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, stretch=3)

        # Controls Group
        ctrl_group = QGroupBox("Macro Controls")
        ctrl_layout = QHBoxLayout(ctrl_group)
        self.start_btn = QPushButton("▶ Start Monitor (F8)")
        self.stop_btn = QPushButton("⏸ Stop Monitor (F9)")
        self.teach_btn = QPushButton("🎯 Teach Button (F10)")
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(self.teach_btn)
        left_layout.addWidget(ctrl_group)

        # Active Rules Table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(7)
        self.rules_table.setHorizontalHeaderLabels([
            "Active", "Name", "Trigger Type", "Action", "Cooldown", "Threshold", "Last Trigger"
        ])
        left_layout.addWidget(self.rules_table)

        # Right Column: Monitoring Logs & Specs
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, stretch=2)

        # Logs Console
        logs_group = QGroupBox("Live Action Log Console")
        logs_layout = QVBoxLayout(logs_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 9))
        self.clear_logs_btn = QPushButton("Clear Console")
        logs_layout.addWidget(self.log_output)
        logs_layout.addWidget(self.clear_logs_btn)
        right_layout.addWidget(logs_group)

        # Quick Specs info
        info_label = QLabel(
            "<b>Hotkey Bindings:</b><br>"
            "🟢 <b>F8</b>: Start capture loop<br>"
            "🔴 <b>F9</b>: Stop capture loop<br>"
            "🎯 <b>F10</b>: Teach new image target<br>"
            "🚨 <b>Esc</b>: Panic emergency abort"
        )
        right_layout.addWidget(info_label)

    def append_log(self, text: str):
        self.log_output.append(text)
