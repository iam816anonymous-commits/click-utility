import cv2
import os
import numpy as np
from typing import Tuple, Optional, Dict, Any

class OCREngine:
    """
    Engine to recognize and locate text elements on screen using Tesseract OCR (via pytesseract).
    Incorporates advanced UI image pre-processing (Grayscale, CLAHE, Upscale, Denoise, Otsu)
    and case-insensitive fuzzy matching to guarantee high-reliability UI text recognition.
    """

    _tesseract_installed = None

    @classmethod
    def check_tesseract(cls) -> bool:
        if cls._tesseract_installed is not None:
            return cls._tesseract_installed
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            cls._tesseract_installed = True
        except Exception:
            cls._tesseract_installed = False
        return cls._tesseract_installed

    @classmethod
    def match_text_on_screen(
        cls,
        screen_bgr: np.ndarray,
        target_text: str
    ) -> Optional[Tuple[int, int, float, Dict[str, int]]]:
        """
        Locates target_text within screen_bgr using pytesseract OCR.
        Applies grayscaling, CLAHE, 2x upscaling, median denoising, and Otsu thresholding.

        Returns:
            Tuple of (center_x, center_y, confidence, bounding_box) if matched, else None.
            bounding_box is a dictionary: {"x": left, "y": top, "w": width, "h": height}
        """
        try:
            import pytesseract
        except ImportError:
            print("[OCR Engine] 'pytesseract' library is not installed.")
            return None

        if not cls.check_tesseract():
            print("[OCR Engine] Tesseract OCR binary is missing or not in PATH.")
            return None

        from pytesseract import Output

        try:
            # 1. UI Image Preprocessing
            gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)

            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray_clahe = clahe.apply(gray)

            # Upscale x2
            resized = cv2.resize(gray_clahe, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

            # Median blur denoising
            denoised = cv2.medianBlur(resized, 3)

            # Otsu's thresholding
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 2. Run OCR with word/layout info
            custom_config = r'--psm 11'
            data = pytesseract.image_to_data(thresh, output_type=Output.DICT, config=custom_config)

            n_boxes = len(data['text'])
            target_lower = target_text.strip().lower()

            for i in range(n_boxes):
                word = data['text'][i].strip()
                if not word:
                    continue

                # Case-insensitive substring matching
                if target_lower in word.lower() or word.lower() in target_lower:
                    # Upscaled coordinates
                    rx = data['left'][i]
                    ry = data['top'][i]
                    rw = data['width'][i]
                    rh = data['height'][i]

                    # Convert back to original coordinate space
                    orig_x = int(rx / 2.0)
                    orig_y = int(ry / 2.0)
                    orig_w = int(rw / 2.0)
                    orig_h = int(rh / 2.0)

                    center_x = orig_x + orig_w // 2
                    center_y = orig_y + orig_h // 2
                    conf = float(data['conf'][i]) / 100.0

                    bbox = {"x": orig_x, "y": orig_y, "w": orig_w, "h": orig_h}
                    print(f"[OCR Engine] Found match: '{word}' at center [{center_x}, {center_y}] with conf {conf:.2f}")
                    return center_x, center_y, conf, bbox

        except Exception as e:
            print(f"[OCR Engine] Error during OCR: {e}")

        return None
