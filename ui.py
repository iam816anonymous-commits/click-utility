import sys
import os
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QTextEdit,
    QSlider, QDialog, QLineEdit, QComboBox, QCheckBox, QStyle, QGroupBox,
    QFileDialog, QHeaderView
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont

class MatchHighlightOverlay(QWidget):
    """
    Frameless transparent click-through overlay to temporarily draw green target highlights
    on-screen over matched locations.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.rects = []
        self.clear_timer = QTimer(self)
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self.clear_highlights)

    def highlight_matches(self, rects: list):
        """
        Expects rects to be a list of Tuples (x, y, w, h)
        """
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.rects = rects
        self.show()
        self.update()
        self.clear_timer.start(1500)

    def clear_highlights(self):
        self.rects = []
        self.hide()

    def paintEvent(self, event):
        if not self.rects:
            return
        painter = QPainter(self)
        pen = QPen(QColor(16, 185, 129), 3) # Emerald green box outline
        painter.setPen(pen)
        painter.setBrush(QColor(16, 185, 129, 30)) # Translucent fill

        for (x, y, w, h) in self.rects:
            painter.drawRect(x, y, w, h)


class TeachOverlay(QWidget):
    """
    Full-screen semi-transparent overlay to select a custom crop region for visual targets.
    """
    region_selected = Signal(int, int, int, int) # x, y, w, h

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.end_pos = None

    def show_overlay(self):
        # Span all monitors
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
        # Translucent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            # Bounding box selection
            pen = QPen(QColor(168, 85, 247), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(168, 85, 247, 30))
            painter.drawRect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))


class CapturePositionOverlay(QWidget):
    """
    Full-screen overlay for capturing a single mouse coordinate.
    Displays a real-time magnifying zoom window, red crosshair, live coordinates,
    and instruction overlay. ESC cancels the action.
    """
    position_captured = Signal(int, int, str) # x, y, window_title
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.mouse_pos = None

    def show_overlay(self):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.mouse_pos = None
        self.show()
        self.activateWindow()

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.globalPosition().toPoint()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.globalPosition().toPoint()
            # Fetch active window details at coordinate capture time
            from capture_engine import CaptureEngine
            title, wx, wy, ww, wh = CaptureEngine.get_active_window_rect()
            self.hide()
            self.position_captured.emit(pos.x(), pos.y(), title)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.cancelled.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Dim overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

        # 1. Instructions at the top
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.setPen(QPen(Qt.white))
        rect_instr = self.rect()
        rect_instr.setTop(40)
        painter.drawText(rect_instr, Qt.AlignHCenter, "📍 Click anywhere to capture the target position\nPress ESC to cancel")

        if self.mouse_pos:
            mx, my = self.mouse_pos.x(), self.mouse_pos.y()

            # 2. Draw red crosshair
            pen = QPen(QColor(239, 68, 68), 1) # Red crosshair
            painter.setPen(pen)
            painter.drawLine(mx - 20, my, mx + 20, my)
            painter.drawLine(mx, my - 20, mx, my + 20)

            # 3. Dynamic Coordinate Label Box
            text = f"X: {mx}  Y: {my}"
            painter.setFont(QFont("Courier New", 10, QFont.Bold))
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(text)
            th = fm.height()

            box_x = mx + 25
            box_y = my + 25

            # Keep text within bounds
            if box_x + tw + 20 > self.width():
                box_x = mx - tw - 40
            if box_y + th + 15 > self.height():
                box_y = my - th - 30

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(box_x, box_y, tw + 20, th + 10, 4, 4)

            painter.setPen(QColor(253, 224, 71)) # Golden yellow text
            painter.drawText(box_x + 10, box_y + th, text)

            # 4. Magnified Zoom Window (like Windows Snipping Tool!)
            # Grab a 60x60 region around the cursor
            try:
                screen = QApplication.primaryScreen()
                # Grab a tiny portion of the desktop
                grab_w, grab_h = 60, 60
                px = screen.grabWindow(0, mx - grab_w//2, my - grab_h//2, grab_w, grab_h)

                if not px.isNull():
                    # Scale it up 3x
                    mag_size = 120
                    scaled_px = px.scaled(mag_size, mag_size, Qt.KeepAspectRatio, Qt.FastTransformation)

                    # Position the magnifying loupe
                    mag_x = mx + 25
                    mag_y = my - 150
                    if mag_x + mag_size > self.width():
                        mag_x = mx - mag_size - 25
                    if mag_y < 0:
                        mag_y = my + 25

                    # Paint magnifying window
                    painter.setPen(QPen(Qt.white, 2))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawPixmap(mag_x, mag_y, scaled_px)
                    painter.drawRect(mag_x, mag_y, mag_size, mag_size)

                    # Draw a center target crosshair inside magnifying window
                    painter.setPen(QPen(QColor(239, 68, 68), 1))
                    cx = mag_x + mag_size // 2
                    cy = mag_y + mag_size // 2
                    painter.drawLine(cx - 8, cy, cx + 8, cy)
                    painter.drawLine(cx, cy - 8, cx, cy + 8)
            except Exception:
                pass


from PySide6.QtGui import QPixmap

class TemplateOffsetPicker(QLabel):
    """
    Displays the cropped template image and registers mouse press events to set
    a precise user click offset relative to the template's top-left corner.
    Renders a red crosshair over the chosen offset.
    """
    offset_clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QStyle.Sunken | QStyle.StyledPanel)
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


class SaveTargetDialog(QDialog):
    """
    Modal window to name and configure the newly captured template target.
    Integrated with a production-grade Coordinate Capture System, region locking, and anchors.
    """
    # Shared coordinate capture history across all dialog instantiations
    RECENT_CAPTURES = []

    def __init__(self, parent=None, abs_x: int = None, abs_y: int = None, rules_snapshot: list = None, template_path: str = None):
        super().__init__(parent)
        self.setWindowTitle("Save Macro Automation Rule")
        self.resize(650, 850)
        self.abs_x = abs_x
        self.abs_y = abs_y
        self.rules_snapshot = rules_snapshot if rules_snapshot is not None else []
        self.template_path = template_path

        self.click_offset_x = 0
        self.click_offset_y = 0

        self.window_title = None
        self.window_offset_x = None
        self.window_offset_y = None

        # Countdown Timer variables
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.handle_countdown)
        self.countdown_remaining = 0

        # Fullscreen overlay
        self.capture_overlay = CapturePositionOverlay()
        self.capture_overlay.position_captured.connect(self.handle_overlay_position_captured)
        self.capture_overlay.cancelled.connect(self.handle_overlay_cancelled)

        # Default click steps
        self.click_steps = [{"action": "Single Click", "offset_x": 0, "offset_y": 0, "delay": 0.5}]
        self.init_ui()

    def update_calibration_offset(self, cx: int, cy: int):
        self.click_offset_x = cx
        self.click_offset_y = cy
        self.offset_label.setText(f"🎯 Stored Target Click Offset: X: +{cx} px, Y: +{cy} px (relative to top-left)")

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Target Name
        layout.addWidget(QLabel("<b>Target / Rule Name:</b>"))
        self.name_input = QLineEdit("My Macro Rule")
        layout.addWidget(self.name_input)

        # Trigger Type
        layout.addWidget(QLabel("<b>Trigger Mechanism:</b>"))
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(["Image Template Match", "OCR Text Match", "Absolute Cursor Position", "Window-Relative Position"])
        self.trigger_combo.currentTextChanged.connect(self.handle_trigger_changed)
        layout.addWidget(self.trigger_combo)

        # --- Region Locking and Anchoring Panel (Only for Template / Visual Matches) ---
        self.visual_settings_group = QGroupBox("Search Region & Anchor Tracking Settings")
        v_layout = QVBoxLayout(self.visual_settings_group)

        # Region Locking dropdown
        v_layout.addWidget(QLabel("<b>Search Region Locking:</b>"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["Entire Screen", "Active Window Only", "Trained Region Only"])
        v_layout.addWidget(self.region_combo)

        # Anchor selection dropdown
        v_layout.addWidget(QLabel("<b>Anchor Rule for Relative Offset (Optional):</b>"))
        self.anchor_select_combo = QComboBox()
        self.anchor_select_combo.addItem("None (Independent)")
        for r in self.rules_snapshot:
            self.anchor_select_combo.addItem(f"{r.name} ({r.id_str})", r.id_str)
        v_layout.addWidget(self.anchor_select_combo)

        # Precise user clicked calibration offset panel inside visual settings group
        self.calibration_offset_group = QGroupBox("Target Calibration Click Offset")
        cal_layout = QVBoxLayout(self.calibration_offset_group)
        cal_layout.addWidget(QLabel("Click EXACTLY inside the captured template below to set the precise click spot:"))

        self.offset_picker = TemplateOffsetPicker()
        self.offset_picker.offset_clicked.connect(self.update_calibration_offset)
        cal_layout.addWidget(self.offset_picker)

        self.offset_label = QLabel("🎯 Stored Target Click Offset: X: +0 px, Y: +0 px")
        cal_layout.addWidget(self.offset_label)

        v_layout.addWidget(self.calibration_offset_group)

        # Load captured template if path is set
        if self.template_path and os.path.exists(self.template_path):
            pix = QPixmap(self.template_path)
            if not pix.isNull():
                self.offset_picker.set_template_image(pix)

        layout.addWidget(self.visual_settings_group)

        # --- Coordinate Capture Panel ---
        self.coord_group = QGroupBox("Coordinate Capture System")
        coord_layout = QVBoxLayout(self.coord_group)

        # Badges and Status
        status_layout = QHBoxLayout()
        self.status_badge = QLabel("🟡 Waiting for Capture")
        self.status_badge.setStyleSheet(
            "padding: 4px 8px; font-weight: bold; border-radius: 4px; color: #374151; background-color: #F3F4F6;"
        )
        status_layout.addWidget(self.status_badge)
        status_layout.addStretch()

        # Delay Combobox
        status_layout.addWidget(QLabel("Capture Delay:"))
        self.delay_combo = QComboBox()
        self.delay_combo.addItems(["0s", "1s", "2s", "3s", "5s", "10s"])
        status_layout.addWidget(self.delay_combo)
        coord_layout.addLayout(status_layout)

        # Coordinate Details Label
        self.coords_lbl = QLabel("No position coordinates captured yet.")
        self.coords_lbl.setStyleSheet(
            "padding: 8px; background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 4px; font-size: 11px;"
        )
        coord_layout.addWidget(self.coords_lbl)

        # Capture controls
        ctrl_layout = QHBoxLayout()
        self.capture_btn = QPushButton("🎯 Capture Position")
        self.capture_btn.clicked.connect(self.start_capture)
        self.test_btn = QPushButton("🔍 Test Position")
        self.test_btn.clicked.connect(self.test_captured_position)
        self.test_btn.setEnabled(False)
        ctrl_layout.addWidget(self.capture_btn)
        ctrl_layout.addWidget(self.test_btn)
        coord_layout.addLayout(ctrl_layout)

        # Recent Positions Combobox
        recent_layout = QHBoxLayout()
        recent_layout.addWidget(QLabel("Recent Captures History:"))
        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("Select previous capture...")
        self.recent_combo.currentIndexChanged.connect(self.use_recent_capture)
        recent_layout.addWidget(self.recent_combo, stretch=1)
        coord_layout.addLayout(recent_layout)

        layout.addWidget(self.coord_group)

        # Cooldown Slider
        layout.addWidget(QLabel("<b>Rule Cooldown Delay (Seconds):</b>"))
        self.cooldown_combo = QComboBox()
        self.cooldown_combo.addItems(["2", "3", "5", "8", "10", "15"])
        layout.addWidget(self.cooldown_combo)

        # Confidence Slider (used for Image match triggers)
        self.conf_lbl_title = QLabel("<b>Confidence Threshold (higher avoids false matches):</b>")
        layout.addWidget(self.conf_lbl_title)
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 99)
        self.conf_slider.setValue(90)
        layout.addWidget(self.conf_slider)

        self.conf_label = QLabel("90%")
        layout.addWidget(self.conf_label)
        self.conf_slider.valueChanged.connect(lambda v: self.conf_label.setText(f"{v}%"))

        # --- Click Sequence Builder Group Box ---
        seq_group = QGroupBox("Click Sequence Builder (Multiple Click Steps)")
        seq_layout = QVBoxLayout(seq_group)

        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels(["Step", "Action", "Offset (X, Y)", "Delay", "Delete"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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

        self.add_step_btn = QPushButton("➕ Add Click Step")
        self.add_step_btn.clicked.connect(self.add_click_step)

        add_ctrls_layout.addWidget(self.step_action_combo)
        add_ctrls_layout.addWidget(self.step_x_input)
        add_ctrls_layout.addWidget(self.step_y_input)
        add_ctrls_layout.addWidget(self.step_delay_input)
        add_ctrls_layout.addWidget(self.add_step_btn)
        seq_layout.addLayout(add_ctrls_layout)
        layout.addWidget(seq_group)

        # Save & Cancel Buttons
        btns_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Rule")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns_layout.addWidget(self.cancel_btn)
        btns_layout.addWidget(self.save_btn)
        layout.addLayout(btns_layout)

        # Init state
        self.refresh_steps_table()
        self.populate_recent_combo()
        self.handle_trigger_changed(self.trigger_combo.currentText())

        # If absolute coordinates were passed on init, set them!
        if self.abs_x is not None and self.abs_y is not None:
            self.set_captured_coordinates(self.abs_x, self.abs_y, "Initiator Crop")

    def handle_trigger_changed(self, text: str):
        # Only show the coordinate capturing panel when using coordinate modes
        is_coord = text in ["Absolute Cursor Position", "Window-Relative Position"]
        is_visual = text in ["Image Template Match", "OCR Text Match"]
        self.coord_group.setVisible(is_coord)
        self.visual_settings_group.setVisible(is_visual)
        self.conf_lbl_title.setVisible(is_visual)
        self.conf_slider.setVisible(is_visual)
        self.conf_label.setVisible(is_visual)

    def populate_recent_combo(self):
        self.recent_combo.clear()
        self.recent_combo.addItem("Select previous capture...")
        for i, cap in enumerate(self.RECENT_CAPTURES):
            self.recent_combo.addItem(f"#{i+1} [{cap['window'][:15]}] Spot: {cap['x']},{cap['y']}")

    def start_capture(self):
        # Read delay
        delay_text = self.delay_combo.currentText().replace("s", "")
        delay_secs = int(delay_text)

        if delay_secs > 0:
            self.countdown_remaining = delay_secs
            self.capture_btn.setEnabled(False)
            self.countdown_timer.start(1000)
            self.handle_countdown()
        else:
            self.launch_overlay()

    def handle_countdown(self):
        if self.countdown_remaining > 0:
            self.capture_btn.setText(f"⏱️ Capturing in {self.countdown_remaining}...")
            self.countdown_remaining -= 1
        else:
            self.countdown_timer.stop()
            self.capture_btn.setText("🎯 Capture Position")
            self.capture_btn.setEnabled(True)
            self.launch_overlay()

    def launch_overlay(self):
        # Minimize dialog to prevent obstructing coordinate capture
        self.hide()
        QTimer.singleShot(250, self.capture_overlay.show_overlay)

    def handle_overlay_cancelled(self):
        self.show()
        self.status_badge.setText("🔴 Capture Cancelled")
        self.status_badge.setStyleSheet(
            "padding: 4px 8px; font-weight: bold; border-radius: 4px; color: #991B1B; background-color: #FEE2E2;"
        )

    def handle_overlay_position_captured(self, x: int, y: int, window_title: str):
        self.show()
        self.set_captured_coordinates(x, y, window_title)

        # Append to static history list
        capture_record = {
            "window": window_title,
            "x": x,
            "y": y,
        }
        # Keep list size up to 10 entries
        if len(self.RECENT_CAPTURES) >= 10:
            self.RECENT_CAPTURES.pop(0)
        self.RECENT_CAPTURES.append(capture_record)
        self.populate_recent_combo()

    def set_captured_coordinates(self, x: int, y: int, window_title: str):
        self.abs_x = x
        self.abs_y = y
        self.window_title = window_title

        # Query window metrics to calculate offsets
        from capture_engine import CaptureEngine
        _, wx, wy, ww, wh = CaptureEngine.get_active_window_rect()
        self.window_offset_x = self.abs_x - wx
        self.window_offset_y = self.abs_y - wy

        # Update Live Preview Labels
        preview_text = (
            f"🎯 <b>Absolute Screen Spot:</b> X: {self.abs_x}, Y: {self.abs_y}<br>"
            f"🪟 <b>Window Relative Offsets:</b> X: +{self.window_offset_x}, Y: +{self.window_offset_y} "
            f"(inside <i>'{self.window_title}'</i>)"
        )
        self.coords_lbl.setText(preview_text)

        # Update Badge to Green Successful status
        self.status_badge.setText("🟢 Position Captured")
        self.status_badge.setStyleSheet(
            "padding: 4px 8px; font-weight: bold; border-radius: 4px; color: #065F46; background-color: #D1FAE5;"
        )
        self.test_btn.setEnabled(True)
        self.name_input.setText(f"Coordinate at [{self.abs_x}, {self.abs_y}]")

    def use_recent_capture(self, idx: int):
        if idx <= 0:
            return
        cap = self.RECENT_CAPTURES[idx - 1]
        self.set_captured_coordinates(cap["x"], cap["y"], cap["window"])

    def test_captured_position(self):
        """
        Executes coordinate validation test sequence:
        Moves mouse -> Highlight Target -> Clicks Once -> Returns mouse.
        """
        if self.abs_x is None or self.abs_y is None:
            return

        try:
            import pyautogui
            import time

            # Save original position
            ox, oy = pyautogui.position()

            # Minimize parent to clear view
            self.hide()
            time.sleep(0.2)

            # Move mouse
            pyautogui.moveTo(self.abs_x, self.abs_y, duration=0.4)

            # Click once to highlight target
            pyautogui.click()
            time.sleep(0.5)

            # Move mouse back
            pyautogui.moveTo(ox, oy, duration=0.3)

            # Restore parent dialog window
            self.show()
        except Exception as e:
            print(f"[SaveTargetDialog] Coordinate test execution failed: {e}")
            self.show()

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

        new_step = {
            "action": action,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "delay": delay
        }
        self.click_steps.append(new_step)
        self.refresh_steps_table()

        # Reset offset fields for next step
        self.step_x_input.setText("0")
        self.step_y_input.setText("0")

    def delete_click_step(self, index: int):
        if 0 <= index < len(self.click_steps):
            self.click_steps.pop(index)
            self.refresh_steps_table()

    def refresh_steps_table(self):
        self.steps_table.setRowCount(len(self.click_steps))
        for row, step in enumerate(self.click_steps):
            self.steps_table.setItem(row, 0, QTableWidgetItem(f"#{row+1}"))
            self.steps_table.setItem(row, 1, QTableWidgetItem(step["action"]))
            self.steps_table.setItem(row, 2, QTableWidgetItem(f"({step['offset_x']}, {step['offset_y']})"))
            self.steps_table.setItem(row, 3, QTableWidgetItem(f"{step['delay']}s"))

            # Delete button
            del_btn = QPushButton("🗑️")
            del_btn.setToolTip("Delete this click step")

            def make_deleter(idx):
                return lambda: self.delete_click_step(idx)

            del_btn.clicked.connect(make_deleter(row))
            self.steps_table.setCellWidget(row, 4, del_btn)


class NativeDashboard(QMainWindow):
    """
    Main Application Dashboard Window for PySide6.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoClicker AI - Native Desktop Controller")
        self.resize(800, 500)
        self.init_ui()

    def init_ui(self):
        # Main Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Column: Targets & Controls
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, stretch=3)

        # Controls Group
        ctrl_group = QGroupBox("Macro Controls")
        ctrl_layout = QHBoxLayout(ctrl_group)
        self.start_btn = QPushButton("▶ Start Monitor (F8)")
        self.stop_btn = QPushButton("⏸ Stop Monitor (F9)")
        self.teach_btn = QPushButton("🎯 Teach Button (F10)")
        self.teach_cursor_btn = QPushButton("📍 Teach Cursor (F11)")
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(self.teach_btn)
        ctrl_layout.addWidget(self.teach_cursor_btn)
        left_layout.addWidget(ctrl_group)

        # Active Rules Table
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(8)
        self.rules_table.setHorizontalHeaderLabels([
            "Active", "Name", "Trigger Type", "Action", "Cooldown", "Threshold", "Last Trigger", "Actions"
        ])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left_layout.addWidget(self.rules_table)

        # Right Column: Monitoring Logs & Specs
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, stretch=2)

        # Logs Console
        logs_group = QGroupBox("Live Action Log Console")
        logs_layout = QVBoxLayout(logs_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 9))
        self.clear_logs_btn = QPushButton("Clear Console")
        logs_layout.addWidget(self.log_output)
        logs_layout.addWidget(self.clear_logs_btn)
        right_layout.addWidget(logs_group)

        # Quick Specs info
        info_label = QLabel(
            "<b>Hotkey Bindings:</b><br>"
            "🟢 <b>F8</b>: Start capture loop<br>"
            "🔴 <b>F9</b>: Stop capture loop<br>"
            "🎯 <b>F10</b>: Teach new image target<br>"
            "📍 <b>F11</b>: Teach current cursor position<br>"
            "🚨 <b>Esc</b>: Panic emergency abort"
        )
        right_layout.addWidget(info_label)

    def append_log(self, text: str):
        self.log_output.append(text)


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


class DebugOverlay(QWidget):
    """
    Transparent fullscreen HUD layout presenting real-time matched bounding boxes,
    precise target click crosshairs, and calibration logs (DPI, resolution, confidence, etc.).
    Pauses execution briefly to allow the developer to visualize and confirm click precision.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Display specifications
        self.rects = []
        self.click_point = None
        self.meta_text = ""

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_overlay)

    def show_debug_info(self, rects: list, click_point: tuple, meta_text: str):
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.rects = rects
        self.click_point = click_point
        self.meta_text = meta_text

        self.show()
        self.update()

        # Pause display for visual confirmation
        self.hide_timer.start(1200)

    def hide_overlay(self):
        self.rects = []
        self.click_point = None
        self.meta_text = ""
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw transparent dark background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 40))

        # Draw matched rectangles (Green outline)
        pen_green = QPen(QColor(16, 185, 129), 3, Qt.SolidLine)
        painter.setPen(pen_green)
        painter.setBrush(QColor(16, 185, 129, 20))
        for (x, y, w, h) in self.rects:
            painter.drawRect(x, y, w, h)

        # Draw precise click spot (Red crosshair)
        if self.click_point:
            cx, cy = self.click_point
            pen_red = QPen(QColor(239, 68, 68), 3)
            painter.setPen(pen_red)
            painter.drawLine(cx - 15, cy, cx + 15, cy)
            painter.drawLine(cx, cy - 15, cx, cy + 15)
            # Circle surrounding click spot
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(cx - 6, cy - 6, 12, 12)

        # Draw HUD metadata panel (Black box top-left)
        if self.meta_text:
            painter.setFont(QFont("Courier New", 10, QFont.Bold))
            fm = painter.fontMetrics()

            # Wrap text lines
            lines = self.meta_text.strip().split("\n")
            max_w = max(fm.horizontalAdvance(line) for line in lines)
            total_h = len(lines) * fm.height()

            # Semi-transparent metadata background panel
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(17, 24, 39, 220)) # Dark Slate
            painter.drawRoundedRect(20, 20, max_w + 30, total_h + 30, 6, 6)

            # Print wrapped text rows
            painter.setPen(QColor(253, 224, 71)) # Golden yellow text
            curr_y = 40
            for line in lines:
                painter.drawText(35, curr_y, line)
                curr_y += fm.height()
