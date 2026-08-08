from typing import Tuple, Optional

class SystemDpiCalibrator:
    """
    Stage 4 - Dedicated DPI Calibration Module.
    During startup, determines:
    - Monitor DPI (devicePixelRatio)
    - Windows scaling ratio
    - Logical resolution (width, height)
    - Physical resolution (width, height)
    - PyAutoGUI coordinate system limits
    - MSS coordinate system limits
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.dpi_scale = 1.0
        self.logical_w = 1920
        self.logical_h = 1080
        self.physical_w = 1920
        self.physical_h = 1080

        self.pyautogui_limit_x = 1920
        self.pyautogui_limit_y = 1080
        self.mss_limit_x = 1920
        self.mss_limit_y = 1080

        self.initialize_calibration()

    def initialize_calibration(self):
        try:
            from PySide6.QtWidgets import QApplication
            primary_screen = QApplication.primaryScreen()
            if primary_screen:
                self.dpi_scale = primary_screen.devicePixelRatio()
                geom = primary_screen.geometry()
                self.logical_w = geom.width()
                self.logical_h = geom.height()
                self.physical_w = int(self.logical_w * self.dpi_scale)
                self.physical_h = int(self.logical_h * self.dpi_scale)
        except Exception as e:
            print(f"[DPI Calibrator] Screen calibration fallback: {e}")

        try:
            import pyautogui
            sz = pyautogui.size()
            self.pyautogui_limit_x = sz[0]
            self.pyautogui_limit_y = sz[1]
        except Exception:
            pass

        try:
            import mss
            with mss.mss() as sct:
                mon = sct.monitors[1]
                self.mss_limit_x = mon["width"]
                self.mss_limit_y = mon["height"]
        except Exception:
            pass


class CoordinateCalculationResult:
    """
    Stage 3 - Immutable Coordinate Handling representation.
    Separate and distinct physical vs logical representation to prevent high DPI drift.
    """
    def __init__(
        self,
        top_left_x: int,
        top_left_y: int,
        template_w: int,
        template_h: int,
        click_offset_x: int,
        click_offset_y: int,
        calculated_click_x: int,
        calculated_click_y: int,
        dpi_scale: float,
        logical_click_x: int,
        logical_click_y: int
    ):
        self.top_left_x = top_left_x
        self.top_left_y = top_left_y
        self.template_w = template_w
        self.template_h = template_h
        self.click_offset_x = click_offset_x
        self.click_offset_y = click_offset_y
        self.calculated_click_x = calculated_click_x # Physical match center + relative offsets
        self.calculated_click_y = calculated_click_y # Physical match center + relative offsets
        self.dpi_scale = dpi_scale
        self.logical_click_x = logical_click_x # Logical click (PyAutoGUI Ready, divided by current_dpi)
        self.logical_click_y = logical_click_y # Logical click (PyAutoGUI Ready, divided by current_dpi)


class CoordinateValidator:
    """
    Stage 5 - Coordinate Validator before executing clicks.
    """
    @staticmethod
    def validate(
        coord_result: CoordinateCalculationResult,
        window_rect: Optional[Tuple[int, int, int, int]], # wx, wy, ww, wh
        screen_w: int,
        screen_h: int
    ) -> Tuple[bool, list[str]]:
        reasons = []

        in_temp_x = (coord_result.calculated_click_x >= coord_result.top_left_x) and \
                    (coord_result.calculated_click_x <= coord_result.top_left_x + coord_result.template_w)
        in_temp_y = (coord_result.calculated_click_y >= coord_result.top_left_y) and \
                    (coord_result.calculated_click_y <= coord_result.top_left_y + coord_result.template_h)

        if not (in_temp_x and in_temp_y):
            reasons.append(
                f"Click point ({coord_result.calculated_click_x}, {coord_result.calculated_click_y}) "
                f"falls outside template physical bounds starting at ({coord_result.top_left_x}, {coord_result.top_left_y}) "
                f"with size {coord_result.template_w}x{coord_result.template_h}."
            )

        if window_rect:
            wx, wy, ww, wh = window_rect
            in_win_x = (coord_result.calculated_click_x >= wx) and (coord_result.calculated_click_x <= wx + ww)
            in_win_y = (coord_result.calculated_click_y >= wy) and (coord_result.calculated_click_y <= wy + wh)
            if not (in_win_x and in_win_y):
                reasons.append(
                    f"Click point falls outside target window bounds: "
                    f"X: {coord_result.calculated_click_x} (Win: {wx} to {wx+ww}), "
                    f"Y: {coord_result.calculated_click_y} (Win: {wy} to {wy+wh})."
                )

        in_screen_x = (coord_result.calculated_click_x >= 0) and (coord_result.calculated_click_x < screen_w)
        in_screen_y = (coord_result.calculated_click_y >= 0) and (coord_result.calculated_click_y < screen_h)
        if not (in_screen_x and in_screen_y):
            reasons.append(
                f"Physical click ({coord_result.calculated_click_x}, {coord_result.calculated_click_y}) "
                f"exceeds physical screen dimensions of {screen_w}x{screen_h}."
            )

        if coord_result.click_offset_x < 0 or coord_result.click_offset_x > coord_result.template_w:
            reasons.append(f"Click offset X ({coord_result.click_offset_x}) is invalid (range: 0-{coord_result.template_w}).")
        if coord_result.click_offset_y < 0 or coord_result.click_offset_y > coord_result.template_h:
            reasons.append(f"Click offset Y ({coord_result.click_offset_y}) is invalid (range: 0-{coord_result.template_h}).")

        return len(reasons) == 0, reasons
