import os
import cv2
import numpy as np
import threading
from typing import Tuple, Optional, List, Dict

class MatchEngine:
    """
    Template Matching engine powered by OpenCV (Sum of Squared Differences / Normalized Cross-Correlation)
    and stubs for OCR and pixel-color matching.
    Includes thread-safe template caching to avoid expensive disk I/O.
    """
    _template_cache: Dict[str, Tuple[float, np.ndarray]] = {}
    _cache_lock = threading.Lock()

    @classmethod
    def load_template(cls, template_path: str) -> Optional[np.ndarray]:
        """
        Loads and caches template_bgr image based on template_path.
        Checks file modification time (mtime) to invalidate the cache if the file changes.
        """
        if not template_path:
            return None

        try:
            mtime = os.path.getmtime(template_path)
        except OSError:
            # File doesn't exist or is inaccessible
            with cls._cache_lock:
                cls._template_cache.pop(template_path, None)
            return None

        with cls._cache_lock:
            cached = cls._template_cache.get(template_path)
            if cached is not None:
                cached_mtime, cached_img = cached
                if cached_mtime == mtime:
                    return cached_img

            # Load image from disk
            img = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if img is not None:
                cls._template_cache[template_path] = (mtime, img)
            else:
                cls._template_cache.pop(template_path, None)
            return img

    @staticmethod
    def match_template(
        screen_bgr: np.ndarray,
        template_bgr: np.ndarray,
        threshold: float = 0.85,
        use_edges: bool = False
    ) -> Optional[Tuple[int, int, float]]:
        """
        Searches for a template_bgr image within screen_bgr.
        Supports use_edges parameter using Canny Edge detection.
        """
        if template_bgr.shape[0] > screen_bgr.shape[0] or template_bgr.shape[1] > screen_bgr.shape[1]:
            return None

        if use_edges:
            scr_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
            tmp_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)

            scr_edges = cv2.Canny(scr_gray, 80, 150)
            tmp_edges = cv2.Canny(tmp_gray, 80, 150)

            result = cv2.matchTemplate(scr_edges, tmp_edges, cv2.TM_CCOEFF_NORMED)
        else:
            result = cv2.matchTemplate(screen_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)

        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template_bgr.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y, float(max_val)

        return None

    @staticmethod
    def non_max_suppression(boxes: np.ndarray, overlap_thresh: float = 0.5) -> list:
        """
        Applies Non-Maximum Suppression to filter overlapping template matching results.
        """
        if len(boxes) == 0:
            return []

        if boxes.dtype.kind == "i":
            boxes = boxes.astype("f")

        pick = []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        scores = boxes[:, 4]

        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(scores)[::-1]

        while len(idxs) > 0:
            last = idxs[0]
            pick.append(last)

            xx1 = np.maximum(x1[last], x1[idxs[1:]])
            yy1 = np.maximum(y1[last], y1[idxs[1:]])
            xx2 = np.minimum(x2[last], x2[idxs[1:]])
            yy2 = np.minimum(y2[last], y2[idxs[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)

            overlap = (w * h) / area[idxs[1:]]
            idxs = idxs[np.where(overlap <= overlap_thresh)[0] + 1]

        return boxes[pick].tolist()

    @staticmethod
    def match_template_multi(
        screen_bgr: np.ndarray,
        template_bgr: np.ndarray,
        threshold: float = 0.85,
        max_matches: int = 10,
        use_edges: bool = False
    ) -> list[Tuple[int, int, float]]:
        """
        Finds multiple distinct non-overlapping occurrences of template_bgr in screen_bgr.
        """
        if template_bgr.shape[0] > screen_bgr.shape[0] or template_bgr.shape[1] > screen_bgr.shape[1]:
            return []

        if use_edges:
            scr_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
            tmp_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
            scr_edges = cv2.Canny(scr_gray, 80, 150)
            tmp_edges = cv2.Canny(tmp_gray, 80, 150)
            result = cv2.matchTemplate(scr_edges, tmp_edges, cv2.TM_CCOEFF_NORMED)
        else:
            result = cv2.matchTemplate(screen_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)

        loc = np.where(result >= threshold)
        h, w = template_bgr.shape[:2]

        boxes = []
        for pt in zip(*loc[::-1]):
            score = float(result[pt[1], pt[0]])
            boxes.append([pt[0], pt[1], pt[0] + w, pt[1] + h, score])

        if not boxes:
            return []

        suppressed_boxes = MatchEngine.non_max_suppression(np.array(boxes), overlap_thresh=0.3)

        matches = []
        for box in suppressed_boxes[:max_matches]:
            x1, y1, x2, y2, score = box
            center_x = int(x1 + w // 2)
            center_y = int(y1 + h // 2)
            matches.append((center_x, center_y, float(score)))

        return matches

    @staticmethod
    def disambiguate_candidates(
        screen_bgr: np.ndarray,
        template_bgr: np.ndarray,
        candidates: list[Tuple[int, int, float]]
    ) -> Optional[Tuple[int, int, float]]:
        """
        Performs multi-stage candidate scoring over visual candidates using:
        1. Template confidence
        2. Edge similarity (Canny NCC)
        3. Color histogram similarity (compareHist over 3D BGR histograms)
        """
        if not candidates:
            return None

        th, tw = template_bgr.shape[:2]
        tmp_hist = cv2.calcHist([template_bgr], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(tmp_hist, tmp_hist)

        tmp_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        tmp_edges = cv2.Canny(tmp_gray, 80, 150)

        best_candidate = None
        best_composite_score = -1.0

        for (cx, cy, temp_conf) in candidates:
            crop_x1 = max(0, cx - tw // 2)
            crop_y1 = max(0, cy - th // 2)
            crop_x2 = min(screen_bgr.shape[1], crop_x1 + tw)
            crop_y2 = min(screen_bgr.shape[0], crop_y1 + th)

            cand_crop = screen_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
            if cand_crop.shape[0] != th or cand_crop.shape[1] != tw:
                cand_crop = cv2.resize(cand_crop, (tw, th))

            cand_gray = cv2.cvtColor(cand_crop, cv2.COLOR_BGR2GRAY)
            cand_edges = cv2.Canny(cand_gray, 80, 150)
            edge_res = cv2.matchTemplate(cand_edges, tmp_edges, cv2.TM_CCOEFF_NORMED)
            _, edge_score, _, _ = cv2.minMaxLoc(edge_res)

            cand_hist = cv2.calcHist([cand_crop], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            cv2.normalize(cand_hist, cand_hist)
            hist_score = cv2.compareHist(tmp_hist, cand_hist, cv2.HISTCMP_CORREL)

            edge_score = max(0.0, float(edge_score))
            hist_score = max(0.0, float(hist_score))

            composite_score = (temp_conf * 0.34) + (edge_score * 0.33) + (hist_score * 0.33)

            if composite_score > best_composite_score:
                best_composite_score = composite_score
                best_candidate = (cx, cy, float(best_composite_score))

        return best_candidate

    @staticmethod
    def verify_pixels(
        current_screen: np.ndarray,
        original_template: np.ndarray,
        click_x: int,
        click_y: int,
        top_left_x: int,
        top_left_y: int,
        threshold: float = 0.80
    ) -> bool:
        """
        Structural template check on snippet.
        """
        th, tw = original_template.shape[:2]
        offset_x = click_x - top_left_x
        offset_y = click_y - top_left_y

        if offset_x < 0 or offset_y < 0 or offset_x >= tw or offset_y >= th:
            return False

        r = 10
        x1_tmp = max(0, offset_x - r)
        y1_tmp = max(0, offset_y - r)
        x2_tmp = min(tw, offset_x + r)
        y2_tmp = min(th, offset_y + r)

        original_snippet = original_template[y1_tmp:y2_tmp, x1_tmp:x2_tmp]

        x1_scr = max(0, click_x - r)
        y1_scr = max(0, click_y - r)
        x2_scr = min(current_screen.shape[1], click_x + r)
        y2_scr = min(current_screen.shape[0], click_y + r)

        current_snippet = current_screen[y1_scr:y2_scr, x1_scr:x2_scr]

        if original_snippet.size == 0 or current_snippet.size == 0:
            return False

        if original_snippet.shape != current_snippet.shape:
            original_snippet = cv2.resize(original_snippet, (current_snippet.shape[1], current_snippet.shape[0]))

        res = cv2.matchTemplate(current_snippet, original_snippet, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        return max_val >= threshold
