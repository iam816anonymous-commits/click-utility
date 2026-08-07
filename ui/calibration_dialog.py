from PySide6.QtCore import Qt, Slot, Signal, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QGroupBox, QApplication, QWidget
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QColor

class InteractiveTargetWindow(QWidget):
    """
    A fullscreen click-responsive window displaying a calibration crosshair at a fixed
    point (e.g., center of primary monitor) and measures the user clicked point to
    determine exact cursor calibration correction factors.
    """
    target_clicked = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        # Center of primary screen as the fixed calibration spot
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.target_point = QPoint(screen.geometry().width() // 2, screen.geometry().height() // 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Measure coordinate system displacement
            cx, cy = event.globalPosition().toPoint().x(), event.globalPosition().toPoint().y()
            tx, ty = self.target_point.x(), self.target_point.y()

            # Compute direct mouse vs screen offset corrections
            corr_x = float(tx - cx)
            corr_y = float(ty - cy)

            self.target_clicked.emit(corr_x, corr_y)
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Dim background
        painter.fillRect(self.rect(), QColor(17, 24, 39, 180))

        # Draw target spot (emerald green concentric target circles)
        cx, cy = self.target_point.x(), self.target_point.y()
        painter.setPen(QPen(QColor(16, 185, 129), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - 15, cy - 15, 30, 30)
        painter.drawEllipse(cx - 5, cy - 5, 10, 10)
        painter.drawLine(cx - 25, cy, cx + 25, cy)
        painter.drawLine(cx, cy - 25, cx, cy + 25)

        # Instruction text
        painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
        painter.setPen(QColor(253, 224, 71)) # Gold
        painter.drawText(self.rect(), Qt.AlignHCenter | Qt.AlignTop, "\n\n🎯 CLICK PRECISELY ON THE CENTER OF THE GREEN TARGET TARGET")


class CalibrationWizard(QDialog):
    """
    Step-by-step Interactive Calibration Wizard.
    Displays an on-screen target, measures clicking alignment, and saves correction offsets.
    """
    calibration_complete = Signal(float, float) # correction_x, correction_y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interactive DPI Calibration Wizard")
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
        self.metrics_lbl.setStyleSheet("padding: 10px; background-color: #F3F4F6; border-radius: 4px; font-family: monospace; color: #1F2937;")
        self.update_metrics_view()
        self.layout.addWidget(self.metrics_lbl)

        self.btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.next_btn = QPushButton("Launch Calibration Target")
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
            self.hide() # hide parent dialog

            self.target_window = InteractiveTargetWindow()
            self.target_window.target_clicked.connect(self.record_target_offset)
            self.target_window.show()

    def record_target_offset(self, corr_x, corr_y):
        self.correction_x = corr_x
        self.correction_y = corr_y

        self.show() # restore parent
        self.desc_lbl.setText(
            f"<b>Calibration Complete!</b><br><br>"
            f"Successfully measured coordinate displacement offset corrections:<br>"
            f"🎯 <b>Correction X:</b> {corr_x:+.1f} px<br>"
            f"🎯 <b>Correction Y:</b> {corr_y:+.1f} px"
        )
        self.next_btn.setText("Apply Corrections")

        # Complete
        self.calibration_complete.emit(self.correction_x, self.correction_y)
        self.next_btn.clicked.disconnect()
        self.next_btn.clicked.connect(self.accept)


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
