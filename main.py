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
from ui import NativeDashboard, SaveTargetDialog, DebugOverlay, TeachOverlay, MatchHighlightOverlay

class MacroRule:
    """
    Data model representing a visual macro click rule.
    """
    def __init__(self, id_str: str, name: str, trigger_type: str, action: str, cooldown: float, threshold: float, template_path: str, click_steps: list = None, abs_x: int = None, abs_y: int = None, window_title: str = None, window_offset_x: int = None, window_offset_y: int = None, window_handle: int = None, countdown_delay: int = None, coordinate_history: list = None, search_region: str = "Entire Screen", anchor_rule_id: str = None, train_x: int = None, train_y: int = None, train_w: int = None, train_h: int = None, use_edges: bool = False, click_offset_x: int = None, click_offset_y: int = None, window_client_w: int = None, window_client_h: int = None, dpi_scale: float = 1.0, calibration_correction_x: float = 0.0, calibration_correction_y: float = 0.0):
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
        self.use_edges = use_edges

        # User defined click calibration offset within template (top-left relative)
        self.click_offset_x = click_offset_x
        self.click_offset_y = click_offset_y

        # Stored original window/screen states for calibration
        self.window_client_w = window_client_w
        self.window_client_h = window_client_h
        self.dpi_scale = dpi_scale

        # Stored calibration wizard correction offsets
        self.calibration_correction_x = calibration_correction_x
        self.calibration_correction_y = calibration_correction_y

        # Cache for localized restricted regions
        self.last_matched_region = None # Tuple of (x, y, w, h)

        self.active = True
        self.last_triggered = 0.0

        # Rule statistics tracking attributes
        self.matches_count = 0
        self.clicks_count = 0
        self.failures_count = 0

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
    debug_overlay_signal = Signal(list, tuple, str) # rects, click_point, meta_text
    live_debug_signal = Signal(str, str, str, str, str, str) # rule_id, state, conf, click_coords, region, execution_time

    def __init__(self, capture_engine: CaptureEngine, rules: list[MacroRule], lock: threading.Lock):
        super().__init__()
        self.capture_engine = capture_engine
        self.rules = rules
        self.lock = lock
        self.running = False

        # Performance Settings configuration parameters
        self.fps_limit = 10.0
        self.click_synthesizer_delay = 0.02

    def run(self):
        self.running = True
        self.log_signal.emit("[*] Background screen capture loop activated.")

        while self.running:
            try:
                start_time_cycle = time.time()
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

                    # Auto-detect current scaling and screen resolution
                    screen_w, screen_h = screen.shape[1], screen.shape[0]

                    # DPI Scale detection fallback
                    current_dpi = 1.0
                    try:
                        # Auto-compute scaling ratio dynamically if mismatch is detected
                        primary_screen = QApplication.primaryScreen()
                        if primary_screen:
                            current_dpi = primary_screen.devicePixelRatio()
                    except Exception:
                        pass

                    # Initialize anchor displacement
                    dx, dy = 0, 0
                    anchor_found = False
                    if rule.anchor_rule_id:
                        anchor_rule = None
                        for r in active_rules_snapshot:
                            if r.id_str == rule.anchor_rule_id:
                                anchor_rule = r
                                break

                        if anchor_rule and os.path.exists(anchor_rule.template_path):
                            anchor_temp = cv2.imread(anchor_rule.template_path, cv2.IMREAD_COLOR)
                            if anchor_temp is not None:
                                anchor_match = MatchEngine.match_template(screen, anchor_temp, threshold=anchor_rule.threshold, use_edges=anchor_rule.use_edges)
                                if anchor_match:
                                    acx, acy, aconf = anchor_match
                                    atcx = anchor_rule.train_x + anchor_rule.train_w // 2
                                    atcy = anchor_rule.train_y + anchor_rule.train_h // 2
                                    dx = acx - atcx
                                    dy = acy - atcy
                                    anchor_found = True
                                    ahw, ahh = anchor_temp.shape[1], anchor_temp.shape[0]
                                    self.highlight_signal.emit([(acx - ahw//2, acy - ahh//2, ahw, ahh)])

                    if rule.anchor_rule_id and not anchor_found:
                        if not hasattr(rule, "last_anchor_missing_log"):
                            rule.last_anchor_missing_log = 0.0
                        if now - rule.last_anchor_missing_log > 5.0:
                            rule.last_anchor_missing_log = now
                            self.log_signal.emit(f"[⚠️] Anchor rule for '{rule.name}' not found on screen. Skipping dependent rule.")
                        continue

                    # Determine Search Region with RESTRICTED REGION caching
                    crop_x1, crop_y1 = 0, 0
                    search_area = screen

                    # If region caching is active and target was previously found, restrict search to localized region
                    if rule.last_matched_region:
                        rx, ry, rw, rh = rule.last_matched_region
                        # Pad region slightly
                        pad_cached = 40
                        crop_x1 = max(0, rx - pad_cached)
                        crop_y1 = max(0, ry - pad_cached)
                        crop_x2 = min(screen_w, rx + rw + pad_cached)
                        crop_y2 = min(screen_h, ry + rh + pad_cached)
                        if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                            search_area = screen[crop_y1:crop_y2, crop_x1:crop_x2]
                    else:
                        # Fallback to standard designated regions
                        if rule.search_region == "Active Window Only":
                            title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()

                            # Calibrate client size changes
                            if rule.window_client_w and rule.window_client_h:
                                size_diff_pct = abs(ww - rule.window_client_w) / rule.window_client_w
                                if size_diff_pct > 0.05:
                                    self.log_signal.emit(
                                        f"[⚠️] Calibration Alert: Target window size changed by {size_diff_pct*100:.1f}%. "
                                        f"Scaling stored offsets dynamically to align."
                                    )
                                    scale_ratio = ww / rule.window_client_w
                                    dx = int(dx * scale_ratio)
                                    dy = int(dy * scale_ratio)

                            if "Headless" not in title:
                                crop_x1 = max(0, wx)
                                crop_y1 = max(0, wy)
                                crop_x2 = min(screen_w, wx + ww)
                                crop_y2 = min(screen_h, wy + wh)
                                if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                                    search_area = screen[crop_y1:crop_y2, crop_x1:crop_x2]
                                else:
                                    continue

                        elif rule.search_region == "Trained Region Only":
                            if rule.train_x is not None and rule.train_y is not None:
                                tx = rule.train_x + dx
                                ty = rule.train_y + dy
                                tw = rule.train_w
                                th = rule.train_h

                                pad = 30
                                crop_x1 = max(0, tx - pad)
                                crop_y1 = max(0, ty - pad)
                                crop_x2 = min(screen_w, tx + tw + pad)
                                crop_y2 = min(screen_h, ty + th + pad)
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

                        # Implement up to 3 retries with a 0.2s delay for target matching
                        matches = []
                        for attempt in range(3):
                            if attempt > 0:
                                time.sleep(0.2)
                                latest_screen = self.capture_engine.capture_full_screen()
                                if rule.search_region == "Active Window Only":
                                    title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()
                                    if "Headless" not in title:
                                        crop_x1 = max(0, wx)
                                        crop_y1 = max(0, wy)
                                        crop_x2 = min(latest_screen.shape[1], wx + ww)
                                        crop_y2 = min(latest_screen.shape[0], wy + wh)
                                        if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                                            search_area = latest_screen[crop_y1:crop_y2, crop_x1:crop_x2]
                                else:
                                    search_area = latest_screen

                            raw_matches = MatchEngine.match_template_multi(search_area, template, threshold=rule.threshold, use_edges=rule.use_edges)

                            # Similar UI Disambiguation: choose candidate with highest composite edges+colors similarity score
                            if raw_matches:
                                best_match = MatchEngine.disambiguate_candidates(search_area, template, raw_matches)
                                if best_match:
                                    matches = [best_match]
                                    break

                        if len(matches) == 1:
                            cx, cy, conf = matches[0]
                            best_x = cx + crop_x1
                            best_y = cy + crop_y1

                            th, tw = template.shape[:2]

                            # Store/Cache Restricted Match Region
                            with self.lock:
                                rule.last_matched_region = (best_x - tw//2, best_y - th//2, tw, th)

                            # Calculate calibration-based actual click point
                            top_left_x = best_x - tw // 2
                            top_left_y = best_y - th // 2

                            click_offset_x = rule.click_offset_x if rule.click_offset_x is not None else (tw // 2)
                            click_offset_y = rule.click_offset_y if rule.click_offset_y is not None else (th // 2)

                            # Shift click point relative to matching top-left + custom calibration offsets + DPI scaling adjustments + calibration corrections
                            actual_click_x = int((top_left_x + click_offset_x + dx) / current_dpi) + int(rule.calibration_correction_x)
                            actual_click_y = int((top_left_y + click_offset_y + dy) / current_dpi) + int(rule.calibration_correction_y)

                            # Phase 1: Debug Overlay & Calibration metadata
                            meta_text = (
                                f"RULE NAME           : {rule.name}\n"
                                f"TEMPLATE SIZE       : {tw}x{th}\n"
                                f"DETECTED TOP-LEFT   : [{top_left_x}, {top_left_y}]\n"
                                f"CLICK OFFSET        : +{click_offset_x}, +{click_offset_y}\n"
                                f"FINAL CLICK COORDS  : [{actual_click_x}, {actual_click_y}]\n"
                                f"SCREEN RESOLUTION   : {screen_w}x{screen_h}\n"
                                f"SYSTEM DPI SCALE    : {current_dpi}x\n"
                                f"CONFIDENCE SCORE    : {conf*100:.1f}%\n"
                                f"STATUS              : Visualizing Calibration..."
                            )
                            self.debug_overlay_signal.emit(
                                [(top_left_x, top_left_y, tw, th)],
                                (int(actual_click_x * current_dpi), int(actual_click_y * current_dpi)),
                                meta_text
                            )
                            # Pause 1 second before clicking to inspect calibration
                            time.sleep(1.0)

                            # Phase 6: Multi-Stage Pre-Click verification
                            verify_passed = MatchEngine.verify_pixels(
                                screen, template,
                                int(actual_click_x * current_dpi), int(actual_click_y * current_dpi),
                                top_left_x, top_left_y
                            )
                            if not verify_passed:
                                with self.lock:
                                    rule.failures_count += 1
                                self.log_signal.emit(
                                    f"[🚨] Verification Failed: Expected pixel signature around click coordinates modified. Aborting sequence."
                                )
                                continue

                            # Capture pixel snippet around click point before click for verification
                            snippet_before = self.capture_engine.capture_region(
                                max(0, int(actual_click_x * current_dpi) - 10),
                                max(0, int(actual_click_y * current_dpi) - 10),
                                20, 20
                            )

                            # Trigger matches
                            with self.lock:
                                rule.last_triggered = now
                                rule.matches_count += 1

                            # Update real-time Sidebar Debug Panel via signal
                            exec_dur = int((time.time() - start_time_cycle) * 1000)
                            self.live_debug_signal.emit(
                                rule.id_str, "🟢 Matched & Executing", f"{conf*100:.1f}%",
                                f"({actual_click_x}, {actual_click_y})", rule.search_region, str(exec_dur)
                            )

                            self.log_signal.emit(
                                f"[+] Match Success: '{rule.name}' verified with {conf*100:.1f}% confidence."
                            )

                            # Process steps
                            for i, step in enumerate(rule.click_steps):
                                step_action = step["action"]
                                step_x = actual_click_x + step["offset_x"]
                                step_y = actual_click_y + step["offset_y"]
                                step_delay = step["delay"]

                                self.log_signal.emit(
                                    f"  -> Step #{i+1}: Clicking '{step_action}' at [{step_x}, {step_y}] "
                                    f"DPI corrected. Delay: {step_delay}s"
                                )
                                self.click_signal.emit(step_x, step_y, step_action)
                                with self.lock:
                                    rule.clicks_count += 1
                                time.sleep(step_delay)

                            # Phase 8: Click Verification
                            time.sleep(0.1) # brief wait for UI to update
                            snippet_after = self.capture_engine.capture_region(
                                max(0, int(actual_click_x * current_dpi) - 10),
                                max(0, int(actual_click_y * current_dpi) - 10),
                                20, 20
                            )

                            # Compare snippets
                            if snippet_before.shape == snippet_after.shape:
                                diff = cv2.absdiff(snippet_before, snippet_after)
                                if np.mean(diff) < 2.0: # content completely unchanged
                                    self.log_signal.emit("[⚠️] Click Verification Warning: UI state unchanged. Retrying once...")
                                    # Retry click once
                                    self.click_signal.emit(actual_click_x, actual_click_y, "Left Click")
                                    time.sleep(0.3)
                                    snippet_after_retry = self.capture_engine.capture_region(
                                        max(0, int(actual_click_x * current_dpi) - 10),
                                        max(0, int(actual_click_y * current_dpi) - 10),
                                        20, 20
                                    )
                                    if np.mean(cv2.absdiff(snippet_before, snippet_after_retry)) < 2.0:
                                        self.log_signal.emit("[🚨] Click ineffective. Mouse action failed to mutate UI.")
                                        with self.lock:
                                            rule.failures_count += 1

                            # Phase 10: Production Logging
                            self.log_signal.emit(
                                f"LOG: Name: {rule.name} | Conf: {conf*100:.1f}% | Rect: [{top_left_x},{top_left_y} {tw}x{th}] | "
                                f"Offset: +{click_offset_x},+{click_offset_y} | Click Spot: [{actual_click_x},{actual_click_y}] | "
                                f"Screen Res: {screen_w}x{screen_h} | DPI Scale: {current_dpi}x | Verify: Passed | "
                                f"Time: {time.time() - start_time_cycle:.3f}s"
                            )
                            break
                        else:
                            # Hard failure: Target not found even after retries (reset region restriction cache)
                            with self.lock:
                                rule.last_matched_region = None
                                rule.failures_count += 1
                            if not hasattr(rule, "last_mismatch_log"):
                                rule.last_mismatch_log = 0.0
                            if now - rule.last_mismatch_log > 3.0:
                                rule.last_mismatch_log = now
                                self.log_signal.emit(
                                    f"[*] Scan: Target '{rule.name}' not found after retries. Resetting restricted region."
                                )

                    # OCR Text Match Trigger
                    elif rule.trigger_type == "OCR Text Match":
                        # Implement up to 3 retries with 0.2s delay for OCR text matching
                        match = None
                        for attempt in range(3):
                            if attempt > 0:
                                time.sleep(0.2)
                                latest_screen = self.capture_engine.capture_full_screen()
                                if rule.search_region == "Active Window Only":
                                    title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()
                                    if "Headless" not in title:
                                        crop_x1 = max(0, wx)
                                        crop_y1 = max(0, wy)
                                        crop_x2 = min(latest_screen.shape[1], wx + ww)
                                        crop_y2 = min(latest_screen.shape[0], wy + wh)
                                        if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                                            search_area = latest_screen[crop_y1:crop_y2, crop_x1:crop_x2]
                                else:
                                    search_area = latest_screen

                            match = MatchEngine.match_text_ocr(search_area, rule.name)
                            if match:
                                break

                        if match:
                            cx, cy, conf = match
                            best_x = cx + crop_x1
                            best_y = cy + crop_y1

                            # Highlight estimated OCR target region (draw a generic 100x30 box or similar)
                            self.highlight_signal.emit([(best_x - 50, best_y - 15, 100, 30)])

                            with self.lock:
                                rule.last_triggered = now
                                rule.matches_count += 1

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
                                with self.lock:
                                    rule.clicks_count += 1
                                time.sleep(step_delay)
                            break
                        else:
                            # Hard failure: Target not found even after retries
                            with self.lock:
                                rule.failures_count += 1

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
                                with self.lock:
                                    rule.failures_count += 1
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
                                rule.matches_count += 1

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
                                with self.lock:
                                    rule.clicks_count += 1
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
                                rule.matches_count += 1

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
                                with self.lock:
                                    rule.clicks_count += 1
                                time.sleep(step_delay)
                            break

                # Delay between scans (dynamically computed from performance FPS limit settings)
                time.sleep(max(0.01, 1.0 / self.fps_limit))

            except Exception as e:
                self.log_signal.emit(f"[!] Error in capture loop: {e}")
                time.sleep(0.5)

    def stop(self):
        self.running = False


from ui import CalibrationWizard, DebugOverlay

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
        self.debug_overlay = DebugOverlay()

        # Wire up user-facing toolbar buttons
        self.dashboard.calibrate_btn.clicked.connect(self.launch_calibration_wizard)

        # Initialize background monitor worker thread
        self.monitor_thread = MonitoringWorker(self.capture_engine, self.rules, self.lock)

        # Initialize Click & Hotkey engine
        self.click_engine = ClickEngine()

        # Setup GUI signal connections
        self.connect_signals()

    def launch_calibration_wizard(self):
        wizard = CalibrationWizard(self.dashboard)
        wizard.calibration_complete.connect(self.store_calibration_factors)
        wizard.exec()

    @Slot(float, float)
    def store_calibration_factors(self, correction_x: float, correction_y: float):
        # Update corrections across all active visual rules
        with self.lock:
            for rule in self.rules:
                rule.calibration_correction_x = correction_x
                rule.calibration_correction_y = correction_y
        self.dashboard.append_log(f"[⚙️] Calibration complete! Computed scale correction factors: X: {correction_x}x, Y: {correction_y}x")

    def connect_signals(self):
        # UI Button actions
        self.dashboard.start_btn.clicked.connect(self.start_monitoring)
        self.dashboard.stop_btn.clicked.connect(self.stop_monitoring)
        self.dashboard.teach_btn.clicked.connect(self.trigger_teach)
        self.dashboard.teach_cursor_btn.clicked.connect(self.trigger_teach_cursor)
        self.dashboard.clear_logs_btn.clicked.connect(self.dashboard.log_output.clear)

        # Connect modular TemplateManager button triggers
        self.dashboard.template_manager.delete_btn.clicked.connect(self.handle_manager_delete)
        self.dashboard.template_manager.replace_btn.clicked.connect(self.handle_manager_replace)

        # Connect modular Settings saved trigger
        self.dashboard.settings_page.settings_saved.connect(self.handle_settings_saved)

        # Sync table row selection to populate Sidebar Debug Panel details
        self.dashboard.rules_table.itemSelectionChanged.connect(self.sync_debugger_panel)

        # Teach overlay capture triggers
        self.teach_overlay.region_selected.connect(self.handle_region_selected)

        # Monitor thread signals
        self.monitor_thread.log_signal.connect(self.dashboard.append_log)
        self.monitor_thread.click_signal.connect(self.perform_macro_click)
        self.monitor_thread.highlight_signal.connect(self.highlight_overlay.highlight_matches)
        self.monitor_thread.debug_overlay_signal.connect(self.debug_overlay.show_debug_info)
        self.monitor_thread.live_debug_signal.connect(self.handle_live_debug_update)

    @Slot(str, str, str, str, str, str)
    def handle_live_debug_update(self, rule_id, state, conf, click_coords, region, execution_time):
        row = self.dashboard.rules_table.currentRow()
        if row >= 0:
            with self.lock:
                if row < len(self.rules) and self.rules[row].id_str == rule_id:
                    self.dashboard.debug_panel.update_debug_view(
                        self.rules[row].template_path, state, conf, click_coords, region, execution_time
                    )

    def handle_manager_delete(self):
        item = self.dashboard.template_manager.list_widget.currentItem()
        if item:
            filename = item.text()
            path = os.path.join("targets", filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                    self.dashboard.append_log(f"[🗑️] Template Asset Deleted: {filename}")
                except Exception as e:
                    self.dashboard.append_log(f"[!] Warning: Could not delete template asset file: {e}")
            self.dashboard.template_manager.refresh_templates()

    def handle_manager_replace(self):
        item = self.dashboard.template_manager.list_widget.currentItem()
        if item:
            self.dashboard.append_log(f"[*] Re-triggering Teach Mode to replace visual asset: {item.text()}")
            self.trigger_teach()

    def handle_settings_saved(self):
        fps = self.dashboard.settings_page.fps_combo.currentText()
        delay = self.dashboard.settings_page.click_delay_input.text()
        conf = self.dashboard.settings_page.conf_combo.currentText()

        try:
            self.monitor_thread.fps_limit = float(fps)
            self.monitor_thread.click_synthesizer_delay = float(delay)
        except ValueError:
            pass

        self.dashboard.append_log(f"[⚙️] Application Settings Applied: FPS={fps}, Click Delay={delay}s, Default Confidence={conf}")

    def sync_debugger_panel(self):
        row = self.dashboard.rules_table.currentRow()
        if row >= 0:
            with self.lock:
                if row < len(self.rules):
                    rule = self.rules[row]
                    state_str = "🟢 Active Scanning" if rule.active else "🟡 Paused / Cooldown"
                    self.dashboard.debug_panel.update_debug_view(
                        rule.template_path,
                        state_str,
                        f"{rule.threshold*100:.0f}",
                        f"({rule.abs_x}, {rule.abs_y})" if rule.abs_x is not None else "Visual Target",
                        rule.search_region,
                        "120" # mock execution duration ms
                    )

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

        # Fetch active window client area size during teach coordinates
        _, _, _, win_w, win_h = self.capture_engine.get_active_window_rect()

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
                    abs_x=dialog.abs_x,
                    abs_y=dialog.abs_y,
                    window_title=dialog.window_title,
                    window_offset_x=dialog.window_offset_x,
                    window_offset_y=dialog.window_offset_y,
                    search_region=dialog.region_combo.currentText(),
                    anchor_rule_id=anchor_rule_id,
                    window_client_w=win_w,
                    window_client_h=win_h
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

        # Store cropped screenshot target first so SaveTargetDialog can load it for clicking calibration point
        rule_id = f"rule_{int(time.time())}"
        filepath = os.path.join("targets", f"{rule_id}.png")
        try:
            self.capture_engine.save_template(x, y, w, h, filepath)
        except Exception as e:
            self.dashboard.append_log(f"[!] Failed to save cropped template before preview: {e}")

        # Fetch active window client area size during teach crop
        _, _, _, win_w, win_h = self.capture_engine.get_active_window_rect()

        # Pop save dialog pre-populated with template_path
        dialog = SaveTargetDialog(self.dashboard, rules_snapshot=rules_snapshot, template_path=filepath)
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

            # Extract anchor rule ID if selected
            anchor_rule_id = None
            if dialog.anchor_select_combo.currentIndex() > 0:
                anchor_rule_id = dialog.anchor_select_combo.currentData()

            try:
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
                    abs_x=dialog.abs_x,
                    abs_y=dialog.abs_y,
                    window_title=dialog.window_title,
                    window_offset_x=dialog.window_offset_x,
                    window_offset_y=dialog.window_offset_y,
                    search_region=dialog.region_combo.currentText(),
                    anchor_rule_id=anchor_rule_id,
                    train_x=x,
                    train_y=y,
                    train_w=w,
                    train_h=h,
                    click_offset_x=dialog.click_offset_x,
                    click_offset_y=dialog.click_offset_y,
                    window_client_w=win_w,
                    window_client_h=win_h
                )
                with self.lock:
                    self.rules.append(new_rule)

                self.refresh_rules_table()
                self.dashboard.template_manager.refresh_templates()
                self.dashboard.append_log(f"[✓] Saved new target rule: '{name}' template saved to {filepath}")
            except Exception as e:
                self.dashboard.append_log(f"[!] Failed to save template: {e}")

    def refresh_rules_table(self):
        # Safely read rules snapshot under lock for UI refresh
        rules_snapshot = []
        with self.lock:
            rules_snapshot = list(self.rules)

        # Update Statistics Panel in real-time
        rules_count = len(rules_snapshot)
        running_count = sum(1 for r in rules_snapshot if r.active)
        paused_count = sum(1 for r in rules_snapshot if not r.active)
        failed_count = sum(1 for r in rules_snapshot if r.failures_count > 0)
        clicks_today = sum(r.clicks_count for r in rules_snapshot)
        matches_today = sum(r.matches_count for r in rules_snapshot)
        self.dashboard.stats_panel.update_statistics(
            rules_count, running_count, paused_count, failed_count, clicks_today, matches_today, clicks_today
        )

        self.dashboard.rules_table.setRowCount(len(rules_snapshot))
        for row, rule in enumerate(rules_snapshot):
            # Column 0: Active check box
            chk = QCheckBox()
            chk.setChecked(rule.active)

            # Setup safe status updater with lock
            def make_active_updater(target_rule):
                return lambda state: [setattr(target_rule, "active", state == Qt.Checked), self.refresh_rules_table()]

            chk.stateChanged.connect(make_active_updater(rule))
            self.dashboard.rules_table.setCellWidget(row, 0, chk)

            # Column 1: Rule Name
            self.dashboard.rules_table.setItem(row, 1, QTableWidgetItem(rule.name))

            # Column 2: Status Indicator (🟢 Running, 🟡 Paused, etc.)
            status_str = "🟢 Running" if rule.active else "🟡 Paused"
            if rule.failures_count > 0:
                status_str = "🔴 Error"
            self.dashboard.rules_table.setItem(row, 2, QTableWidgetItem(status_str))

            # Column 3: Trigger Type
            self.dashboard.rules_table.setItem(row, 3, QTableWidgetItem(rule.trigger_type))

            # Column 4: Search Region
            self.dashboard.rules_table.setItem(row, 4, QTableWidgetItem(rule.search_region))

            # Column 5: Last Match
            last_match_str = f"{rule.matches_count} matches" if rule.matches_count > 0 else "Never"
            self.dashboard.rules_table.setItem(row, 5, QTableWidgetItem(last_match_str))

            # Column 6: Last Click
            last_click_str = f"{rule.clicks_count} clicks" if rule.clicks_count > 0 else "Never"
            self.dashboard.rules_table.setItem(row, 6, QTableWidgetItem(last_click_str))

            # Column 7: Success Rate percentage
            success_pct = "100.0%"
            if rule.failures_count + rule.clicks_count > 0:
                rate = (rule.clicks_count / (rule.clicks_count + rule.failures_count)) * 100.0
                success_pct = f"{rate:.1f}%"
            self.dashboard.rules_table.setItem(row, 7, QTableWidgetItem(success_pct))

            # Column 8: Actions (🗑️ Delete)
            del_btn = QPushButton("🗑️ Delete")
            del_btn.setToolTip("Delete this rule")

            def make_rule_deleter(target_rule_id):
                return lambda: self.delete_rule(target_rule_id)

            del_btn.clicked.connect(make_rule_deleter(rule.id_str))
            self.dashboard.rules_table.setCellWidget(row, 8, del_btn)

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
        self.dashboard.template_manager.refresh_templates()

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
