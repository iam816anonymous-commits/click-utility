import sys
import os
import cv2
import threading
import time
from PySide6.QtCore import QThread, Signal, Slot, Qt, QObject
from PySide6.QtWidgets import QApplication, QDialog, QTableWidgetItem, QCheckBox, QPushButton

# Import modular custom engines
from capture_engine import CaptureEngine
from match_engine import MatchEngine
from click_engine import ClickEngine
from ui import NativeDashboard, TeachOverlay, SaveTargetDialog

class MacroRule:
    """
    Data model representing a visual macro click rule.
    """
    def __init__(self, id_str: str, name: str, trigger_type: str, action: str, cooldown: float, threshold: float, template_path: str, click_steps: list = None, abs_x: int = None, abs_y: int = None, window_title: str = None, window_offset_x: int = None, window_offset_y: int = None):
        self.id_str = id_str
        self.name = name
        self.trigger_type = trigger_type
        self.action = action
        self.cooldown = cooldown
        self.threshold = threshold
        self.template_path = template_path
        self.abs_x = abs_x
        self.abs_y = abs_y
        self.window_title = window_title
        self.window_offset_x = window_offset_x
        self.window_offset_y = window_offset_y
        self.active = True
        self.last_triggered = 0.0
        # If no click steps specified, default to a single step at the center (offset 0,0)
        if click_steps is None:
            self.click_steps = [{"action": action, "offset_x": 0, "offset_y": 0, "delay": 0.5}]
        else:
            self.click_steps = click_steps


class MonitoringWorker(QThread):
    """
    Background worker thread running the ultra-fast screen scanning and match-firing loop.
    Safe against concurrent collection mutation by using thread locking.
    """
    log_signal = Signal(str)
    click_signal = Signal(int, int, str) # x, y, action

    def __init__(self, capture_engine: CaptureEngine, rules: list[MacroRule], lock: threading.Lock):
        super().__init__()
        self.capture_engine = capture_engine
        self.rules = rules
        self.lock = lock
        self.running = False

    def run(self):
        self.running = True
        self.log_signal.emit("[*] Background screen capture loop activated.")

        while self.running:
            try:
                # Capture full screen using MSS
                screen = self.capture_engine.capture_full_screen()
                now = time.time()

                # Safely iterate over a copy of the rules list under lock to avoid race conditions
                active_rules_snapshot = []
                with self.lock:
                    active_rules_snapshot = list(self.rules)

                for rule in active_rules_snapshot:
                    if not rule.active:
                        continue

                    # Cooldown check
                    if now - rule.last_triggered < rule.cooldown:
                        continue

                    # Template matching
                    if rule.trigger_type == "Image Template Match":
                        # Load template image
                        if not os.path.exists(rule.template_path):
                            continue

                        template = cv2.imread(rule.template_path, cv2.IMREAD_COLOR)
                        if template is None:
                            continue

                        # Search template in current screen capture (pass threshold=0.0 to find the best candidate)
                        match = MatchEngine.match_template(screen, template, threshold=0.0)
                        if match:
                            best_x, best_y, conf = match
                            if conf >= rule.threshold:
                                # Safely write the last triggered timestamp
                                with self.lock:
                                    rule.last_triggered = now

                                self.log_signal.emit(
                                    f"[+] Match Success: '{rule.name}' matched with {conf*100:.1f}% confidence "
                                    f"(threshold {rule.threshold*100:.1f}%). Executing click steps..."
                                )

                                # Process each step in sequence
                                for i, step in enumerate(rule.click_steps):
                                    step_action = step["action"]
                                    step_x = best_x + step["offset_x"]
                                    step_y = best_y + step["offset_y"]
                                    step_delay = step["delay"]

                                    self.log_signal.emit(
                                        f"  -> Step #{i+1}: Clicking '{step_action}' at [{step_x}, {step_y}] "
                                        f"(offset: {step['offset_x']},{step['offset_y']}). Delay: {step_delay}s"
                                    )

                                    self.click_signal.emit(step_x, step_y, step_action)
                                    # Sleep after this step
                                    time.sleep(step_delay)
                                break # execute one match per cycle
                            else:
                                # Throttle mismatch logging to avoid flooding the console
                                if not hasattr(rule, "last_mismatch_log"):
                                    rule.last_mismatch_log = 0.0
                                if now - rule.last_mismatch_log > 3.0:
                                    rule.last_mismatch_log = now
                                    self.log_signal.emit(
                                        f"[*] Scan: Best candidate for '{rule.name}' is at [{best_x}, {best_y}] "
                                        f"with {conf*100:.1f}% confidence. (Threshold is {rule.threshold*100:.1f}%)."
                                    )

                    # OCR matching
                    elif rule.trigger_type == "OCR Text Match":
                        match = MatchEngine.match_text_ocr(screen, rule.name)
                        if match:
                            best_x, best_y, conf = match
                            # Safely write the last triggered timestamp
                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] OCR Match Success: Found text '{rule.name}' with {conf*100:.1f}% confidence. Executing click steps..."
                            )

                            # Process each step in sequence
                            for i, step in enumerate(rule.click_steps):
                                step_action = step["action"]
                                step_x = best_x + step["offset_x"]
                                step_y = best_y + step["offset_y"]
                                step_delay = step["delay"]

                                self.log_signal.emit(
                                    f"  -> Step #{i+1}: Clicking '{step_action}' at [{step_x}, {step_y}] "
                                    f"(offset: {step['offset_x']},{step['offset_y']}). Delay: {step_delay}s"
                                )

                                self.click_signal.emit(step_x, step_y, step_action)
                                # Sleep after this step
                                time.sleep(step_delay)
                            break # execute one match per cycle

                    # Window-Relative Position matching
                    elif rule.trigger_type == "Window-Relative Position":
                        if rule.window_offset_x is not None and rule.window_offset_y is not None:
                            # Retrieve the current active window location on the screen
                            title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()

                            # Calculate current absolute coordinates based on active window and saved offset
                            target_x = wx + rule.window_offset_x
                            target_y = wy + rule.window_offset_y

                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] Window Relative Trigger Success: '{rule.name}' inside active window '{title}' "
                                f"at offset [{rule.window_offset_x}, {rule.window_offset_y}] -> Screen [{target_x}, {target_y}]. "
                                f"Executing click steps..."
                            )

                            # Process each step in sequence relative to computed active window target coordinates
                            for i, step in enumerate(rule.click_steps):
                                step_action = step["action"]
                                step_x = target_x + step["offset_x"]
                                step_y = target_y + step["offset_y"]
                                step_delay = step["delay"]

                                self.log_signal.emit(
                                    f"  -> Step #{i+1}: Clicking '{step_action}' at [{step_x}, {step_y}] "
                                    f"(offset: {step['offset_x']},{step['offset_y']}). Delay: {step_delay}s"
                                )

                                self.click_signal.emit(step_x, step_y, step_action)
                                # Sleep after this step
                                time.sleep(step_delay)
                            break # execute one match per cycle

                    # Absolute Cursor Position matching
                    elif rule.trigger_type == "Absolute Cursor Position":
                        if rule.abs_x is not None and rule.abs_y is not None:
                            # Bypasses screen matching/scanning and triggers the steps directly!
                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] Absolute Trigger Success: '{rule.name}' at [{rule.abs_x}, {rule.abs_y}]. Executing click steps..."
                            )

                            # Process each step in sequence relative to the absolute coordinates
                            for i, step in enumerate(rule.click_steps):
                                step_action = step["action"]
                                step_x = rule.abs_x + step["offset_x"]
                                step_y = rule.abs_y + step["offset_y"]
                                step_delay = step["delay"]

                                self.log_signal.emit(
                                    f"  -> Step #{i+1}: Clicking '{step_action}' at [{step_x}, {step_y}] "
                                    f"(offset: {step['offset_x']},{step['offset_y']}). Delay: {step_delay}s"
                                )

                                self.click_signal.emit(step_x, step_y, step_action)
                                # Sleep after this step
                                time.sleep(step_delay)
                            break # execute one match per cycle

                # Delay between scans (e.g. scanning ~10 times per second)
                time.sleep(0.1)

            except Exception as e:
                self.log_signal.emit(f"[!] Error in capture loop: {e}")
                time.sleep(0.5)

    def stop(self):
        self.running = False


class ApplicationCoordinator(QObject):
    """
    Orchestrates the entire Native Python Desktop Macro platform.
    """
    def __init__(self, app_instance: QApplication):
        super().__init__()
        self.app = app_instance
        self.capture_engine = CaptureEngine()
        self.rules: list[MacroRule] = []
        self.lock = threading.Lock() # Thread lock protecting rule list reads and mutations

        # Create target storage directory
        os.makedirs("targets", exist_ok=True)

        # Initialize GUI components
        self.dashboard = NativeDashboard()
        self.teach_overlay = TeachOverlay()

        # Initialize background monitor worker thread
        self.monitor_thread = MonitoringWorker(self.capture_engine, self.rules, self.lock)

        # Initialize Click & Hotkey engine
        self.click_engine = ClickEngine()

        # Setup GUI signal connections
        self.connect_signals()

    def connect_signals(self):
        # UI Button actions
        self.dashboard.start_btn.clicked.connect(self.start_monitoring)
        self.dashboard.stop_btn.clicked.connect(self.stop_monitoring)
        self.dashboard.teach_btn.clicked.connect(self.trigger_teach)
        self.dashboard.teach_cursor_btn.clicked.connect(self.trigger_teach_cursor)
        self.dashboard.clear_logs_btn.clicked.connect(self.dashboard.log_output.clear)

        # Teach overlay capture triggers
        self.teach_overlay.region_selected.connect(self.handle_region_selected)

        # Monitor thread signals
        self.monitor_thread.log_signal.connect(self.dashboard.append_log)
        self.monitor_thread.click_signal.connect(self.perform_macro_click)

        # Global Hotkey Thread-Safe Signal bindings
        self.click_engine.start_signal.connect(self.start_monitoring)
        self.click_engine.stop_signal.connect(self.stop_monitoring)
        self.click_engine.teach_signal.connect(self.trigger_teach)
        self.click_engine.teach_cursor_signal.connect(self.trigger_teach_cursor)
        self.click_engine.emergency_signal.connect(self.emergency_abort)

    def start_hotkeys(self):
        # Start global keyboard hotkeys in separate thread
        self.click_engine.start_hotkeys_listener()
        self.dashboard.append_log("[*] Global Hotkey Listener started: F8 (Start), F9 (Stop), F10 (Teach), F11 (Teach Cursor), ESC (Abort)")

    @Slot()
    def start_monitoring(self):
        if not self.monitor_thread.isRunning():
            self.monitor_thread.start()
            self.dashboard.append_log("[▶] Screen Monitoring started.")

    @Slot()
    def stop_monitoring(self):
        if self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            self.dashboard.append_log("[⏸] Screen Monitoring stopped.")

    @Slot()
    def trigger_teach(self):
        self.dashboard.append_log("[*] Initializing crosshair teaching overlay. Draw bounding box over target button.")
        self.teach_overlay.show_overlay()

    @Slot()
    def trigger_teach_cursor(self):
        import pyautogui
        mx, my = pyautogui.position()
        self.dashboard.append_log(f"[*] Capturing current cursor coordinates: [{mx}, {my}].")

        # Pop save dialog pre-populated with cursor coordinates
        dialog = SaveTargetDialog(self.dashboard, abs_x=mx, abs_y=my)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text()
            trigger_type = dialog.trigger_combo.currentText()
            cooldown = float(dialog.cooldown_combo.currentText())
            threshold = float(dialog.conf_slider.value()) / 100.0

            click_steps = dialog.click_steps
            if len(click_steps) == 1:
                action = click_steps[0]["action"]
            else:
                action = f"Sequence ({len(click_steps)} steps)"

            rule_id = f"rule_{int(time.time())}"
            filepath = ""

            try:
                new_rule = MacroRule(
                    id_str=rule_id,
                    name=name,
                    trigger_type=trigger_type,
                    action=action,
                    cooldown=cooldown,
                    threshold=threshold,
                    template_path=filepath,
                    click_steps=click_steps,
                    abs_x=mx,
                    abs_y=my,
                    window_title=dialog.window_title,
                    window_offset_x=dialog.window_offset_x,
                    window_offset_y=dialog.window_offset_y
                )
                with self.lock:
                    self.rules.append(new_rule)

                self.refresh_rules_table()
                self.dashboard.append_log(f"[✓] Saved new rule: '{name}' (Trigger: {trigger_type})")
            except Exception as e:
                self.dashboard.append_log(f"[!] Failed to save rule: {e}")

    @Slot(int, int, int, int)
    def handle_region_selected(self, x: int, y: int, w: int, h: int):
        self.dashboard.append_log(f"[*] Captured crop box at: X:{x}, Y:{y} [{w}x{h} px]")

        # Pop save dialog
        dialog = SaveTargetDialog(self.dashboard)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text()
            trigger_type = dialog.trigger_combo.currentText()
            cooldown = float(dialog.cooldown_combo.currentText())
            threshold = float(dialog.conf_slider.value()) / 100.0

            click_steps = dialog.click_steps
            if len(click_steps) == 1:
                action = click_steps[0]["action"]
            else:
                action = f"Sequence ({len(click_steps)} steps)"

            # Store cropped screenshot target
            rule_id = f"rule_{int(time.time())}"
            filepath = os.path.join("targets", f"{rule_id}.png")

            try:
                self.capture_engine.save_template(x, y, w, h, filepath)

                # Add Macro Rule safely under Thread Lock
                new_rule = MacroRule(rule_id, name, trigger_type, action, cooldown, threshold, filepath, click_steps=click_steps)
                with self.lock:
                    self.rules.append(new_rule)

                self.refresh_rules_table()
                self.dashboard.append_log(f"[✓] Saved new target rule: '{name}' template saved to {filepath}")
            except Exception as e:
                self.dashboard.append_log(f"[!] Failed to save template: {e}")

    def refresh_rules_table(self):
        # Safely read rules snapshot under lock for UI refresh
        rules_snapshot = []
        with self.lock:
            rules_snapshot = list(self.rules)

        self.dashboard.rules_table.setRowCount(len(rules_snapshot))
        for row, rule in enumerate(rules_snapshot):
            # Active check box
            chk = QCheckBox()
            chk.setChecked(rule.active)

            # Setup safe status updater with lock
            def make_active_updater(target_rule):
                return lambda state: setattr(target_rule, "active", state == Qt.Checked)

            chk.stateChanged.connect(make_active_updater(rule))
            self.dashboard.rules_table.setCellWidget(row, 0, chk)

            # Metadata columns
            self.dashboard.rules_table.setItem(row, 1, QTableWidgetItem(rule.name))
            self.dashboard.rules_table.setItem(row, 2, QTableWidgetItem(rule.trigger_type))
            self.dashboard.rules_table.setItem(row, 3, QTableWidgetItem(rule.action))
            self.dashboard.rules_table.setItem(row, 4, QTableWidgetItem(f"{rule.cooldown}s"))
            self.dashboard.rules_table.setItem(row, 5, QTableWidgetItem(f"{rule.threshold*100:.0f}%"))
            self.dashboard.rules_table.setItem(row, 6, QTableWidgetItem("Never"))

            # Delete button
            del_btn = QPushButton("🗑️ Delete")
            del_btn.setToolTip("Delete this rule")

            def make_rule_deleter(target_rule_id):
                return lambda: self.delete_rule(target_rule_id)

            del_btn.clicked.connect(make_rule_deleter(rule.id_str))
            self.dashboard.rules_table.setCellWidget(row, 7, del_btn)

    def delete_rule(self, rule_id: str):
        # Safely mutate rules list under lock
        with self.lock:
            # Find and remove rule
            rule_to_remove = None
            for r in self.rules:
                if r.id_str == rule_id:
                    rule_to_remove = r
                    break

            if rule_to_remove:
                self.rules.remove(rule_to_remove)
                # Try to delete file from disk
                try:
                    if os.path.exists(rule_to_remove.template_path):
                        os.remove(rule_to_remove.template_path)
                except Exception as e:
                    self.dashboard.append_log(f"[!] Warning: Could not delete rule template file: {e}")
                self.dashboard.append_log(f"[-] Deleted rule: '{rule_to_remove.name}'")

        self.refresh_rules_table()

    @Slot(int, int, str)
    def perform_macro_click(self, x: int, y: int, action_type: str):
        # Delegate click to ClickEngine safely
        self.click_engine.trigger_click(x, y, action_type)

    @Slot()
    def emergency_abort(self):
        self.stop_monitoring()
        self.dashboard.append_log("[🚨] EMERGENCY PANIC STOP ENGAGED. Automatic clicking aborted immediately.")


if __name__ == "__main__":
    # Create the application
    app = QApplication(sys.argv)

    coordinator = ApplicationCoordinator(app)
    coordinator.dashboard.show()
    coordinator.start_hotkeys()

    # Run the Qt main event loop
    sys.exit(app.exec())
