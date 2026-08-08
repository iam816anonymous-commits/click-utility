from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PySide6.QtGui import QFont, QTextCursor

class ConsolePanel(QWidget):
    """
    Highly Polished colored rich-text action log presentation window.
    Features descriptive colored prefixes tracing macro execution states.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        self.log_text = QTextBrowser(self)
        self.log_text.setReadOnly(True)
        self.log_text.setOpenExternalLinks(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setStyleSheet(
            "QTextBrowser { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; color: #F9FAFB; padding: 10px; }"
        )
        layout.addWidget(self.log_text)

        row = QHBoxLayout()
        self.clear_btn = QPushButton("🧹 Clear Logs", self)
        self.clear_btn.setStyleSheet(
            "QPushButton { background-color: #4B5563; padding: 6px 12px; font-weight: normal; font-size: 11px; }"
            "QPushButton:hover { background-color: #374151; }"
        )
        self.clear_btn.clicked.connect(self.log_text.clear)
        row.addStretch()
        row.addWidget(self.clear_btn)
        layout.addLayout(row)

    @Slot(str)
    def append_html(self, html_text: str):
        self.log_text.append(html_text)
        self.log_text.moveCursor(QTextCursor.End)

    def log_info(self, message: str):
        self.append_html(f"<span style='color: #9CA3AF;'>[ℹ️] {message}</span>")

    def log_success(self, message: str):
        self.append_html(f"<span style='color: #10B981; font-weight: bold;'>[✓] {message}</span>")

    def log_warning(self, message: str):
        self.append_html(f"<span style='color: #FBBF24; font-weight: bold;'>[⚠️] {message}</span>")

    def log_error(self, message: str):
        self.append_html(f"<span style='color: #EF4444; font-weight: bold;'>[🚨] {message}</span>")
