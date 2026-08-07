import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any

class MatchEngine:
    """
    Template Matching engine powered by OpenCV (Sum of Squared Differences / Normalized Cross-Correlation)
    and stubs for OCR and pixel-color matching.
    """

    @staticmethod
    def match_template(
        screen_bgr: np.ndarray,
        template_bgr: np.ndarray,
        threshold: float = 0.85,
        use_edges: bool = False
    ) -> Optional[Tuple[int, int, float]]:
        """
        Searches for a template_bgr image within screen_bgr.
        Supports use_edges parameter using Canny Edge detection to reduce false-positive rates
        when matching similar UI elements with gray borders and white paddings.
        Returns:
            Tuple of (center_x, center_y, confidence) if matched above threshold, else None.
        """
        if template_bgr.shape[0] > screen_bgr.shape[0] or template_bgr.shape[1] > screen_bgr.shape[1]:
            return None

        if use_edges:
            # Convert screen and template to grayscale then apply Canny edge detector
            scr_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
            tmp_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)

            scr_edges = cv2.Canny(scr_gray, 80, 150)
            tmp_edges = cv2.Canny(tmp_gray, 80, 150)

            # Match edge images using Normalized Cross-Correlation
            result = cv2.matchTemplate(scr_edges, tmp_edges, cv2.TM_CCOEFF_NORMED)
        else:
            # Standard color template matching
            result = cv2.matchTemplate(screen_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)

        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template_bgr.shape[:2]
            # Center coordinate of the match
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y, float(max_val)

        return None

    @staticmethod
    def non_max_suppression(boxes: np.ndarray, overlap_thresh: float = 0.5) -> list:
        """
        Applies Non-Maximum Suppression to filter overlapping template matching results.
        boxes: np.ndarray of shape (N, 5) representing [x1, y1, x2, y2, score].
        """
        if len(boxes) == 0:
            return []

        # Convert coordinates to floats if they aren't
        if boxes.dtype.kind == "i":
            boxes = boxes.astype("f")

        pick = []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        scores = boxes[:, 4]

        # Compute area of boxes
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        # Sort by scores
        idxs = np.argsort(scores)[::-1]

        while len(idxs) > 0:
            last = idxs[0]
            pick.append(last)

            # Find largest coordinates
            xx1 = np.maximum(x1[last], x1[idxs[1:]])
            yy1 = np.maximum(y1[last], y1[idxs[1:]])
            xx2 = np.minimum(x2[last], x2[idxs[1:]])
            yy2 = np.minimum(y2[last], y2[idxs[1:]])

            # Compute width and height of overlap
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)

            # Compute ratio of overlap
            overlap = (w * h) / area[idxs[1:]]

            # Delete all indexes with overlap greater than overlap_thresh
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
        Supports use_edges parameter using Canny Edge detection to reduce false-positive rates
        when matching similar UI elements with gray borders and white paddings.
        Returns:
            List of Tuples of (center_x, center_y, confidence) sorted by confidence.
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

        # Find all local maxima locations above threshold
        loc = np.where(result >= threshold)
        h, w = template_bgr.shape[:2]

        boxes = []
        for pt in zip(*loc[::-1]): # x, y on screen
            score = float(result[pt[1], pt[0]])
            # Bounding box: [x1, y1, x2, y2, score]
            boxes.append([pt[0], pt[1], pt[0] + w, pt[1] + h, score])

        if not boxes:
            return []

        # Apply Non-Maximum Suppression to merge overlapping detections
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

        Chooses the highest combined composite score to guarantee distinct matching
        across visually identical shapes (like tab sidebars).
        """
        if not candidates:
            return None

        th, tw = template_bgr.shape[:2]

        # Compute template's color histogram as baseline
        tmp_hist = cv2.calcHist([template_bgr], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(tmp_hist, tmp_hist)

        # Compute template's edge image
        tmp_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        tmp_edges = cv2.Canny(tmp_gray, 80, 150)

        best_candidate = None
        best_composite_score = -1.0

        for (cx, cy, temp_conf) in candidates:
            # Crop actual matched region from screen
            crop_x1 = max(0, cx - tw // 2)
            crop_y1 = max(0, cy - th // 2)
            crop_x2 = min(screen_bgr.shape[1], crop_x1 + tw)
            crop_y2 = min(screen_bgr.shape[0], crop_y1 + th)

            cand_crop = screen_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
            if cand_crop.shape[0] != th or cand_crop.shape[1] != tw:
                # Pad/resize to ensure exact shape compatibility
                cand_crop = cv2.resize(cand_crop, (tw, th))

            # 1. Edge Similarity
            cand_gray = cv2.cvtColor(cand_crop, cv2.COLOR_BGR2GRAY)
            cand_edges = cv2.Canny(cand_gray, 80, 150)
            edge_res = cv2.matchTemplate(cand_edges, tmp_edges, cv2.TM_CCOEFF_NORMED)
            _, edge_score, _, _ = cv2.minMaxLoc(edge_res)

            # 2. Color Histogram Similarity
            cand_hist = cv2.calcHist([cand_crop], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            cv2.normalize(cand_hist, cand_hist)
            hist_score = cv2.compareHist(tmp_hist, cand_hist, cv2.HISTCMP_CORREL)

            # Normalize scores to [0, 1] range safely
            edge_score = max(0.0, float(edge_score))
            hist_score = max(0.0, float(hist_score))

            # Composite Scoring: equal weight of template match (34%), edge shape (33%), and color histograms (33%)
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
        Before clicking, captures a small 20x20 region around the click point on current screen
        and verifies if the visual content still aligns with the trained template at that offset.
        """
        th, tw = original_template.shape[:2]

        # Click offset relative to matched top-left
        offset_x = click_x - top_left_x
        offset_y = click_y - top_left_y

        # Verify range
        if offset_x < 0 or offset_y < 0 or offset_x >= tw or offset_y >= th:
            return False

        # Small 20x20 region bounds
        r = 10
        x1_tmp = max(0, offset_x - r)
        y1_tmp = max(0, offset_y - r)
        x2_tmp = min(tw, offset_x + r)
        y2_tmp = min(th, offset_y + r)

        original_snippet = original_template[y1_tmp:y2_tmp, x1_tmp:x2_tmp]

        # Retrieve same snippet relative to current matched screen coordinate
        x1_scr = max(0, click_x - r)
        y1_scr = max(0, click_y - r)
        x2_scr = min(current_screen.shape[1], click_x + r)
        y2_scr = min(current_screen.shape[0], click_y + r)

        current_snippet = current_screen[y1_scr:y2_scr, x1_scr:x2_scr]

        if original_snippet.size == 0 or current_snippet.size == 0:
            return False

        # Ensure identical sizing
        if original_snippet.shape != current_snippet.shape:
            original_snippet = cv2.resize(original_snippet, (current_snippet.shape[1], current_snippet.shape[0]))

        # Structural template check
        res = cv2.matchTemplate(current_snippet, original_snippet, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        return max_val >= threshold

    @staticmethod
    def match_text_ocr(
        screen_bgr: np.ndarray,
        target_text: str
    ) -> Optional[Tuple[int, int, float]]:
        """
        Integrates with the OCREngine to locate target text on the screen
        using pre-processed image OCR and case-insensitive matching.
        """
        from ocr_engine import OCREngine
        return OCREngine.match_text_on_screen(screen_bgr, target_text)
