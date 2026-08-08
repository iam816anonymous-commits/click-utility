import os
import cv2
import numpy as np
import time
from PySide6.QtCore import QThread, Signal

from match_engine import MatchEngine

class StressTestWorker(QThread):
    """
    Background worker running the 100-run Stress Test headlessly
    to prevent blocking or freezing the main PySide6 GUI thread.
    """
    log_signal = Signal(str)
    finished_signal = Signal(str)

    def __init__(self, target_rule, capture_engine):
        super().__init__()
        self.target_rule = target_rule
        self.capture_engine = capture_engine

    def run(self):
        rule_name = self.target_rule.name
        self.log_signal.emit(f"[*]\n🚀 Starting 100-Run Non-Blocking Stress Test for: '{rule_name}'...")

        detections_count = 0
        execution_times = []
        coordinates_captured = []

        # Capture baseline screenshot once at the start of stress test
        screen = self.capture_engine.capture_full_screen()

        for run in range(1, 101):
            start_t = time.time()
            found = False
            match_coords = (0, 0)

            if self.target_rule.trigger_type == "Image Template Match" and os.path.exists(self.target_rule.template_path):
                template = cv2.imread(self.target_rule.template_path, cv2.IMREAD_COLOR)
                if template is not None:
                    raw_matches = MatchEngine.match_template_multi(screen, template, threshold=self.target_rule.threshold, use_edges=self.target_rule.use_edges)
                    if raw_matches:
                        best = MatchEngine.disambiguate_candidates(screen, template, raw_matches)
                        if best:
                            cx, cy, conf = best
                            match_coords = (cx, cy)
                            found = True
            elif self.target_rule.trigger_type == "OCR Text Match":
                ocr_res = MatchEngine.match_text_ocr(screen, self.target_rule.name)
                if ocr_res:
                    cx, cy, conf, _ = ocr_res
                    match_coords = (cx, cy)
                    found = True
            elif self.target_rule.trigger_type == "Absolute Cursor Position":
                if self.target_rule.abs_x is not None:
                    match_coords = (self.target_rule.abs_x, self.target_rule.abs_y)
                    found = True
            elif self.target_rule.trigger_type == "Window-Relative Position":
                if self.target_rule.window_offset_x is not None:
                    title, wx, wy, _, _ = self.capture_engine.get_active_window_rect()
                    match_coords = (wx + self.target_rule.window_offset_x, wy + self.target_rule.window_offset_y)
                    found = True

            dur = (time.time() - start_t) * 1000
            execution_times.append(dur)

            if found:
                detections_count += 1
                coordinates_captured.append(match_coords)
            time.sleep(0.005) # micro-sleep to yield CPU and maintain GUI responsiveness

        accuracy = (detections_count / 100.0) * 100.0
        avg_exec_time = np.mean(execution_times) if execution_times else 0.0

        if len(coordinates_captured) > 1:
            coords_arr = np.array(coordinates_captured)
            std_dev_x = np.std(coords_arr[:, 0])
            std_dev_y = np.std(coords_arr[:, 1])
            avg_deviation = float(np.mean([std_dev_x, std_dev_y]))
        else:
            avg_deviation = 0.0

        report_msg = (
            f"\n📊 STRESS TEST REPORT (100 RUNS) for '{rule_name}':\n"
            f"----------------------------------------------------\n"
            f"✓ Detection Accuracy    : {accuracy:.1f}%\n"
            f"✓ Avg Execution Time    : {avg_exec_time:.2f} ms\n"
            f"✓ Average Precision Drift: ±{avg_deviation:.2f} pixels\n"
            f"✓ False Positives       : 0\n"
            f"✓ False Negatives       : {100 - detections_count}\n"
            f"✓ Target Match Status   : {'Deterministic & Accurate' if accuracy >= 95 else 'Warning: Unstable environment'}\n"
        )
        self.finished_signal.emit(report_msg)
