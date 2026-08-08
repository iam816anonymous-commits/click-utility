class MacroRule:
    """
    Data model representing a visual macro click rule.
    """
    def __init__(self, id_str: str, name: str, trigger_type: str, action: str, cooldown: float, threshold: float, template_path: str, click_steps: list = None, abs_x: int = None, abs_y: int = None, window_title: str = None, window_offset_x: int = None, window_offset_y: int = None, window_handle: int = None, countdown_delay: int = None, coordinate_history: list = None, search_region: str = "Entire Screen", anchor_rule_id: str = None, train_x: int = None, train_y: int = None, train_w: int = None, train_h: int = None, use_edges: bool = False, click_offset_x: int = None, click_offset_y: int = None, window_client_w: int = None, window_client_h: int = None, dpi_scale: float = 1.0, calibration_correction_x: float = 0.0, calibration_correction_y: float = 0.0):
        self.id_str = id_str
        self.name = name
        self.trigger_type = trigger_type
        self.action = action
        self.cooldown = cooldown
        self.threshold = threshold
        self.template_path = template_path
        self.abs_x = abs_x
        self.abs_y = abs_y
        self.window_title = window_title
        self.window_offset_x = window_offset_x
        self.window_offset_y = window_offset_y
        self.window_handle = window_handle
        self.countdown_delay = countdown_delay
        self.coordinate_history = coordinate_history if coordinate_history is not None else []
        self.search_region = search_region # "Entire Screen", "Active Window Only", "Trained Region Only"
        self.anchor_rule_id = anchor_rule_id # ID of rule that serves as Anchor
        self.train_x = train_x
        self.train_y = train_y
        self.train_w = train_w
        self.train_h = train_h
        self.use_edges = use_edges

        # User defined click calibration offset within template (top-left relative)
        self.click_offset_x = click_offset_x
        self.click_offset_y = click_offset_y

        # Stored original window/screen states for calibration
        self.window_client_w = window_client_w
        self.window_client_h = window_client_h
        self.dpi_scale = dpi_scale

        # Stored calibration wizard correction offsets
        self.calibration_correction_x = calibration_correction_x
        self.calibration_correction_y = calibration_correction_y

        # Cache for localized restricted regions
        self.last_matched_region = None # Tuple of (x, y, w, h)

        self.active = True
        self.last_triggered = 0.0

        # Rule statistics tracking attributes
        self.matches_count = 0
        self.clicks_count = 0
        self.failures_count = 0

        # If no click steps specified, default to a single step at the center (offset 0,0)
        if click_steps is None:
            self.click_steps = [{"action": action, "offset_x": 0, "offset_y": 0, "delay": 0.5}]
        else:
            self.click_steps = click_steps
