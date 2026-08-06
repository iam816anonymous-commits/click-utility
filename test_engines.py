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

if __name__ == "__main__":
    unittest.main()
