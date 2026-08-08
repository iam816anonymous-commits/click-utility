from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton

class SettingsPage(QWidget):
    """
    Studio configuration settings.
    """
    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("<h3>⚙️ Performance & Clicking Settings</h3>"))

        # FPS
        row_fps = QHBoxLayout()
        row_fps.addWidget(QLabel("Loop Scan FPS Limit:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["5", "10", "15", "20", "30"])
        self.fps_combo.setCurrentText("10")
        row_fps.addWidget(self.fps_combo)
        layout.addLayout(row_fps)

        # Clicks delay
        row_delay = QHBoxLayout()
        row_delay.addWidget(QLabel("Click Synthesizer micro-delay (s):"))
        self.click_delay_input = QLineEdit("0.02")
        row_delay.addWidget(self.click_delay_input)
        layout.addLayout(row_delay)

        # Default conf
        row_conf = QHBoxLayout()
        row_conf.addWidget(QLabel("Default Matching Confidence Threshold:"))
        self.conf_combo = QComboBox()
        self.conf_combo.addItems(["80%", "85%", "90%", "95%", "98%"])
        self.conf_combo.setCurrentText("90%")
        row_conf.addWidget(self.conf_combo)
        layout.addLayout(row_conf)

        self.save_btn = QPushButton("Save Configuration", self)
        self.save_btn.setStyleSheet("background-color: #10B981; font-weight: bold;")
        self.save_btn.clicked.connect(self.settings_saved.emit)
        layout.addWidget(self.save_btn)
        layout.addStretch()
