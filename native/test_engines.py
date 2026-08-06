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

if __name__ == "__main__":
    unittest.main()
