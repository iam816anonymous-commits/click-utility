import sys
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QTextEdit,
    QSlider, QDialog, QLineEdit, QComboBox, QCheckBox, QStyle, QGroupBox,
    QFileDialog, QHeaderView
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
    def __init__(self, parent=None, abs_x: int = None, abs_y: int = None):
        super().__init__(parent)
        self.setWindowTitle("Save Macro Automation Rule")
        self.resize(600, 670)
        self.abs_x = abs_x
        self.abs_y = abs_y
        # Default with one single click step at the center (offset 0,0)
        self.click_steps = [{"action": "Single Click", "offset_x": 0, "offset_y": 0, "delay": 0.5}]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Target Name
        layout.addWidget(QLabel("<b>Target / Rule Name:</b>"))
        self.name_input = QLineEdit("My Macro Button" if self.abs_x is None else f"Click at [{self.abs_x}, {self.abs_y}]")
        layout.addWidget(self.name_input)

        # Trigger Type
        layout.addWidget(QLabel("<b>Trigger Mechanism:</b>"))
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(["Image Template Match", "OCR Text Match", "Absolute Cursor Position"])
        layout.addWidget(self.trigger_combo)

        if self.abs_x is not None and self.abs_y is not None:
            self.trigger_combo.setCurrentText("Absolute Cursor Position")
            coords_lbl = QLabel(f"<font color='#059669'>🎯 Captured Cursor Coordinates: <b>X: {self.abs_x}, Y: {self.abs_y}</b></font>")
            coords_lbl.setStyleSheet("padding: 4px; background-color: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 4px;")
            layout.addWidget(coords_lbl)

        # Cooldown Slider
        layout.addWidget(QLabel("<b>Rule Cooldown Delay (Seconds):</b>"))
        self.cooldown_combo = QComboBox()
        self.cooldown_combo.addItems(["2", "3", "5", "8", "10", "15"])
        layout.addWidget(self.cooldown_combo)

        # Confidence Slider
        layout.addWidget(QLabel("<b>Confidence Threshold (higher avoids false matches):</b>"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 99)
        self.conf_slider.setValue(90)  # Default updated to 90%
        layout.addWidget(self.conf_slider)

        self.conf_label = QLabel("90%")
        layout.addWidget(self.conf_label)
        self.conf_slider.valueChanged.connect(lambda v: self.conf_label.setText(f"{v}%"))

        # --- Click Sequence Builder Group Box ---
        seq_group = QGroupBox("Click Sequence Builder (Multiple Click Steps)")
        seq_layout = QVBoxLayout(seq_group)

        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels(["Step", "Action", "Offset (X, Y)", "Delay", "Delete"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        seq_layout.addWidget(self.steps_table)

        # Controls to add a new step
        add_ctrls_layout = QHBoxLayout()

        self.step_action_combo = QComboBox()
        self.step_action_combo.addItems(["Single Click", "Double Click", "Right Click"])

        self.step_x_input = QLineEdit("0")
        self.step_x_input.setPlaceholderText("X Offset")

        self.step_y_input = QLineEdit("0")
        self.step_y_input.setPlaceholderText("Y Offset")

        self.step_delay_input = QLineEdit("0.5")
        self.step_delay_input.setPlaceholderText("Delay (s)")

        self.add_step_btn = QPushButton("➕ Add Click Step")
        self.add_step_btn.clicked.connect(self.add_click_step)

        add_ctrls_layout.addWidget(self.step_action_combo)
        add_ctrls_layout.addWidget(self.step_x_input)
        add_ctrls_layout.addWidget(self.step_y_input)
        add_ctrls_layout.addWidget(self.step_delay_input)
        add_ctrls_layout.addWidget(self.add_step_btn)

        seq_layout.addLayout(add_ctrls_layout)
        layout.addWidget(seq_group)

        # Render initial steps table
        self.refresh_steps_table()

        # Save & Cancel Buttons
        btns_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Rule")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns_layout.addWidget(self.cancel_btn)
        btns_layout.addWidget(self.save_btn)
        layout.addLayout(btns_layout)

    def add_click_step(self):
        action = self.step_action_combo.currentText()
        try:
            offset_x = int(self.step_x_input.text())
        except ValueError:
            offset_x = 0

        try:
            offset_y = int(self.step_y_input.text())
        except ValueError:
            offset_y = 0

        try:
            delay = float(self.step_delay_input.text())
        except ValueError:
            delay = 0.5

        new_step = {
            "action": action,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "delay": delay
        }
        self.click_steps.append(new_step)
        self.refresh_steps_table()

        # Reset offset fields for next step
        self.step_x_input.setText("0")
        self.step_y_input.setText("0")

    def delete_click_step(self, index: int):
        if 0 <= index < len(self.click_steps):
            self.click_steps.pop(index)
            self.refresh_steps_table()

    def refresh_steps_table(self):
        self.steps_table.setRowCount(len(self.click_steps))
        for row, step in enumerate(self.click_steps):
            self.steps_table.setItem(row, 0, QTableWidgetItem(f"#{row+1}"))
            self.steps_table.setItem(row, 1, QTableWidgetItem(step["action"]))
            self.steps_table.setItem(row, 2, QTableWidgetItem(f"({step['offset_x']}, {step['offset_y']})"))
            self.steps_table.setItem(row, 3, QTableWidgetItem(f"{step['delay']}s"))

            # Delete button
            del_btn = QPushButton("🗑️")
            del_btn.setToolTip("Delete this click step")

            def make_deleter(idx):
                return lambda: self.delete_click_step(idx)

            del_btn.clicked.connect(make_deleter(row))
            self.steps_table.setCellWidget(row, 4, del_btn)


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
        self.teach_cursor_btn = QPushButton("📍 Teach Cursor (F11)")
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(self.teach_btn)
        ctrl_layout.addWidget(self.teach_cursor_btn)
        left_layout.addWidget(ctrl_group)

        # Active Rules Table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(8)
        self.rules_table.setHorizontalHeaderLabels([
            "Active", "Name", "Trigger Type", "Action", "Cooldown", "Threshold", "Last Trigger", "Actions"
        ])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
            "📍 <b>F11</b>: Teach current cursor position<br>"
            "🚨 <b>Esc</b>: Panic emergency abort"
        )
        right_layout.addWidget(info_label)

    def append_log(self, text: str):
        self.log_output.append(text)
