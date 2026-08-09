from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
from automation_studio.ui.settings import SettingsPage

class SettingsDialog(QDialog):
    """
    Dialog wrapper for application settings to allow standalone configuration.
    Fully compliant with the Professional Automation Studio contract folder layout.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        self.settings_page = SettingsPage(self)
        layout.addWidget(self.settings_page)

        # Add OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect inner save signal to accept
        self.settings_page.settings_saved.connect(self.accept)
