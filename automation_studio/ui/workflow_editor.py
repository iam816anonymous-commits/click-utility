from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget

class WorkflowEditor(QWidget):
    """
    Pipeline Workflow steps sequence visualizer list.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        layout.addWidget(QLabel("<h3>🛠️ Active Workflow Sequences</h3>"))

        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; color: #F9FAFB; padding: 5px; }"
        )
        # Mock sequence pipeline steps
        self.list_widget.addItem("1. WHEN   - Capture Region")
        self.list_widget.addItem("2. VERIFY - Disambiguate Matches")
        self.list_widget.addItem("3. WAIT   - Cooldown validation")
        self.list_widget.addItem("4. ACTION - Precise click trigger")
        self.list_widget.addItem("5. VERIFY - Post-click snapshot check")
        layout.addWidget(self.list_widget)
