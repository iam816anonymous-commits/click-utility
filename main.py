import sys
import os
import cv2
import threading
import time
from PySide6.QtCore import QThread, Signal, Slot, Qt, QObject
from PySide6.QtWidgets import QApplication, QDialog, QTableWidgetItem, QCheckBox

# Import modular custom engines
from capture_engine import CaptureEngine
from match_engine import MatchEngine
from click_engine import ClickEngine
from ui import NativeDashboard, TeachOverlay, SaveTargetDialog

class MacroRule:
    """
    Data model representing a visual macro click rule.
    """
    def __init__(self, id_str: str, name: str, trigger_type: str, action: str, cooldown: float, threshold: float, template_path: str):
        self.id_str = id_str
        self.name = name
        self.trigger_type = trigger_type
        self.action = action
        self.cooldown = cooldown
        self.threshold = threshold
        self.template_path = template_path
        self.active = True
        self.last_triggered = 0.0


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

                        # Search template in current screen capture
                        match = MatchEngine.match_template(screen, template, rule.threshold)
                        if match:
                            click_x, click_y, conf = match

                            # Safely write the last triggered timestamp
                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] Match Success: '{rule.name}' matched with {conf*100:.1f}% confidence. "
                                f"Triggering {rule.action} at [{click_x}, {click_y}]"
                            )
                            # Emit signal to perform safe GUI thread click
                            self.click_signal.emit(click_x, click_y, rule.action)
                            # Small sleep between matched actions
                            time.sleep(0.1)
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
        self.click_engine.emergency_signal.connect(self.emergency_abort)

    def start_hotkeys(self):
        # Start global keyboard hotkeys in separate thread
        self.click_engine.start_hotkeys_listener()
        self.dashboard.append_log("[*] Global Hotkey Listener started: F8 (Start), F9 (Stop), F10 (Teach), ESC (Abort)")

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

    @Slot(int, int, int, int)
    def handle_region_selected(self, x: int, y: int, w: int, h: int):
        self.dashboard.append_log(f"[*] Captured crop box at: X:{x}, Y:{y} [{w}x{h} px]")

        # Pop save dialog
        dialog = SaveTargetDialog(self.dashboard)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text()
            trigger_type = dialog.trigger_combo.currentText()
            action = dialog.action_combo.currentText()
            cooldown = float(dialog.cooldown_combo.currentText())
            threshold = float(dialog.conf_slider.value()) / 100.0

            # Store cropped screenshot target
            rule_id = f"rule_{int(time.time())}"
            filepath = os.path.join("targets", f"{rule_id}.png")

            try:
                self.capture_engine.save_template(x, y, w, h, filepath)

                # Add Macro Rule safely under Thread Lock
                new_rule = MacroRule(rule_id, name, trigger_type, action, cooldown, threshold, filepath)
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
