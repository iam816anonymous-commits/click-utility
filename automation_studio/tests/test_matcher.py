import unittest
import numpy as np
from automation_studio.matching.template_matcher import MatchEngine

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
        result = MatchEngine.match_template(self.screen, self.template, threshold=0.95)
        self.assertIsNotNone(result)

        center_x, center_y, confidence = result
        self.assertEqual(center_x, 45)
        self.assertEqual(center_y, 45)
        self.assertGreaterEqual(confidence, 0.99)

    def test_no_match_below_threshold(self):
        different_template = np.ones((10, 10, 3), dtype=np.uint8) * 255
        different_template[2:8, 2:8, :] = 0

        result = MatchEngine.match_template(self.screen, different_template, threshold=0.85)
        self.assertIsNone(result)

    def test_non_max_suppression(self):
        boxes = np.array([
            [10, 10, 20, 20, 0.95],
            [11, 11, 21, 21, 0.90], # strong overlap
            [50, 50, 60, 60, 0.85]  # distinct
        ])
        suppressed = MatchEngine.non_max_suppression(boxes, overlap_thresh=0.3)
        self.assertEqual(len(suppressed), 2)
        self.assertEqual(suppressed[0][4], 0.95)
        self.assertEqual(suppressed[1][4], 0.85)

    def test_match_template_multi(self):
        multi_screen = np.zeros((100, 100, 3), dtype=np.uint8)
        multi_screen[20:30, 20:30, :] = self.template
        multi_screen[60:70, 60:70, :] = self.template

        matches = MatchEngine.match_template_multi(multi_screen, self.template, threshold=0.90)
        self.assertEqual(len(matches), 2)

        matches.sort(key=lambda m: (m[0], m[1]))
        self.assertEqual(matches[0][0], 25)
        self.assertEqual(matches[0][1], 25)
        self.assertEqual(matches[1][0], 65)
        self.assertEqual(matches[1][1], 65)

    def test_multi_stage_candidate_disambiguation(self):
        candidates = [
            (25, 25, 0.98),
            (65, 65, 0.95)
        ]

        screen = np.zeros((100, 100, 3), dtype=np.uint8)
        screen[20:30, 20:30, :] = self.template
        screen[60:70, 60:70, :] = self.template

        best_candidate = MatchEngine.disambiguate_candidates(screen, self.template, candidates)
        self.assertIsNotNone(best_candidate)
        self.assertEqual(best_candidate[0], 25)
        self.assertEqual(best_candidate[1], 25)

    def test_is_safe_path(self):
        # 1. Valid paths inside base_dir should return True
        self.assertTrue(MatchEngine.is_safe_path("targets/rule_1.png", base_dir="targets"))
        self.assertTrue(MatchEngine.is_safe_path("targets/nested/rule_1.png", base_dir="targets"))

        # 2. Backtracking or external paths should return False (Path Traversal attempt)
        self.assertFalse(MatchEngine.is_safe_path("targets/../etc/passwd", base_dir="targets"))
        self.assertFalse(MatchEngine.is_safe_path("targets_evil/rule_1.png", base_dir="targets"))
        self.assertFalse(MatchEngine.is_safe_path("/etc/passwd", base_dir="targets"))
        self.assertFalse(MatchEngine.is_safe_path("rules.json", base_dir="targets"))

        # 3. Empty or None paths should return False
        self.assertFalse(MatchEngine.is_safe_path("", base_dir="targets"))
        self.assertFalse(MatchEngine.is_safe_path(None, base_dir="targets"))
