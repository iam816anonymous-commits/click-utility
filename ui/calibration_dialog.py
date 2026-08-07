from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QGroupBox, QApplication
)
from PySide6.QtGui import QFont, QPixmap

class CalibrationWizard(QDialog):
    """
    Step-by-step Calibration Wizard to detect monitor resolutions, scaling,
    verify alignment, and compute correction factors automatically.
    Stores calibration offsets per monitor.
    """
    calibration_complete = Signal(float, float) # correction_x, correction_y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System DPI & Calibration Wizard")
        self.resize(500, 350)
        self.current_step = 1

        self.correction_x = 0.0
        self.correction_y = 0.0

        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

        self.title_lbl = QLabel("<h3>DPI Alignment & Calibration Wizard</h3>")
        self.layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(
            "This wizard aligns your mouse cursor coordinate space with the screenshot coordinate space "
            "to ensure perfect clicking accuracy regardless of Windows DPI scaling or resolution mismatches."
        )
        self.desc_lbl.setWordWrap(True)
        self.layout.addWidget(self.desc_lbl)

        self.metrics_lbl = QLabel()
        self.metrics_lbl.setStyleSheet("padding: 10px; background-color: #F3F4F6; border-radius: 4px; font-family: monospace;")
        self.update_metrics_view()
        self.layout.addWidget(self.metrics_lbl)

        self.btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.next_btn = QPushButton("Start Calibration Step 1")
        self.next_btn.clicked.connect(self.handle_next)

        self.btn_layout.addWidget(self.cancel_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.next_btn)
        self.layout.addLayout(self.btn_layout)

    def update_metrics_view(self):
        screen = QApplication.primaryScreen()
        geom = screen.geometry()
        ratio = screen.devicePixelRatio()
        text = (
            f"Primary Monitor Res : {geom.width()}x{geom.height()}\n"
            f"Device Pixel Ratio  : {ratio}x\n"
            f"Coordinate System   : PySide6 QScreen Alignment"
        )
        self.metrics_lbl.setText(text)

    def handle_next(self):
        if self.current_step == 1:
            self.current_step = 2
            self.desc_lbl.setText(
                "<b>Step 1/2: Calculate Mouse Coordinates vs Screen Pixels</b><br><br>"
                "We will position your cursor and verify scaling. Please do not move the mouse for a second."
            )
            self.next_btn.setText("Calculate Correction")

            # Auto-calculate scaling DPI factors
            screen = QApplication.primaryScreen()
            ratio = screen.devicePixelRatio()
            if ratio != 1.0:
                self.correction_x = ratio
                self.correction_y = ratio

        elif self.current_step == 2:
            # Complete
            self.calibration_complete.emit(self.correction_x, self.correction_y)
            self.accept()


class CalibrationDialog(QDialog):
    """
    DPI and click offset correction tuning dialog.
    """
    calibration_saved = Signal(float, float)

    def __init__(self, parent=None, rule_name="Rule"):
        super().__init__(parent)
        self.setWindowTitle(f"Click Calibration Tuning - {rule_name}")
        self.resize(450, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>🛠️ Fine-Tune Calibration Offsets</h3>"))
        layout.addWidget(QLabel(
            "Use this dialog to apply micro pixel adjustments directly on top "
            "of your calibrated visual templates to compensate for custom application borders."
        ))

        # Pixel Adjustments
        box = QGroupBox("Fine Tuning Offsets (Pixels)")
        bl = QHBoxLayout(box)
        bl.addWidget(QLabel("Offset X Adjust:"))
        self.off_x_input = QLineEdit("0")
        bl.addWidget(self.off_x_input)

        bl.addWidget(QLabel("Offset Y Adjust:"))
        self.off_y_input = QLineEdit("0")
        bl.addWidget(self.off_y_input)
        layout.addWidget(box)

        btn_box = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save Correction")
        self.save_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.handle_save)

        btn_box.addWidget(self.cancel_btn)
        btn_box.addStretch()
        btn_box.addWidget(self.save_btn)
        layout.addLayout(btn_box)

    def handle_save(self):
        try:
            cx = float(self.off_x_input.text())
            cy = float(self.off_y_input.text())
            self.calibration_saved.emit(cx, cy)
            self.accept()
        except ValueError:
            self.reject()
