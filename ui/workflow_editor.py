from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QGroupBox, QComboBox, QLineEdit
)

class WorkflowEditor(QFrame):
    """
    Workflow sequence pipeline: WHEN -> VERIFY -> WAIT -> ACTION -> VERIFY RESULT -> RETRY
    Letting users define full automation flows visually.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
            "QLabel { color: #D1D5DB; font-family: 'Segoe UI'; font-size: 11px; }"
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.title = QLabel("<h3>🛠️ Visual Workflow Editor Pipeline</h3>")
        layout.addWidget(self.title)

        # WHEN
        when_box = QGroupBox("1. WHEN (Scan Trigger)")
        wl = QHBoxLayout(when_box)
        wl.addWidget(QLabel("Trigger matching detection rule matches target candidate"))
        layout.addWidget(when_box)

        # VERIFY
        verify_box = QGroupBox("2. VERIFY (Scoring Verification)")
        vl = QHBoxLayout(verify_box)
        vl.addWidget(QLabel("Edge similarity score + Histogram Correlation matches threshold"))
        layout.addWidget(verify_box)

        # ACTION
        action_box = QGroupBox("3. ACTION (Calibrated Mouse Click)")
        al = QHBoxLayout(action_box)
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Single Left Click", "Double Click", "Right Click"])
        al.addWidget(self.action_combo)
        layout.addWidget(action_box)

        # VERIFY RESULT
        result_box = QGroupBox("4. VERIFY RESULT (Post Check)")
        rl = QHBoxLayout(result_box)
        rl.addWidget(QLabel("Monitor screen change signature within 300ms of clicking"))
        layout.addWidget(result_box)

        # FAIL RECOVERY
        fail_box = QGroupBox("5. ON FAILURE (Recovery Plan)")
        fl = QHBoxLayout(fail_box)
        self.retry_combo = QComboBox()
        self.retry_combo.addItems(["Do Nothing", "Retry Once", "Retry 3 Times", "Alert Log Error"])
        self.retry_combo.setCurrentText("Retry Once")
        fl.addWidget(self.retry_combo)
        layout.addWidget(fail_box)
