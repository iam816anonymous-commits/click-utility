from automation_studio.windows.coordinate_manager import SystemDpiCalibrator

class DPIManager:
    """
    Utility wrapper around coordinate pipeline's SystemDpiCalibrator.
    """
    @staticmethod
    def get_scale_factor() -> float:
        return SystemDpiCalibrator.get_instance().dpi_scale

    @staticmethod
    def get_logical_dimensions() -> tuple[int, int]:
        cal = SystemDpiCalibrator.get_instance()
        return cal.logical_w, cal.logical_h

    @staticmethod
    def get_physical_dimensions() -> tuple[int, int]:
        cal = SystemDpiCalibrator.get_instance()
        return cal.physical_w, cal.physical_h
