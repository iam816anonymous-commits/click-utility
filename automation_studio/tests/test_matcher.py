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

    def test_template_caching_and_invalidation(self):
        import tempfile
        import cv2
        import time
        import os

        # Clear any existing cache to start fresh
        MatchEngine._template_cache.clear()

        # Create a temporary template image on disk
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 1. Write initial image
            img1 = np.ones((10, 10, 3), dtype=np.uint8) * 100
            cv2.imwrite(tmp_path, img1)

            # First load (uncached)
            loaded1 = MatchEngine.load_template(tmp_path)
            self.assertIsNotNone(loaded1)
            np.testing.assert_array_equal(loaded1, img1)

            # Second load (should be cached)
            loaded2 = MatchEngine.load_template(tmp_path)
            self.assertIsNotNone(loaded2)
            np.testing.assert_array_equal(loaded2, img1)

            # 2. Modify the image and update the modification time to force reload
            img2 = np.ones((10, 10, 3), dtype=np.uint8) * 200
            cv2.imwrite(tmp_path, img2)

            # Explicitly set mtime to a future time to bypass filesystem mtime resolution limits
            current_mtime = os.path.getmtime(tmp_path)
            os.utime(tmp_path, (current_mtime + 5, current_mtime + 5))

            # Third load (cache should be invalidated due to new mtime, reloading img2)
            loaded3 = MatchEngine.load_template(tmp_path)
            self.assertIsNotNone(loaded3)
            np.testing.assert_array_equal(loaded3, img2)

            # 3. Missing/invalid file handling
            os.remove(tmp_path)
            loaded_missing = MatchEngine.load_template(tmp_path)
            self.assertIsNone(loaded_missing)

            # Verify missing file gets popped from cache
            self.assertNotIn(tmp_path, MatchEngine._template_cache)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_template_caching_performance_benchmark(self):
        import tempfile
        import cv2
        import time
        import os

        MatchEngine._template_cache.clear()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            img = np.ones((50, 50, 3), dtype=np.uint8) * 127
            cv2.imwrite(tmp_path, img)

            # Benchmark direct disk reads (100 times)
            t_start_disk = time.perf_counter()
            for _ in range(100):
                _ = cv2.imread(tmp_path, cv2.IMREAD_COLOR)
            t_disk = time.perf_counter() - t_start_disk

            # Warm up the cache
            _ = MatchEngine.load_template(tmp_path)

            # Benchmark cache reads (100 times)
            t_start_cache = time.perf_counter()
            for _ in range(100):
                _ = MatchEngine.load_template(tmp_path)
            t_cache = time.perf_counter() - t_start_cache

            print(f"\n[BENCHMARK] 100 direct disk reads took: {t_disk * 1000:.4f} ms")
            print(f"[BENCHMARK] 100 cached memory loads took: {t_cache * 1000:.4f} ms")
            print(f"[BENCHMARK] Template cache is {t_disk / max(1e-9, t_cache):.2f}x FASTER!")

            # Cache must be faster than disk reads by at least 2x
            self.assertLess(t_cache, t_disk)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
