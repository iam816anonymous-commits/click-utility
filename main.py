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
from ui import NativeDashboard, TeachOverlay, SaveTargetDialog, MatchHighlightOverlay

class MacroRule:
    """
    Data model representing a visual macro click rule.
    """
    def __init__(self, id_str: str, name: str, trigger_type: str, action: str, cooldown: float, threshold: float, template_path: str, click_steps: list = None, abs_x: int = None, abs_y: int = None, window_title: str = None, window_offset_x: int = None, window_offset_y: int = None, window_handle: int = None, countdown_delay: int = None, coordinate_history: list = None, search_region: str = "Entire Screen", anchor_rule_id: str = None, train_x: int = None, train_y: int = None, train_w: int = None, train_h: int = None):
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
        self.window_handle = window_handle
        self.countdown_delay = countdown_delay
        self.coordinate_history = coordinate_history if coordinate_history is not None else []
        self.search_region = search_region # "Entire Screen", "Active Window Only", "Trained Region Only"
        self.anchor_rule_id = anchor_rule_id # ID of rule that serves as Anchor
        self.train_x = train_x
        self.train_y = train_y
        self.train_w = train_w
        self.train_h = train_h
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
    highlight_signal = Signal(list) # list of Tuples (x, y, w, h)

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

                    # Initialize anchor displacement
                    dx, dy = 0, 0
                    anchor_found = False
                    if rule.anchor_rule_id:
                        # Find the anchor rule in active_rules_snapshot
                        anchor_rule = None
                        for r in active_rules_snapshot:
                            if r.id_str == rule.anchor_rule_id:
                                anchor_rule = r
                                break

                        if anchor_rule and os.path.exists(anchor_rule.template_path):
                            anchor_temp = cv2.imread(anchor_rule.template_path, cv2.IMREAD_COLOR)
                            if anchor_temp is not None:
                                # Match anchor on screen
                                anchor_match = MatchEngine.match_template(screen, anchor_temp, threshold=anchor_rule.threshold)
                                if anchor_match:
                                    acx, acy, aconf = anchor_match
                                    # Anchor training center
                                    atcx = anchor_rule.train_x + anchor_rule.train_w // 2
                                    atcy = anchor_rule.train_y + anchor_rule.train_h // 2
                                    dx = acx - atcx
                                    dy = acy - atcy
                                    anchor_found = True
                                    # Highlight anchor template
                                    ahw, ahh = anchor_temp.shape[1], anchor_temp.shape[0]
                                    self.highlight_signal.emit([(acx - ahw//2, acy - ahh//2, ahw, ahh)])

                    # If anchor rule ID is set but anchor not found, skip/warn to be safe
                    if rule.anchor_rule_id and not anchor_found:
                        # Throttled logging
                        if not hasattr(rule, "last_anchor_missing_log"):
                            rule.last_anchor_missing_log = 0.0
                        if now - rule.last_anchor_missing_log > 5.0:
                            rule.last_anchor_missing_log = now
                            self.log_signal.emit(f"[⚠️] Anchor rule for '{rule.name}' not found on screen. Skipping dependent rule.")
                        continue

                    # Determine Search Region
                    # We crop screen to the defined search region before passing to matching
                    crop_x1, crop_y1 = 0, 0
                    search_area = screen

                    if rule.search_region == "Active Window Only":
                        title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()
                        # Allow headless tests bypass
                        if "Headless" not in title:
                            crop_x1 = max(0, wx)
                            crop_y1 = max(0, wy)
                            crop_x2 = min(screen.shape[1], wx + ww)
                            crop_y2 = min(screen.shape[0], wy + wh)
                            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                                search_area = screen[crop_y1:crop_y2, crop_x1:crop_x2]
                            else:
                                continue # Invalid active window bounds

                    elif rule.search_region == "Trained Region Only":
                        if rule.train_x is not None and rule.train_y is not None:
                            # Apply anchor displacement to trained region coordinates
                            tx = rule.train_x + dx
                            ty = rule.train_y + dy
                            tw = rule.train_w
                            th = rule.train_h

                            # Pad slightly
                            pad = 30
                            crop_x1 = max(0, tx - pad)
                            crop_y1 = max(0, ty - pad)
                            crop_x2 = min(screen.shape[1], tx + tw + pad)
                            crop_y2 = min(screen.shape[0], ty + th + pad)
                            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                                search_area = screen[crop_y1:crop_y2, crop_x1:crop_x2]
                            else:
                                continue

                    # Image Template Match Trigger
                    if rule.trigger_type == "Image Template Match":
                        if not os.path.exists(rule.template_path):
                            continue

                        template = cv2.imread(rule.template_path, cv2.IMREAD_COLOR)
                        if template is None:
                            continue

                        # Match multi template
                        matches = MatchEngine.match_template_multi(search_area, template, threshold=rule.threshold)

                        if len(matches) > 1:
                            # Highlight all matches
                            th, tw = template.shape[:2]
                            rects = []
                            for (cx, cy, conf) in matches:
                                rects.append((cx + crop_x1 - tw//2, cy + crop_y1 - th//2, tw, th))
                            self.highlight_signal.emit(rects)

                            # Warning & Skip
                            if not hasattr(rule, "last_multi_match_log"):
                                rule.last_multi_match_log = 0.0
                            if now - rule.last_multi_match_log > 3.0:
                                rule.last_multi_match_log = now
                                self.log_signal.emit(
                                    f"[⚠️] Multiple distinct matches ({len(matches)}) found for '{rule.name}'. "
                                    f"Skipping click sequence to prevent random clicking."
                                )
                            continue

                        elif len(matches) == 1:
                            cx, cy, conf = matches[0]
                            best_x = cx + crop_x1
                            best_y = cy + crop_y1

                            th, tw = template.shape[:2]
                            # Emit highlight for the match
                            self.highlight_signal.emit([(best_x - tw//2, best_y - th//2, tw, th)])

                            # Trigger matches
                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] Match Success: '{rule.name}' matched with {conf*100:.1f}% confidence. "
                                f"Executing click steps..."
                            )

                            # Process steps
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
                                time.sleep(step_delay)
                            break

                    # OCR Text Match Trigger
                    elif rule.trigger_type == "OCR Text Match":
                        match = MatchEngine.match_text_ocr(search_area, rule.name)
                        if match:
                            cx, cy, conf = match
                            best_x = cx + crop_x1
                            best_y = cy + crop_y1

                            # Highlight estimated OCR target region (draw a generic 100x30 box or similar)
                            self.highlight_signal.emit([(best_x - 50, best_y - 15, 100, 30)])

                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] OCR Match Success: Found text '{rule.name}' with {conf*100:.1f}% confidence. Executing click steps..."
                            )

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
                                time.sleep(step_delay)
                            break

                    # Window-Relative Position Trigger
                    elif rule.trigger_type == "Window-Relative Position":
                        if rule.window_offset_x is not None and rule.window_offset_y is not None:
                            window_found = False
                            wx, wy = 0, 0
                            title = rule.window_title

                            try:
                                import pygetwindow as gw
                                all_wins = gw.getWindowsWithTitle(rule.window_title) if rule.window_title else []
                                if all_wins:
                                    target_win = all_wins[0]
                                    if target_win.isMinimized:
                                        target_win.restore()
                                        time.sleep(0.3)
                                    wx = target_win.left
                                    wy = target_win.top
                                    title = target_win.title
                                    window_found = True
                            except Exception:
                                pass

                            if not window_found:
                                try:
                                    title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()
                                    if rule.window_title in title or "Headless" in title:
                                        window_found = True
                                except Exception:
                                    pass

                            if not window_found:
                                self.log_signal.emit(
                                    f"[🚨] Target window '{rule.window_title}' not found. Skipping click sequence to prevent random clicking."
                                )
                                continue

                            # Compute target relative to window + anchor displacement (dx, dy)
                            target_x = wx + rule.window_offset_x + dx
                            target_y = wy + rule.window_offset_y + dy

                            # Highlight target coordinate
                            self.highlight_signal.emit([(target_x - 15, target_y - 15, 30, 30)])

                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] Window Relative Trigger Success: '{rule.name}' inside active window '{title}' "
                                f"at offset [{rule.window_offset_x}, {rule.window_offset_y}] (Shifted dx:{dx}, dy:{dy}) -> Screen [{target_x}, {target_y}]. "
                                f"Executing click steps..."
                            )

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
                                time.sleep(step_delay)
                            break

                    # Absolute Cursor Position Trigger
                    elif rule.trigger_type == "Absolute Cursor Position":
                        if rule.abs_x is not None and rule.abs_y is not None:
                            # Shift absolute coordinates based on anchor displacement
                            target_x = rule.abs_x + dx
                            target_y = rule.abs_y + dy

                            # Highlight target coordinate
                            self.highlight_signal.emit([(target_x - 15, target_y - 15, 30, 30)])

                            with self.lock:
                                rule.last_triggered = now

                            self.log_signal.emit(
                                f"[+] Absolute Trigger Success: '{rule.name}' at [{target_x}, {target_y}] (Shifted dx:{dx}, dy:{dy}). Executing click steps..."
                            )

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
                                time.sleep(step_delay)
                            break

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
        self.highlight_overlay = MatchHighlightOverlay()

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
        self.monitor_thread.highlight_signal.connect(self.highlight_overlay.highlight_matches)

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

        # Safely copy rules under lock to pass as snapshot for Anchor Selection
        with self.lock:
            rules_snapshot = list(self.rules)

        # Pop save dialog pre-populated with cursor coordinates and rules snapshot
        dialog = SaveTargetDialog(self.dashboard, abs_x=mx, abs_y=my, rules_snapshot=rules_snapshot)
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

            # Extract anchor rule ID if selected
            anchor_rule_id = None
            if dialog.anchor_select_combo.currentIndex() > 0:
                anchor_rule_id = dialog.anchor_select_combo.currentData()

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
                    window_offset_y=dialog.window_offset_y,
                    search_region=dialog.region_combo.currentText(),
                    anchor_rule_id=anchor_rule_id
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

        # Safely copy rules under lock to pass as snapshot for Anchor Selection
        with self.lock:
            rules_snapshot = list(self.rules)

        # Pop save dialog
        dialog = SaveTargetDialog(self.dashboard, rules_snapshot=rules_snapshot)
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

            # Extract anchor rule ID if selected
            anchor_rule_id = None
            if dialog.anchor_select_combo.currentIndex() > 0:
                anchor_rule_id = dialog.anchor_select_combo.currentData()

            try:
                self.capture_engine.save_template(x, y, w, h, filepath)

                # Add Macro Rule safely under Thread Lock
                new_rule = MacroRule(
                    id_str=rule_id,
                    name=name,
                    trigger_type=trigger_type,
                    action=action,
                    cooldown=cooldown,
                    threshold=threshold,
                    template_path=filepath,
                    click_steps=click_steps,
                    search_region=dialog.region_combo.currentText(),
                    anchor_rule_id=anchor_rule_id,
                    train_x=x,
                    train_y=y,
                    train_w=w,
                    train_h=h
                )
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
