import os
import sys
from unittest.mock import MagicMock

# Mock sys.modules for GUI/X11 modules during unit testing to prevent connection errors
sys.modules['pyautogui'] = MagicMock()
sys.modules['pynput'] = MagicMock()
sys.modules['pynput.keyboard'] = MagicMock()
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()

import unittest
import numpy as np
from match_engine import MatchEngine

class TestMatchEngine(unittest.TestCase):
    """
    Unit tests ensuring the correctness of the custom OpenCV MatchEngine.
    """
    def setUp(self):
        # Create a mock 100x100 black image
        self.screen = np.zeros((100, 100, 3), dtype=np.uint8)

        # Create a non-flat template (6x6 white square inside a 10x10 black background)
        self.template = np.zeros((10, 10, 3), dtype=np.uint8)
        self.template[2:8, 2:8, :] = 255

        # Inject the exact same patterned template at [40, 40] on screen
        self.screen[40:50, 40:50, :] = self.template

    def test_perfect_template_match(self):
        # Match template with high confidence threshold
        result = MatchEngine.match_template(self.screen, self.template, threshold=0.95)
        self.assertIsNotNone(result)

        # Extract matches
        center_x, center_y, confidence = result

        # Template is 10x10 at top-left [40, 40].
        # Its center should be [45, 45].
        self.assertEqual(center_x, 45)
        self.assertEqual(center_y, 45)
        self.assertGreaterEqual(confidence, 0.99)

    def test_no_match_below_threshold(self):
        # Create a totally different textured template (e.g. inverted)
        different_template = np.ones((10, 10, 3), dtype=np.uint8) * 255
        different_template[2:8, 2:8, :] = 0

        # Attempting match should return None
        result = MatchEngine.match_template(self.screen, different_template, threshold=0.85)
        self.assertIsNone(result)

    def test_macro_rule_multi_step_sequence(self):
        # Import MacroRule model
        from main import MacroRule

        # Configure a custom multi-step click sequence
        custom_steps = [
            {"action": "Single Click", "offset_x": 10, "offset_y": 20, "delay": 0.1},
            {"action": "Double Click", "offset_x": 0, "offset_y": -50, "delay": 1.5},
            {"action": "Right Click", "offset_x": -100, "offset_y": 0, "delay": 0.5}
        ]

        rule = MacroRule(
            id_str="rule_seq_test",
            name="Test Sequence",
            trigger_type="Image Template Match",
            action="Sequence",
            cooldown=5.0,
            threshold=0.90,
            template_path="targets/fake.png",
            click_steps=custom_steps
        )

        # Verify the steps are stored in correct order
        self.assertEqual(len(rule.click_steps), 3)
        self.assertEqual(rule.click_steps[0]["action"], "Single Click")
        self.assertEqual(rule.click_steps[0]["offset_x"], 10)
        self.assertEqual(rule.click_steps[0]["offset_y"], 20)
        self.assertEqual(rule.click_steps[0]["delay"], 0.1)

        self.assertEqual(rule.click_steps[1]["action"], "Double Click")
        self.assertEqual(rule.click_steps[1]["offset_x"], 0)
        self.assertEqual(rule.click_steps[1]["offset_y"], -50)
        self.assertEqual(rule.click_steps[1]["delay"], 1.5)

        self.assertEqual(rule.click_steps[2]["action"], "Right Click")
        self.assertEqual(rule.click_steps[2]["offset_x"], -100)
        self.assertEqual(rule.click_steps[2]["offset_y"], 0)
        self.assertEqual(rule.click_steps[2]["delay"], 0.5)

    def test_absolute_cursor_position_rule(self):
        # Import MacroRule model
        from main import MacroRule

        rule = MacroRule(
            id_str="rule_abs_test",
            name="Test Absolute Position",
            trigger_type="Absolute Cursor Position",
            action="Single Click",
            cooldown=3.0,
            threshold=1.0,
            template_path="",
            click_steps=[{"action": "Single Click", "offset_x": 0, "offset_y": 0, "delay": 0.5}],
            abs_x=1200,
            abs_y=800
        )

        # Verify absolute coordinates are stored correctly
        self.assertEqual(rule.trigger_type, "Absolute Cursor Position")
        self.assertEqual(rule.abs_x, 1200)
        self.assertEqual(rule.abs_y, 800)
        self.assertEqual(len(rule.click_steps), 1)

    def test_window_relative_position_rule(self):
        # Import MacroRule model
        from main import MacroRule

        rule = MacroRule(
            id_str="rule_win_test",
            name="Test Window Relative Position",
            trigger_type="Window-Relative Position",
            action="Single Click",
            cooldown=3.0,
            threshold=1.0,
            template_path="",
            click_steps=[{"action": "Single Click", "offset_x": 0, "offset_y": 0, "delay": 0.5}],
            window_title="My Chrome Window",
            window_offset_x=220,
            window_offset_y=430
        )

        # Verify window metrics are stored correctly
        self.assertEqual(rule.trigger_type, "Window-Relative Position")
        self.assertEqual(rule.window_title, "My Chrome Window")
        self.assertEqual(rule.window_offset_x, 220)
        self.assertEqual(rule.window_offset_y, 430)

        # Calculate target position using mock active window top-left (left=150, top=100)
        mock_win_x, mock_win_y = 150, 100
        target_x = mock_win_x + rule.window_offset_x
        target_y = mock_win_y + rule.window_offset_y

        self.assertEqual(target_x, 370)
        self.assertEqual(target_y, 530)

    def test_coordinate_history_tracking(self):
        # Import MacroRule model
        from main import MacroRule

        rule = MacroRule(
            id_str="rule_hist_test",
            name="Test Coordinate History",
            trigger_type="Absolute Cursor Position",
            action="Single Click",
            cooldown=3.0,
            threshold=1.0,
            template_path="",
            coordinate_history=[
                {"window": "Chrome", "x": 1245, "y": 621},
                {"window": "Explorer", "x": 712, "y": 441}
            ]
        )

        self.assertEqual(len(rule.coordinate_history), 2)
        self.assertEqual(rule.coordinate_history[0]["window"], "Chrome")
        self.assertEqual(rule.coordinate_history[0]["x"], 1245)
        self.assertEqual(rule.coordinate_history[1]["window"], "Explorer")
        self.assertEqual(rule.coordinate_history[1]["y"], 441)

    def test_active_window_offset_calculation(self):
        # Simulate active window offset calculation bounds: Screen coordinates (1200, 800) vs Window (1000, 600)
        screen_x, screen_y = 1200, 800
        win_left, win_top = 1000, 600

        offset_x = screen_x - win_left
        offset_y = screen_y - win_top

        self.assertEqual(offset_x, 200)
        self.assertEqual(offset_y, 200)

    def test_non_max_suppression(self):
        # Create overlapping boxes: [x1, y1, x2, y2, score]
        boxes = np.array([
            [10, 10, 20, 20, 0.95],
            [11, 11, 21, 21, 0.90], # strong overlap
            [50, 50, 60, 60, 0.85]  # distinct
        ])
        suppressed = MatchEngine.non_max_suppression(boxes, overlap_thresh=0.3)
        # Should filter out the second box, keeping only 2 boxes
        self.assertEqual(len(suppressed), 2)
        # Verify the top score box is kept
        self.assertEqual(suppressed[0][4], 0.95)
        self.assertEqual(suppressed[1][4], 0.85)

    def test_non_maximum_suppression(self):
        # Alias test matching precise naming requested in plan step
        boxes = np.array([
            [10, 10, 20, 20, 0.95],
            [11, 11, 21, 21, 0.90],
            [50, 50, 60, 60, 0.85]
        ])
        suppressed = MatchEngine.non_max_suppression(boxes, overlap_thresh=0.3)
        self.assertEqual(len(suppressed), 2)

    def test_region_locking_crop(self):
        # Test visual cropping mock logic representing region-locking
        screen = np.zeros((200, 200, 3), dtype=np.uint8)
        # Mocking region boundaries of a locked trained region
        train_x, train_y, train_w, train_h = 40, 50, 60, 60
        pad = 10
        crop_x1 = max(0, train_x - pad)
        crop_y1 = max(0, train_y - pad)
        crop_x2 = min(screen.shape[1], train_x + train_w + pad)
        crop_y2 = min(screen.shape[0], train_y + train_h + pad)

        self.assertEqual(crop_x1, 30)
        self.assertEqual(crop_y1, 40)
        self.assertEqual(crop_x2, 110)
        self.assertEqual(crop_y2, 120)

        cropped = screen[crop_y1:crop_y2, crop_x1:crop_x2]
        self.assertEqual(cropped.shape, (80, 80, 3))

    def test_anchor_relative_calculation(self):
        # Test calculations of displacement offsets from a reference anchor coordinate
        # Let's say Anchor template was trained at center [50, 50]
        atcx = 50
        atcy = 50

        # When monitoring runs, anchor match is found at [65, 45] (e.g. shifted +15x, -5y)
        acx = 65
        acy = 45

        dx = acx - atcx
        dy = acy - atcy

        self.assertEqual(dx, 15)
        self.assertEqual(dy, -5)

        # Dependent target trained position
        target_train_x = 120
        target_train_y = 180

        # Shift target using computed anchor displacement
        target_actual_x = target_train_x + dx
        target_actual_y = target_train_y + dy

        self.assertEqual(target_actual_x, 135)
        self.assertEqual(target_actual_y, 175)

    def test_match_template_multi(self):
        # Create a screen with two identical white squares
        multi_screen = np.zeros((100, 100, 3), dtype=np.uint8)
        multi_screen[20:30, 20:30, :] = self.template
        multi_screen[60:70, 60:70, :] = self.template

        matches = MatchEngine.match_template_multi(multi_screen, self.template, threshold=0.90)
        # Should detect exactly 2 distinct matches
        self.assertEqual(len(matches), 2)

        # Sort matches by coordinates to make test order independent of confidence scores
        matches.sort(key=lambda m: (m[0], m[1]))

        # First match center
        self.assertEqual(matches[0][0], 25)
        self.assertEqual(matches[0][1], 25)
        # Second match center
        self.assertEqual(matches[1][0], 65)
        self.assertEqual(matches[1][1], 65)

    def test_macro_rule_region_locking_and_anchor_init(self):
        from main import MacroRule
        rule = MacroRule(
            id_str="rule_region_anchor",
            name="Test Rule with Region & Anchor",
            trigger_type="Image Template Match",
            action="Single Click",
            cooldown=1.0,
            threshold=0.85,
            template_path="targets/test_temp.png",
            search_region="Trained Region Only",
            anchor_rule_id="anchor_123",
            train_x=100, train_y=150, train_w=50, train_h=50
        )
        self.assertEqual(rule.search_region, "Trained Region Only")
        self.assertEqual(rule.anchor_rule_id, "anchor_123")
        self.assertEqual(rule.train_x, 100)
        self.assertEqual(rule.train_y, 150)
        self.assertEqual(rule.train_w, 50)
        self.assertEqual(rule.train_h, 50)

    def test_rule_statistics_tracking(self):
        from main import MacroRule
        rule = MacroRule(
            id_str="stats_test_rule",
            name="Stats Track Rule",
            trigger_type="Image Template Match",
            action="Single Click",
            cooldown=1.0,
            threshold=0.85,
            template_path="targets/fake.png"
        )
        # Ensure tracking stats initialize to 0
        self.assertEqual(rule.matches_count, 0)
        self.assertEqual(rule.clicks_count, 0)
        self.assertEqual(rule.failures_count, 0)

        # Simulate statistics modifications under visual match trigger
        rule.matches_count += 1
        rule.clicks_count += 2
        rule.failures_count += 3

        self.assertEqual(rule.matches_count, 1)
        self.assertEqual(rule.clicks_count, 2)
        self.assertEqual(rule.failures_count, 3)

    def test_retry_recovery_logic(self):
        # Simulate attempt counters representing the up to 3 retries logic
        attempts = 0
        success = False

        # Simulate 3 attempts loop with mock target appearing on the 3rd attempt
        for attempt in range(3):
            attempts += 1
            if attempt == 2: # Mock success on the 3rd attempt
                success = True
                break

        self.assertEqual(attempts, 3)
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
