import sys
import os

# Guarantee search paths find the new automation_studio packages
sys.path.append(os.path.join(os.path.dirname(__file__), "automation_studio"))

from automation_studio.app.application import AutomationStudioApplication

if __name__ == "__main__":
    """
    Main Entry Point for the Calibrated Desktop Automation Studio.
    """
    app = AutomationStudioApplication(sys.argv)
    sys.exit(app.start())
