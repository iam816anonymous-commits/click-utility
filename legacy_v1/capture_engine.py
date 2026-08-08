import mss
import numpy as np
from PIL import Image

class CaptureEngine:
    """
    High-performance screen, region, and window capturing utility powered by MSS.
    Singleton Pattern: guarantees only one instance resides in memory.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if already instantiated
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
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

    @staticmethod
    def get_active_window_rect():
        """
        Retrieves the active window's title, top-left (left, top), and dimensions (width, height).
        Safely falls back on Linux/headless environments to mock values.
        """
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active:
                title = active.title if active.title else "Untitled Window"
                return title, int(active.left), int(active.top), int(active.width), int(active.height)
        except Exception:
            pass
        return "Headless Active Window", 100, 100, 1024, 768
