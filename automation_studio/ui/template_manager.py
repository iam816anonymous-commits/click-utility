import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtGui import QPixmap

class TemplateManager(QWidget):
    """
    Template assets manager tab.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; color: #F9FAFB; padding: 5px; }"
        )
        self.list_widget.currentItemChanged.connect(self.preview_template)
        layout.addWidget(self.list_widget)

        self.preview_lbl = QLabel("Select a template asset to preview.", self)
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setFrameStyle(QLabel.StyledPanel)
        self.preview_lbl.setFixedHeight(150)
        layout.addWidget(self.preview_lbl)

        row = QHBoxLayout()
        self.replace_btn = QPushButton("🔄 Replace Template", self)
        self.replace_btn.setStyleSheet("background-color: #3B82F6;")
        self.delete_btn = QPushButton("🗑️ Delete Template", self)
        self.delete_btn.setStyleSheet("background-color: #EF4444;")

        row.addWidget(self.replace_btn)
        row.addWidget(self.delete_btn)
        layout.addLayout(row)

        self.refresh_templates()

    def refresh_templates(self):
        self.list_widget.clear()
        if os.path.exists("targets"):
            for filename in os.listdir("targets"):
                if filename.endswith(".png"):
                    self.list_widget.addItem(filename)

    def preview_template(self, current, previous):
        if current:
            filename = current.text()
            path = os.path.join("targets", filename)
            if os.path.exists(path):
                pix = QPixmap(path)
                self.preview_lbl.setPixmap(pix.scaled(self.preview_lbl.width(), self.preview_lbl.height(), Qt.KeepAspectRatio))
        else:
            self.preview_lbl.clear()
            self.preview_lbl.setText("Select a template asset to preview.")
