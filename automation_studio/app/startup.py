import os
from automation_studio.app.dependency_container import DependencyContainer
from automation_studio.capture.capture_engine import CaptureEngine
from automation_studio.mouse.click_engine import ClickEngine
from automation_studio.windows.coordinate_manager import SystemDpiCalibrator
from automation_studio.database.sqlite_manager import SQLiteManager
from automation_studio.rules.rule_manager import RuleManager

def run_startup_sequence():
    """
    Orchestrates the clean, structured application boot sequence:
    1. Ensure storage directory.
    2. Instantiate and register shared singletons in the DependencyContainer.
    """
    print("[Startup] Initializing Enterprise Desktop Automation Studio Services...")

    # Ensure targets directory exists
    os.makedirs("targets", exist_ok=True)

    # Get global DI container instance
    container = DependencyContainer.get_instance()

    # 1. Initialize & Register SQLite Manager
    db_manager = SQLiteManager()
    container.register("Database", db_manager)

    # 2. Initialize & Register CaptureEngine
    capture_engine = CaptureEngine.get_instance()
    container.register("CaptureEngine", capture_engine)

    # 3. Initialize & Register ClickEngine
    click_engine = ClickEngine.get_instance()
    container.register("ClickEngine", click_engine)

    # 4. Initialize & Register DPI Calibrator
    dpi_calibrator = SystemDpiCalibrator.get_instance()
    container.register("CoordinateManager", dpi_calibrator)

    # 5. Initialize & Register RuleManager with database binding
    rule_manager = RuleManager.get_instance(db_manager)
    container.register("RuleManager", rule_manager)

    print("[Startup] All core singletons successfully registered in DependencyContainer.")
