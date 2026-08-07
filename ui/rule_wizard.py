import os
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QSlider, QWidget, QStackedWidget, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPen

class TeachOverlay(QWidget):
    """
    Full-screen semi-transparent overlay to select a custom crop region for visual targets.
    """
    region_selected = Signal(int, int, int, int) # x, y, w, h

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.end_pos = None

    def show_overlay(self):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.start_pos = None
        self.end_pos = None
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.globalPosition().toPoint()
            self.end_pos = self.start_pos
            self.update()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.end_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x1 - x2)
            h = abs(y1 - y2)
            self.hide()
            if w > 5 and h > 5:
                self.region_selected.emit(x, y, w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            pen = QPen(QColor(168, 85, 247), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(168, 85, 247, 30))
            painter.drawRect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))


from PySide6.QtWidgets import QApplication

class TemplateOffsetPicker(QLabel):
    """
    Displays the cropped template image and registers mouse press events to set
    a precise user click offset relative to the template's top-left corner.
    Renders a red crosshair over the chosen offset.
    """
    offset_clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QLabel.StyledPanel)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.CrossCursor)
        self.click_x = None
        self.click_y = None

    def set_template_image(self, pixmap: QPixmap):
        self.setPixmap(pixmap)
        self.click_x = pixmap.width() // 2
        self.click_y = pixmap.height() // 2
        self.offset_clicked.emit(self.click_x, self.click_y)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap():
            lbl_w, lbl_h = self.width(), self.height()
            pm_w, pm_h = self.pixmap().width(), self.pixmap().height()

            x0 = (lbl_w - pm_w) // 2
            y0 = (lbl_h - pm_h) // 2

            click_x = event.position().x() - x0
            click_y = event.position().y() - y0

            self.click_x = max(0, min(pm_w - 1, int(click_x)))
            self.click_y = max(0, min(pm_h - 1, int(click_y)))

            self.offset_clicked.emit(self.click_x, self.click_y)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap() and self.click_x is not None and self.click_y is not None:
            painter = QPainter(self)
            lbl_w, lbl_h = self.width(), self.height()
            pm_w, pm_h = self.pixmap().width(), self.pixmap().height()
            x0 = (lbl_w - pm_w) // 2
            y0 = (lbl_h - pm_h) // 2

            cx = x0 + self.click_x
            cy = y0 + self.click_y

            pen = QPen(QColor(239, 68, 68), 2)
            painter.setPen(pen)
            painter.drawLine(cx - 8, cy, cx + 8, cy)
            painter.drawLine(cx, cy - 8, cx, cy + 8)


class RuleWizard(QDialog):
    """
    Polished step-by-step wizard dialog to configure visual/cursor automation rules.
    Includes the multi-step click sequence builder.
    """
    def __init__(self, parent=None, abs_x=None, abs_y=None, rules_snapshot=None, template_path=None):
        super().__init__(parent)
        self.setWindowTitle("New Automation Rule Wizard")
        self.resize(550, 750)
        self.abs_x = abs_x
        self.abs_y = abs_y
        self.rules_snapshot = rules_snapshot if rules_snapshot is not None else []
        self.template_path = template_path

        # Stored original window/coordinate properties accessed by main.py
        self.window_title = "Active Window"
        self.window_offset_x = 0
        self.window_offset_y = 0

        self.current_step = 0
        self.click_offset_x = 0
        self.click_offset_y = 0

        self.click_steps = [{"action": "Single Click", "offset_x": 0, "offset_y": 0, "delay": 0.5}]
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.stacked_widget = QStackedWidget(self)

        # Step 1: Choose Trigger
        self.step1_widget = QWidget()
        s1_layout = QVBoxLayout(self.step1_widget)
        s1_layout.addWidget(QLabel("<h3>Step 1: Choose Trigger Type</h3>"))
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(["Image Template Match", "OCR Text Match", "Absolute Cursor Position", "Window-Relative Position"])
        s1_layout.addWidget(self.trigger_combo)
        s1_layout.addStretch()
        self.stacked_widget.addWidget(self.step1_widget)

        # Step 2: Configure Offset / Click Point Calibration
        self.step2_widget = QWidget()
        s2_layout = QVBoxLayout(self.step2_widget)
        s2_layout.addWidget(QLabel("<h3>Step 2: Calibrate Click Target Spot</h3>"))
        s2_layout.addWidget(QLabel("Click inside the preview template below to choose the precise coordinate of click:"))

        self.offset_picker = TemplateOffsetPicker(self)
        self.offset_picker.offset_clicked.connect(self.update_offset_lbl)
        s2_layout.addWidget(self.offset_picker)

        self.offset_lbl = QLabel("🎯 Click Offset: X: +0 px, Y: +0 px")
        s2_layout.addWidget(self.offset_lbl)
        s2_layout.addStretch()
        self.stacked_widget.addWidget(self.step2_widget)

        # Step 3: Search Region & Anchor Selector Combo
        self.step3_widget = QWidget()
        s3_layout = QVBoxLayout(self.step3_widget)
        s3_layout.addWidget(QLabel("<h3>Step 3: Define Search Region & Anchor</h3>"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["Entire Screen", "Active Window Only", "Trained Region Only"])
        s3_layout.addWidget(self.region_combo)

        s3_layout.addWidget(QLabel("Anchor Rule for Relative Offset (Optional):"))
        self.anchor_select_combo = QComboBox()
        self.anchor_select_combo.addItem("None (Independent)")
        for r in self.rules_snapshot:
            self.anchor_select_combo.addItem(f"{r.name} ({r.id_str})", r.id_str)
        s3_layout.addWidget(self.anchor_select_combo)
        s3_layout.addStretch()
        self.stacked_widget.addWidget(self.step3_widget)

        # Step 4: Rule Parameters (Confidence, Cooldown) & Click Sequence Builder
        self.step4_widget = QWidget()
        s4_layout = QVBoxLayout(self.step4_widget)
        s4_layout.addWidget(QLabel("<h3>Step 4: Click Sequence & Parameters</h3>"))

        s4_layout.addWidget(QLabel("Rule Name:"))
        self.name_input = QLineEdit("My Automated Rule")
        s4_layout.addWidget(self.name_input)

        s4_layout.addWidget(QLabel("Confidence Threshold:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 99)
        self.conf_slider.setValue(90)
        s4_layout.addWidget(self.conf_slider)

        s4_layout.addWidget(QLabel("Cooldown (s):"))
        self.cooldown_combo = QComboBox()
        self.cooldown_combo.addItems(["1", "2", "3", "5", "8", "10", "15"])
        s4_layout.addWidget(self.cooldown_combo)

        # Click Sequence Builder Group Box
        seq_group = QGroupBox("Macro Sequences Steps (Clicks / Keyboard Delays)")
        seq_layout = QVBoxLayout(seq_group)

        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels(["Step", "Action", "Offset (X, Y)", "Delay", "Delete"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.steps_table.setFixedHeight(120)
        seq_layout.addWidget(self.steps_table)

        add_ctrls_layout = QHBoxLayout()
        self.step_action_combo = QComboBox()
        self.step_action_combo.addItems(["Single Click", "Double Click", "Right Click"])
        self.step_x_input = QLineEdit("0")
        self.step_x_input.setPlaceholderText("X Offset")
        self.step_y_input = QLineEdit("0")
        self.step_y_input.setPlaceholderText("Y Offset")
        self.step_delay_input = QLineEdit("0.5")
        self.step_delay_input.setPlaceholderText("Delay (s)")

        self.add_step_btn = QPushButton("➕ Add Step")
        self.add_step_btn.clicked.connect(self.add_click_step)

        add_ctrls_layout.addWidget(self.step_action_combo)
        add_ctrls_layout.addWidget(self.step_x_input)
        add_ctrls_layout.addWidget(self.step_y_input)
        add_ctrls_layout.addWidget(self.step_delay_input)
        add_ctrls_layout.addWidget(self.add_step_btn)
        seq_layout.addLayout(add_ctrls_layout)
        s4_layout.addWidget(seq_group)

        self.stacked_widget.addWidget(self.step4_widget)
        self.main_layout.addWidget(self.stacked_widget)

        # Navigation Buttons
        self.nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Back")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.handle_back)
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.handle_next)

        self.nav_layout.addWidget(self.prev_btn)
        self.nav_layout.addStretch()
        self.nav_layout.addWidget(self.next_btn)
        self.main_layout.addLayout(self.nav_layout)

        # Load cropped image if valid
        if self.template_path and os.path.exists(self.template_path):
            pix = QPixmap(self.template_path)
            if not pix.isNull():
                self.offset_picker.set_template_image(pix)

        self.refresh_steps_table()

    def update_offset_lbl(self, x, y):
        self.click_offset_x = x
        self.click_offset_y = y
        self.offset_lbl.setText(f"🎯 Click Offset: X: +{x} px, Y: +{y} px")

    def handle_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stacked_widget.setCurrentIndex(self.current_step)
            self.next_btn.setText("Next")
            if self.current_step == 0:
                self.prev_btn.setEnabled(False)

    def handle_next(self):
        if self.current_step < 3:
            self.current_step += 1
            self.stacked_widget.setCurrentIndex(self.current_step)
            self.prev_btn.setEnabled(True)
            if self.current_step == 3:
                self.next_btn.setText("Finish & Save")
        else:
            self.accept()

    def add_click_step(self):
        action = self.step_action_combo.currentText()
        try:
            offset_x = int(self.step_x_input.text())
        except ValueError:
            offset_x = 0
        try:
            offset_y = int(self.step_y_input.text())
        except ValueError:
            offset_y = 0
        try:
            delay = float(self.step_delay_input.text())
        except ValueError:
            delay = 0.5

        self.click_steps.append({
            "action": action,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "delay": delay
        })
        self.refresh_steps_table()

    def delete_click_step(self, idx):
        if 0 <= idx < len(self.click_steps):
            self.click_steps.pop(idx)
            self.refresh_steps_table()

    def refresh_steps_table(self):
        self.steps_table.setRowCount(len(self.click_steps))
        for row, step in enumerate(self.click_steps):
            self.steps_table.setItem(row, 0, QTableWidgetItem(f"#{row+1}"))
            self.steps_table.setItem(row, 1, QTableWidgetItem(step["action"]))
            self.steps_table.setItem(row, 2, QTableWidgetItem(f"({step['offset_x']}, {step['offset_y']})"))
            self.steps_table.setItem(row, 3, QTableWidgetItem(f"{step['delay']}s"))

            del_btn = QPushButton("🗑️")
            def make_deleter(index):
                return lambda: self.delete_click_step(index)
            del_btn.clicked.connect(make_deleter(row))
            self.steps_table.setCellWidget(row, 4, del_btn)


class SaveTargetDialog(RuleWizard):
    """
    Maintain backward-compatibility with coordinator instantiation calls.
    """
    pass
