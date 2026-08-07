from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QFrame, QLabel
from PySide6.QtGui import QFont, QColor

class ConsolePanel(QFrame):
    """
    Colored text log viewer panel displaying real-time execution flows.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.title = QLabel("<h3>📝 Colored Action Log Console</h3>")
        self.title.setStyleSheet("color: #E5E7EB; font-family: 'Segoe UI';")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(
            "QPushButton { background-color: #4B5563; border-radius: 5px; color: white; padding: 4px 10px; }"
            "QPushButton:hover { background-color: #374151; }"
        )
        self.clear_btn.clicked.connect(self.clear_console)
        row.addWidget(self.title)
        row.addStretch()
        row.addWidget(self.clear_btn)
        layout.addLayout(row)

        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setStyleSheet("background-color: #111827; color: #10B981; border: none; border-radius: 5px;")
        layout.addWidget(self.log_text)

    @Slot()
    def clear_console(self):
        self.log_text.clear()

    def log_success(self, msg):
        self.log_text.append(f"<font color='#10B981'>[✓] {msg}</font>")

    def log_info(self, msg):
        self.log_text.append(f"<font color='#3B82F6'>[*] {msg}</font>")

    def log_warning(self, msg):
        self.log_text.append(f"<font color='#F59E0B'>[⚠️] {msg}</font>")

    def log_error(self, msg):
        self.log_text.append(f"<font color='#EF4444'>[🚨] {msg}</font>")
