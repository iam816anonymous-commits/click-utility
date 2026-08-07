import os
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QFont, QPixmap

class TemplateManager(QFrame):
    """
    Template Manager sidebar displaying preview thumbnails, template paths,
    and fast replace/delete triggers.
    """
    template_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
            "QLabel { color: #E5E7EB; font-family: 'Segoe UI'; font-size: 11px; }"
            "QListWidget { background-color: #111827; border: 1px solid #374151; color: #F3F4F6; border-radius: 4px; }"
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.title = QLabel("<h3>📁 Stored Template Assets</h3>")
        layout.addWidget(self.title)

        self.list_widget = QListWidget(self)
        self.list_widget.currentTextChanged.connect(self.handle_template_changed)
        layout.addWidget(self.list_widget)

        self.preview_lbl = QLabel("No template selected.")
        self.preview_lbl.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setFixedSize(140, 110)

        preview_box = QHBoxLayout()
        preview_box.addStretch()
        preview_box.addWidget(self.preview_lbl)
        preview_box.addStretch()
        layout.addLayout(preview_box)

        # Actions
        btn_box = QHBoxLayout()
        self.replace_btn = QPushButton("Replace")
        self.replace_btn.setStyleSheet("background-color: #3B82F6; color: white;")
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("background-color: #EF4444; color: white;")

        btn_box.addWidget(self.replace_btn)
        btn_box.addWidget(self.delete_btn)
        layout.addLayout(btn_box)

        self.refresh_templates()

    def refresh_templates(self):
        self.list_widget.clear()
        if os.path.exists("targets"):
            files = [f for f in os.listdir("targets") if f.endswith(".png")]
            for f in files:
                self.list_widget.addItem(f)

    def handle_template_changed(self, text):
        if not text:
            self.preview_lbl.setText("No Image")
            return

        path = os.path.join("targets", text)
        if os.path.exists(path):
            pix = QPixmap(path)
            self.preview_lbl.setPixmap(pix.scaled(140, 110, Qt.KeepAspectRatio))
            self.template_selected.emit(path)
        else:
            self.preview_lbl.setText("Error loading")
