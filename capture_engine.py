import mss
import numpy as np
from PIL import Image

class CaptureEngine:
    """
    High-performance screen, region, and window capturing utility powered by MSS.
    """
    def __init__(self):
        self.sct = mss.mss()

    def capture_full_screen(self) -> np.ndarray:
        """
        Captures the primary monitor and returns a BGR OpenCV-compatible numpy array.
        """
        monitor = self.sct.monitors[1] # Primary monitor
        screenshot = self.sct.grab(monitor)
        # Convert raw BGRA pixels to BGR numpy array
        img = np.array(screenshot)
        return img[:, :, :3] # Remove alpha channel

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """
        Captures a specific screen rectangular coordinate region.
        """
        monitor = {"top": y, "left": x, "width": w, "height": h}
        screenshot = self.sct.grab(monitor)
        img = np.array(screenshot)
        return img[:, :, :3]

    def save_template(self, x: int, y: int, w: int, h: int, filepath: str):
        """
        Grabs a screen region and saves it as a PNG file.
        """
        monitor = {"top": y, "left": x, "width": w, "height": h}
        screenshot = self.sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.save(filepath, "PNG")
