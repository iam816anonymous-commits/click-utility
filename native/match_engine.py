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
    def match_text_ocr(
        screen_bgr: np.ndarray,
        target_text: str
    ) -> Optional[Tuple[int, int, float]]:
        """
        OCR matching stub. In production, this imports pytesseract or easyocr
        to perform optical character recognition on screen_bgr, parses text boxes,
        and matches target_text.
        """
        # Simulated OCR matching logic for demonstration and testing
        # Returns a mock center position if target_text matches a keyword
        print(f"[MatchEngine] Scanning screen for OCR text: '{target_text}'")
        return None
