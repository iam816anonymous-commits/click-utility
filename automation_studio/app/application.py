import sys
from PySide6.QtWidgets import QApplication

from automation_studio.app.dependency_container import DependencyContainer
from automation_studio.app.startup import run_startup_sequence
from automation_studio.app.shutdown import run_shutdown_sequence

class AutomationStudioApplication:
    """
    Manages the lifecycle of the Calibrated Desktop Automation Studio application.
    Resolves registered dependencies from the DependencyContainer.
    """
    def __init__(self, argv: list):
        self.app = QApplication(argv)
        self.running = False
        self.coordinator = None

    def start(self) -> int:
        self.running = True

        # Run startup sequence to initialize and register singletons in DI container
        run_startup_sequence()

        # Resolve core dependencies
        container = DependencyContainer.get_instance()
        self.db_manager = container.resolve("Database")
        self.capture_engine = container.resolve("CaptureEngine")
        self.click_engine = container.resolve("ClickEngine")
        self.coordinate_manager = container.resolve("CoordinateManager")
        self.rule_manager = container.resolve("RuleManager")

        # Load Application Coordinator and show main GUI dashboard
        from automation_studio.controllers.application_controller import ApplicationCoordinator
        self.coordinator = ApplicationCoordinator(self)
        self.coordinator.dashboard.show()
        self.coordinator.start_hotkeys()

        print("[Lifecycle] Launching application main window...")

        exit_code = self.app.exec()

        self.stop()
        return exit_code

    def stop(self):
        if self.running:
            self.running = False
            run_shutdown_sequence()
