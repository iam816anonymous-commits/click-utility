import sys
import os
import threading
import time
from PySide6.QtCore import Slot, Qt, QObject
from PySide6.QtWidgets import QApplication, QDialog

# Import custom modular packages
from capture_engine import CaptureEngine
from click_engine import ClickEngine
from models.automation_rule import MacroRule
from workers.monitoring_worker import MonitoringWorker
from controllers.rule_controller import RuleController
from ui import NativeDashboard, SaveTargetDialog, DebugOverlay, TeachOverlay, MatchHighlightOverlay

class ApplicationCoordinator(QObject):
    """
    Pure Application Coordinator and Bootstrapper.
    Delegates all macro business logic and UI rendering updates to rule_controller.py.
    """
    def __init__(self, app_instance: QApplication):
        super().__init__()
        self.app = app_instance
        self.capture_engine = CaptureEngine()
        self.rules: list[MacroRule] = []
        self.lock = threading.Lock()

        os.makedirs("targets", exist_ok=True)

        self.dashboard = NativeDashboard()
        self.teach_overlay = TeachOverlay()
        self.highlight_overlay = MatchHighlightOverlay()
        self.debug_overlay = DebugOverlay()

        self.click_engine = ClickEngine()
        self.monitor_thread = MonitoringWorker(self.capture_engine, self.rules, self.click_engine, self.lock)

        # Instantiate Stage-based Rule Controller
        self.rule_controller = RuleController(
            self.dashboard, self.rules, self.lock, self.click_engine, self.capture_engine
        )

        self.connect_signals()

    def connect_signals(self):
        # Bind Start/Stop and Teach toolbar buttons
        self.dashboard.start_btn.clicked.connect(self.start_monitoring)
        self.dashboard.stop_btn.clicked.connect(self.stop_monitoring)
        self.dashboard.teach_btn.clicked.connect(self.trigger_teach)
        self.dashboard.teach_cursor_btn.clicked.connect(self.trigger_teach_cursor)
        self.dashboard.calibrate_btn.clicked.connect(self.launch_calibration_wizard)
        self.dashboard.clear_logs_btn.clicked.connect(self.dashboard.log_output.clear)

        # Connect template manager replaces/deletes
        self.dashboard.template_manager.delete_btn.clicked.connect(
            lambda: self.rule_controller.delete_rule(
                self.dashboard.template_manager.list_widget.currentItem().text() if self.dashboard.template_manager.list_widget.currentItem() else ""
            )
        )
        self.dashboard.template_manager.replace_btn.clicked.connect(
            lambda: self.rule_controller.handle_manager_replace(self.trigger_teach)
        )
        self.dashboard.settings_page.settings_saved.connect(self.handle_settings_saved)
        self.dashboard.rules_table.itemSelectionChanged.connect(self.rule_controller.refresh_rules_table)

        self.teach_overlay.region_selected.connect(self.handle_region_selected)

        # Monitor Thread to UI bindings
        self.monitor_thread.log_signal.connect(self.dashboard.append_log)
        self.monitor_thread.click_signal.connect(self.perform_macro_click)
        self.monitor_thread.highlight_signal.connect(self.highlight_overlay.highlight_matches)
        self.monitor_thread.debug_overlay_signal.connect(self.debug_overlay.show_debug_info)
        self.monitor_thread.live_debug_signal.connect(self.handle_live_debug_update)

        # ClickEngine F8/F9/F10 and Esc Hooks bindings
        self.click_engine.start_signal.connect(self.start_monitoring)
        self.click_engine.stop_signal.connect(self.stop_monitoring)
        self.click_engine.teach_signal.connect(self.trigger_teach)
        self.click_engine.teach_cursor_signal.connect(self.trigger_teach_cursor)
        self.click_engine.emergency_signal.connect(self.emergency_abort)

    def launch_calibration_wizard(self):
        from ui.calibration_dialog import CalibrationWizard
        wizard = CalibrationWizard(self.dashboard)
        wizard.calibration_complete.connect(self.store_calibration_factors)
        wizard.exec()

    @Slot(float, float)
    def store_calibration_factors(self, correction_x: float, correction_y: float):
        with self.lock:
            for rule in self.rules:
                rule.calibration_correction_x = correction_x
                rule.calibration_correction_y = correction_y
        self.dashboard.append_log(f"[⚙️] Calibration factors configured: X: {correction_x}x, Y: {correction_y}x")

    @Slot()
    def start_monitoring(self):
        if not self.monitor_thread.isRunning():
            self.monitor_thread.move_only = self.dashboard.move_only_chk.isChecked()
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
        self.teach_overlay.show_overlay()

    @Slot()
    def trigger_teach_cursor(self):
        import pyautogui
        mx, my = pyautogui.position()
        with self.lock:
            rules_snapshot = list(self.rules)
        _, _, _, win_w, win_h = self.capture_engine.get_active_window_rect()

        dialog = SaveTargetDialog(self.dashboard, abs_x=mx, abs_y=my, rules_snapshot=rules_snapshot)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text()
            trigger_type = dialog.trigger_combo.currentText()
            cooldown = float(dialog.cooldown_combo.currentText())
            threshold = float(dialog.conf_slider.value()) / 100.0
            click_steps = dialog.click_steps
            action = click_steps[0]["action"] if len(click_steps) == 1 else f"Sequence ({len(click_steps)} steps)"
            rule_id = f"rule_{int(time.time())}"

            anchor_rule_id = dialog.anchor_select_combo.currentData() if dialog.anchor_select_combo.currentIndex() > 0 else None

            new_rule = MacroRule(
                id_str=rule_id, name=name, trigger_type=trigger_type, action=action, cooldown=cooldown, threshold=threshold,
                template_path="", click_steps=click_steps, abs_x=dialog.abs_x, abs_y=dialog.abs_y,
                window_title=dialog.window_title, window_offset_x=dialog.window_offset_x, window_offset_y=dialog.window_offset_y,
                search_region=dialog.region_combo.currentText(), anchor_rule_id=anchor_rule_id, window_client_w=win_w, window_client_h=win_h
            )
            with self.lock:
                self.rules.append(new_rule)
            self.rule_controller.refresh_rules_table()
            self.dashboard.append_log(f"[✓] Saved new rule: '{name}'")

    @Slot(int, int, int, int)
    def handle_region_selected(self, x: int, y: int, w: int, h: int):
        # Handle Replace Template Action safely
        if self.rule_controller.replacing_rule_id:
            with self.lock:
                for rule in self.rules:
                    if rule.id_str == self.rule_controller.replacing_rule_id:
                        self.capture_engine.save_template(x, y, w, h, rule.template_path)
                        rule.train_x = x
                        rule.train_y = y
                        rule.train_w = w
                        rule.train_h = h
                        self.dashboard.append_log(f"[✓] Successfully replaced template for rule '{rule.name}'!")
                        break
            self.rule_controller.replacing_rule_id = None
            self.rule_controller.refresh_rules_table()
            self.dashboard.template_manager.refresh_templates()
            return

        with self.lock:
            rules_snapshot = list(self.rules)
        rule_id = f"rule_{int(time.time())}"
        filepath = os.path.join("targets", f"{rule_id}.png")
        self.capture_engine.save_template(x, y, w, h, filepath)
        _, _, _, win_w, win_h = self.capture_engine.get_active_window_rect()

        dialog = SaveTargetDialog(self.dashboard, rules_snapshot=rules_snapshot, template_path=filepath)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text()
            trigger_type = dialog.trigger_combo.currentText()
            cooldown = float(dialog.cooldown_combo.currentText())
            threshold = float(dialog.conf_slider.value()) / 100.0
            click_steps = dialog.click_steps
            action = click_steps[0]["action"] if len(click_steps) == 1 else f"Sequence ({len(click_steps)} steps)"
            anchor_rule_id = dialog.anchor_select_combo.currentData() if dialog.anchor_select_combo.currentIndex() > 0 else None

            new_rule = MacroRule(
                id_str=rule_id, name=name, trigger_type=trigger_type, action=action, cooldown=cooldown, threshold=threshold,
                template_path=filepath, click_steps=click_steps, abs_x=dialog.abs_x, abs_y=dialog.abs_y,
                window_title=dialog.window_title, window_offset_x=dialog.window_offset_x, window_offset_y=dialog.window_offset_y,
                search_region=dialog.region_combo.currentText(), anchor_rule_id=anchor_rule_id, train_x=x, train_y=y, train_w=w, train_h=h,
                click_offset_x=dialog.click_offset_x, click_offset_y=dialog.click_offset_y, window_client_w=win_w, window_client_h=win_h
            )
            with self.lock:
                self.rules.append(new_rule)
            self.rule_controller.refresh_rules_table()
            self.dashboard.template_manager.refresh_templates()
            self.dashboard.append_log(f"[✓] Saved target rule: '{name}' template saved to {filepath}")

    @Slot()
    def trigger_stress_test(self):
        self.rule_controller.trigger_stress_test()

    @Slot(str, str, str, str, str, str)
    def handle_live_debug_update(self, rule_id, state, conf, click_coords, region, execution_time):
        row = self.dashboard.rules_table.currentRow()
        if row >= 0:
            with self.lock:
                if row < len(self.rules) and self.rules[row].id_str == rule_id:
                    self.dashboard.debug_panel.update_debug_view(
                        self.rules[row].template_path, state, conf, click_coords, region, execution_time
                    )

    def handle_settings_saved(self):
        fps = self.dashboard.settings_page.fps_combo.currentText()
        delay = self.dashboard.settings_page.click_delay_input.text()
        try:
            self.monitor_thread.fps_limit = float(fps)
            self.monitor_thread.click_synthesizer_delay = float(delay)
        except ValueError:
            pass
        self.dashboard.append_log(f"[⚙️] Application Settings Applied: FPS={fps}, Click Delay={delay}s")

    def start_hotkeys(self):
        self.click_engine.start_hotkeys_listener()
        self.dashboard.append_log("[*] Global Hotkey Listener started: F8 (Start), F9 (Stop), F10 (Teach), F11 (Teach Cursor), ESC (Abort)")

    def refresh_rules_table(self):
        self.rule_controller.refresh_rules_table()

    @Slot(int, int, str)
    def perform_macro_click(self, x: int, y: int, action_type: str):
        self.click_engine.trigger_click(x, y, action_type)

    @Slot()
    def emergency_abort(self):
        self.stop_monitoring()
        self.click_engine.release_all_buttons()
        self.debug_overlay.hide_overlay()
        self.highlight_overlay.clear_highlights()
        self.dashboard.append_log("[🚨] EMERGENCY PANIC STOP ENGAGED. Clicks released, overlays destroyed under 100ms.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    coordinator = ApplicationCoordinator(app)
    coordinator.dashboard.show()
    coordinator.start_hotkeys()
    sys.exit(app.exec())
