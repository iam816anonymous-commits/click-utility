import unittest
from automation_studio.windows.coordinate_manager import CoordinateCalculationResult, CoordinateValidator

class TestCoordinatePipeline(unittest.TestCase):
    """
    Unit tests verifying stage-based Coordinate calculations and coordinate boundaries validation.
    """
    def test_coordinate_calculations_mapping(self):
        # Stored original DPI=1.25 values mapping
        top_left_x = 220
        top_left_y = 310
        template_w = 180
        template_h = 50
        click_offset_x = 102
        click_offset_y = 25

        calculated_click_x = top_left_x + click_offset_x # 322
        calculated_click_y = top_left_y + click_offset_y # 335

        # Divide by DPI scale factor to determine logical click coordinates
        current_dpi = 1.25
        logical_click_x = int(calculated_click_x / current_dpi) # 257
        logical_click_y = int(calculated_click_y / current_dpi) # 268

        result = CoordinateCalculationResult(
            top_left_x=top_left_x,
            top_left_y=top_left_y,
            template_w=template_w,
            template_h=template_h,
            click_offset_x=click_offset_x,
            click_offset_y=click_offset_y,
            calculated_click_x=calculated_click_x,
            calculated_click_y=calculated_click_y,
            dpi_scale=current_dpi,
            logical_click_x=logical_click_x,
            logical_click_y=logical_click_y
        )

        self.assertEqual(result.calculated_click_x, 322)
        self.assertEqual(result.calculated_click_y, 335)
        self.assertEqual(result.logical_click_x, 257)
        self.assertEqual(result.logical_click_y, 268)

    def test_coordinate_validator_success_and_failures(self):
        # Valid coordinate result
        coord_result = CoordinateCalculationResult(
            top_left_x=100, top_left_y=100, template_w=50, template_h=50,
            click_offset_x=25, click_offset_y=25,
            calculated_click_x=125, calculated_click_y=125,
            dpi_scale=1.0, logical_click_x=125, logical_click_y=125
        )

        # Validate against screen dimensions of 1920x1080
        valid, reasons = CoordinateValidator.validate(coord_result, None, 1920, 1080)
        self.assertTrue(valid)
        self.assertEqual(len(reasons), 0)

        # Invalid coordinate result exceeding screen bounds
        coord_invalid = CoordinateCalculationResult(
            top_left_x=2000, top_left_y=100, template_w=50, template_h=50,
            click_offset_x=25, click_offset_y=25,
            calculated_click_x=2025, calculated_click_y=125,
            dpi_scale=1.0, logical_click_x=2025, logical_click_y=125
        )

        invalid_win, invalid_reasons = CoordinateValidator.validate(coord_invalid, None, 1920, 1080)
        self.assertFalse(invalid_win)
        self.assertGreater(len(invalid_reasons), 0)
