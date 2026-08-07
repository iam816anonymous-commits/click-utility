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
        threshold: float = 0.85
    ) -> Optional[Tuple[int, int, float]]:
        """
        Searches for a template_bgr image within screen_bgr.
        Returns:
            Tuple of (center_x, center_y, confidence) if matched above threshold, else None.
        """
        if template_bgr.shape[0] > screen_bgr.shape[0] or template_bgr.shape[1] > screen_bgr.shape[1]:
            return None

        # TM_CCOEFF_NORMED gives a confidence score between -1 and 1 (1 is perfect match)
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
        max_matches: int = 10
    ) -> list[Tuple[int, int, float]]:
        """
        Finds multiple distinct non-overlapping occurrences of template_bgr in screen_bgr.
        Returns:
            List of Tuples of (center_x, center_y, confidence) sorted by confidence.
        """
        if template_bgr.shape[0] > screen_bgr.shape[0] or template_bgr.shape[1] > screen_bgr.shape[1]:
            return []

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
