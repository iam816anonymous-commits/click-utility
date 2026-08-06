import cv2
import os
import numpy as np
from typing import Tuple, Optional

class OCREngine:
    """
    Engine to recognize and locate text elements on screen using Tesseract OCR (via pytesseract).
    Incorporates advanced UI image pre-processing (Grayscale, 2x Resize, Thresholding)
    and case-insensitive fuzzy matching to guarantee high-reliability UI text recognition.
    """

    _tesseract_installed = None

    @classmethod
    def check_tesseract(cls) -> bool:
        if cls._tesseract_installed is not None:
            return cls._tesseract_installed
        try:
            import pytesseract
            # Run a dummy check to verify tesseract executable is available in path
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
    ) -> Optional[Tuple[int, int, float]]:
        """
        Locates target_text within screen_bgr using pytesseract OCR.
        Applies grayscaling, 2x upscaling, and Otsu/binary thresholding to handle
        small fonts and anti-aliased UI text in dark/light modes.

        Returns:
            Tuple of (center_x, center_y, confidence) if matched, else None.
        """
        try:
            import pytesseract
        except ImportError:
            print("[OCR Engine] 'pytesseract' library is not installed. Run 'pip install pytesseract' first.")
            return None

        if not cls.check_tesseract():
            print("[OCR Engine] 'pytesseract' is imported, but the system Tesseract OCR binary is missing or not in PATH.")
            print("[OCR Engine] Please install tesseract-ocr (e.g. 'sudo apt-get install tesseract-ocr' or download for Windows).")
            return None

        from pytesseract import Output

        try:
            # 1. UI Image Preprocessing as recommended: Grayscale -> Resize 2x -> Threshold
            gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

            # Use Otsu thresholding or adaptive thresholding to separate text cleanly from dark backgrounds
            _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 2. Run OCR with detailed word-level layout information
            # psm 11 (Sparse text. Find as much text as possible in no particular order.) works well for desktop UIs
            custom_config = r'--psm 11'
            data = pytesseract.image_to_data(thresh, output_type=Output.DICT, config=custom_config)

            n_boxes = len(data['text'])
            target_lower = target_text.strip().lower()

            for i in range(n_boxes):
                word = data['text'][i].strip()
                if not word:
                    continue

                # Check case-insensitive substring matching
                if target_lower in word.lower() or word.lower() in target_lower:
                    # Retrieve coordinates in the upscaled image coordinate space
                    rx = data['left'][i]
                    ry = data['top'][i]
                    rw = data['width'][i]
                    rh = data['height'][i]

                    # Convert back to original screen coordinates (divide by upscale factor of 2)
                    orig_x = int((rx + rw / 2) / 2.0)
                    orig_y = int((ry + rh / 2) / 2.0)
                    conf = float(data['conf'][i]) / 100.0

                    print(f"[OCR Engine] Found match: '{word}' at screen coordinates [{orig_x}, {orig_y}] with confidence {conf:.1f}%")
                    return orig_x, orig_y, conf

        except Exception as e:
            print(f"[OCR Engine] Error during OCR processing: {e}")

        return None
