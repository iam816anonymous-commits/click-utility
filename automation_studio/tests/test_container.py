import unittest
from unittest.mock import MagicMock
import sys

# Mock GUI modules if they are not available
if "PySide6" not in sys.modules:
    sys.modules["PySide6"] = MagicMock()
    sys.modules["PySide6.QtCore"] = MagicMock()
    sys.modules["PySide6.QtWidgets"] = MagicMock()
    sys.modules["PySide6.QtGui"] = MagicMock()

from automation_studio.app.dependency_container import DependencyContainer

class TestDependencyContainer(unittest.TestCase):
    """
    Unit tests for the thread-safe Dependency Injection Container.
    """
    def setUp(self):
        self.container = DependencyContainer.get_instance()
        self.container.clear()

    def test_singleton_resolution(self):
        mock_service = MagicMock()
        self.container.register("mock_service", mock_service)

        resolved = self.container.resolve("mock_service")
        self.assertEqual(resolved, mock_service)

    def test_unregistered_service_throws(self):
        with self.assertRaises(ValueError):
            self.container.resolve("non_existent")

    def test_get_instance_is_singleton(self):
        another_container = DependencyContainer.get_instance()
        self.assertEqual(self.container, another_container)
