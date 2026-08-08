from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox, QFrame, QGroupBox
)
from PySide6.QtGui import QFont

class SettingsPage(QFrame):
    """
    Settings Page configuring monitoring FPS, default confidences, hotkey themes, and layouts.
    """
    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
            "QLabel { color: #E5E7EB; font-family: 'Segoe UI'; font-size: 11px; }"
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.title = QLabel("<h3>⚙️ Application Settings Studio</h3>")
        layout.addWidget(self.title)

        box = QGroupBox("Performance & Automation")
        box_layout = QVBoxLayout(box)

        box_layout.addWidget(QLabel("Monitoring Target FPS:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["5", "10", "15", "20", "30"])
        self.fps_combo.setCurrentText("10")
        box_layout.addWidget(self.fps_combo)

        box_layout.addWidget(QLabel("Mouse Click Synthesizer Delay (s):"))
        self.click_delay_input = QLineEdit("0.02")
        box_layout.addWidget(self.click_delay_input)

        box_layout.addWidget(QLabel("Default Scanning Confidence Threshold:"))
        self.conf_combo = QComboBox()
        self.conf_combo.addItems(["80%", "85%", "90%", "95%"])
        self.conf_combo.setCurrentText("90%")
        box_layout.addWidget(self.conf_combo)

        layout.addWidget(box)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.handle_save)
        layout.addWidget(self.save_btn)

    def handle_save(self):
        self.settings_saved.emit()
