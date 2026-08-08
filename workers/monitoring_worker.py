import os
import cv2
import numpy as np
import time
import threading
from PySide6.QtCore import QThread, Signal

# Import modular custom engines
from capture_engine import CaptureEngine
from match_engine import MatchEngine
from click_engine import ClickEngine
from coordinate_pipeline import SystemDpiCalibrator, CoordinateCalculationResult, CoordinateValidator

class MonitoringWorker(QThread):
    """
    Stage 1-9 Background worker thread implementing the strict deterministic pipeline.
    Handles logical vs physical scaling flawlessly.
    """
    log_signal = Signal(str)
    click_signal = Signal(int, int, str) # x, y, action
    highlight_signal = Signal(list) # list of Tuples (x, y, w, h)
    debug_overlay_signal = Signal(list, tuple, str) # rects, click_point, meta_text
    live_debug_signal = Signal(str, str, str, str, str, str) # rule_id, state, conf, click_coords, region, execution_time

    def __init__(self, capture_engine: CaptureEngine, rules: list, click_engine: ClickEngine, lock: threading.Lock):
        super().__init__()
        self.capture_engine = capture_engine
        self.rules = rules
        self.click_engine = click_engine
        self.lock = lock
        self.running = False
        self.move_only = False

        self.fps_limit = 10.0
        self.click_synthesizer_delay = 0.02

    def run(self):
        self.running = True
        self.log_signal.emit("[Worker] Background screen capture loop activated.")

        while self.running:
            try:
                start_time_cycle = time.time()

                # Stage 4: DPI Calibration - Load pre-cached parameters
                calibrator = SystemDpiCalibrator.get_instance()
                screen_w = calibrator.physical_w
                screen_h = calibrator.physical_h
                current_dpi = calibrator.dpi_scale

                # Capture full screen (Take snapshot before showing any overlays)
                screen = self.capture_engine.capture_full_screen()
                now = time.time()

                active_rules_snapshot = []
                with self.lock:
                    active_rules_snapshot = list(self.rules)

                for rule in active_rules_snapshot:
                    if not self.running:
                        break
                    if not rule.active:
                        continue

                    # Cooldown check
                    if now - rule.last_triggered < rule.cooldown:
                        continue

                    # Stage 1 & 2: Detection and Candidate Selection
                    t_detect_start = time.time()
                    crop_x1, crop_y1 = 0, 0
                    search_area = screen
                    window_rect = None

                    # Restricted regions check
                    if rule.search_region == "Active Window Only":
                        title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()
                        if "Headless" not in title:
                            window_rect = (wx, wy, ww, wh)
                            crop_x1 = max(0, wx)
                            crop_y1 = max(0, wy)
                            crop_x2 = min(screen.shape[1], wx + ww)
                            crop_y2 = min(screen.shape[0], wy + wh)
                            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                                search_area = screen[crop_y1:crop_y2, crop_x1:crop_x2]
                            else:
                                continue
                    elif rule.search_region == "Trained Region Only" and rule.train_x is not None:
                        pad = 30
                        crop_x1 = max(0, rule.train_x - pad)
                        crop_y1 = max(0, rule.train_y - pad)
                        crop_x2 = min(screen.shape[1], rule.train_x + rule.train_w + pad)
                        crop_y2 = min(screen.shape[0], rule.train_y + rule.train_h + pad)
                        if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                            search_area = screen[crop_y1:crop_y2, crop_x1:crop_x2]
                        else:
                            continue

                    # Identify Candidates
                    candidates = []

                    if rule.trigger_type == "Image Template Match":
                        if not os.path.exists(rule.template_path):
                            continue
                        template = cv2.imread(rule.template_path, cv2.IMREAD_COLOR)
                        if template is None:
                            continue

                        raw_matches = MatchEngine.match_template_multi(search_area, template, threshold=rule.threshold, use_edges=rule.use_edges)

                        # Disambiguate visual candidates
                        if raw_matches:
                            best_match = MatchEngine.disambiguate_candidates(search_area, template, raw_matches)
                            if best_match:
                                cx, cy, conf = best_match
                                global_cx = cx + crop_x1
                                global_cy = cy + crop_y1
                                candidates.append((global_cx, global_cy, conf, template.shape[1], template.shape[0]))

                    elif rule.trigger_type == "OCR Text Match":
                        ocr_res = MatchEngine.match_text_ocr(search_area, rule.name)
                        if ocr_res:
                            cx, cy, conf, bbox = ocr_res
                            global_cx = cx + crop_x1
                            global_cy = cy + crop_y1
                            candidates.append((global_cx, global_cy, conf, bbox["w"], bbox["h"]))

                    elif rule.trigger_type == "Absolute Cursor Position":
                        if rule.abs_x is not None:
                            candidates.append((rule.abs_x, rule.abs_y, 1.0, 30, 30))

                    elif rule.trigger_type == "Window-Relative Position":
                        if rule.window_offset_x is not None:
                            title, wx, wy, ww, wh = self.capture_engine.get_active_window_rect()
                            global_cx = wx + rule.window_offset_x
                            global_cy = wy + rule.window_offset_y
                            candidates.append((global_cx, global_cy, 1.0, 30, 30))

                    if not candidates:
                        continue

                    global_cx, global_cy, match_conf, tw, th = candidates[0]
                    t_detect_end = time.time()
                    self.log_signal.emit(f"[Detection] Verified candidate for rule '{rule.name}' with {match_conf*100:.1f}% confidence.")

                    # Stage 3: Coordinate Calculation
                    t_coord_start = time.time()
                    top_left_x = global_cx - tw // 2
                    top_left_y = global_cy - th // 2

                    click_offset_x = rule.click_offset_x if rule.click_offset_x is not None else (tw // 2)
                    click_offset_y = rule.click_offset_y if rule.click_offset_y is not None else (th // 2)

                    # Physical coordinates on the MSS screenshot
                    calculated_click_x = top_left_x + click_offset_x
                    calculated_click_y = top_left_y + click_offset_y

                    # Logical mouse cursor coordinates for PyAutoGUI movements:
                    # Divide physical coordinates by current_dpi, and then apply Wizard custom calibration offsets!
                    logical_click_x = int(calculated_click_x / current_dpi) + int(rule.calibration_correction_x)
                    logical_click_y = int(calculated_click_y / current_dpi) + int(rule.calibration_correction_y)

                    coord_result = CoordinateCalculationResult(
                        top_left_x=top_left_x,
                        top_left_y=top_left_y,
                        template_w=tw,
                        template_h=th,
                        click_offset_x=click_offset_x,
                        click_offset_y=click_offset_y,
                        calculated_click_x=calculated_click_x,
                        calculated_click_y=calculated_click_y,
                        dpi_scale=current_dpi,
                        logical_click_x=logical_click_x,
                        logical_click_y=logical_click_y
                    )
                    t_coord_end = time.time()

                    # Stage 5: Coordinate Validation
                    t_val_start = time.time()
                    valid, reasons = CoordinateValidator.validate(coord_result, window_rect, screen_w, screen_h)
                    t_val_end = time.time()

                    if not valid:
                        self.log_signal.emit(f"[🚨] [Validation] Coordinate Validation Failed for '{rule.name}': {', '.join(reasons)}")
                        with self.lock:
                            rule.failures_count += 1
                        continue

                    # Stage 6: Preview / Safe Mode
                    if self.move_only:
                        self.log_signal.emit(f"[Preview Mode] Safely moving to ({logical_click_x}, {logical_click_y}) for '{rule.name}'. No Click.")
                        meta_text = (
                            f"RULE NAME           : {rule.name}\n"
                            f"STAGE               : Stage 6 - Preview Mode (No Click)\n"
                            f"TEMPLATE SIZE       : {tw}x{th}\n"
                            f"CALCULATED CLICK    : ({logical_click_x}, {logical_click_y})\n"
                            f"PHYSICAL MATCH COORD: ({calculated_click_x}, {calculated_click_y})\n"
                            f"DPI SCALE           : {current_dpi}x\n"
                            f"STATUS              : Moving cursor, waiting 2 seconds..."
                        )
                        self.debug_overlay_signal.emit(
                            [(top_left_x, top_left_y, tw, th)],
                            (logical_click_x, logical_click_y),
                            meta_text
                        )
                        self.click_engine.safe_move_to(logical_click_x, logical_click_y)
                        time.sleep(2.0)
                        break

                    # Capture pixel snippet before click (using physical pixels space relative to MSS)
                    snippet_before = self.capture_engine.capture_region(
                        max(0, calculated_click_x - 10),
                        max(0, calculated_click_y - 10),
                        20, 20
                    )

                    # Stage 7: Click Engine Rewrite (with smart moveTo position verification in logical space)
                    t_click_start = time.time()
                    click_ok = False

                    for i, step in enumerate(rule.click_steps):
                        if not self.running:
                            break
                        step_x = logical_click_x + step["offset_x"]
                        step_y = logical_click_y + step["offset_y"]
                        step_delay = step["delay"]
                        step_action = step["action"]

                        self.log_signal.emit(f"-> [Execution] Clicking step #{i+1}: '{step_action}' at [{step_x}, {step_y}]")
                        click_ok = self.click_engine.trigger_click(step_x, step_y, step_action)
                        if click_ok:
                            with self.lock:
                                rule.clicks_count += 1
                        time.sleep(step_delay)
                    t_click_end = time.time()

                    # Stage 8: Post Click Verification (capture physical snippets relative to MSS)
                    t_post_start = time.time()
                    time.sleep(0.1) # wait for UI state change
                    snippet_after = self.capture_engine.capture_region(
                        max(0, calculated_click_x - 10),
                        max(0, calculated_click_y - 10),
                        20, 20
                    )

                    post_verify_passed = True
                    if snippet_before.shape == snippet_after.shape:
                        diff = cv2.absdiff(snippet_before, snippet_after)
                        if np.mean(diff) < 2.0: # UI completely unchanged
                            self.log_signal.emit("[Verification] Warning: click ineffective. Retrying once...")
                            click_ok = self.click_engine.trigger_click(logical_click_x, logical_click_y, "Left Click")
                            time.sleep(0.3)

                            snippet_after_retry = self.capture_engine.capture_region(
                                max(0, calculated_click_x - 10),
                                max(0, calculated_click_y - 10),
                                20, 20
                            )
                            if np.mean(cv2.absdiff(snippet_before, snippet_after_retry)) < 2.0:
                                self.log_signal.emit("[🚨] [Verification] Click ineffective after retry. Target UI unchanged.")
                                post_verify_passed = False
                                with self.lock:
                                    rule.failures_count += 1
                    t_post_end = time.time()

                    # Update statistics
                    with self.lock:
                        rule.last_triggered = now
                        rule.matches_count += 1

                    # Log execution timings
                    dur_detect = int((t_detect_end - t_detect_start) * 1000)
                    dur_coord = int((t_coord_end - t_coord_start) * 1000)
                    dur_val = int((t_val_end - t_val_start) * 1000)
                    dur_click = int((t_click_end - t_click_start) * 1000)
                    dur_post = int((t_post_end - t_post_start) * 1000)
                    total_dur = dur_detect + dur_coord + dur_val + dur_click + dur_post

                    self.live_debug_signal.emit(
                        rule.id_str, "🟢 Success" if post_verify_passed else "🔴 Failed", f"{match_conf*100:.1f}%",
                        f"({logical_click_x}, {logical_click_y})", rule.search_region, str(total_dur)
                    )

                    self.log_signal.emit(
                        f"LOG PIPELINE: Name: {rule.name}\n"
                        f"  -> Detection: {dur_detect}ms (Conf: {match_conf*100:.1f}%)\n"
                        f"  -> Coord Calc: {dur_coord}ms | Validation: {dur_val}ms\n"
                        f"  -> Click Exec: {dur_click}ms | Post-Click Verify: {dur_post}ms ({'Passed' if post_verify_passed else 'Failed'})\n"
                        f"  -> Total Pipeline Time: {total_dur}ms"
                    )
                    break

                # FPS Limit sleep
                time.sleep(max(0.01, 1.0 / self.fps_limit))

            except Exception as e:
                self.log_signal.emit(f"[!] Error in capture loop: {e}")
                time.sleep(0.5)

    def stop(self):
        self.running = False
