import threading
from typing import Dict, Any

class DependencyContainer:
    """
    Centralized, thread-safe Dependency Injection Container.
    Manages and resolves singletons across services, managers, and engines.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._services: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = True

    def register(self, name: str, instance: Any):
        """
        Registers a service instance in the container.
        """
        with self._lock:
            self._services[name] = instance

    def resolve(self, name: str) -> Any:
        """
        Resolves a registered service from the container.
        """
        with self._lock:
            if name not in self._services:
                raise ValueError(f"Service '{name}' has not been registered in the container.")
            return self._services[name]

    def clear(self):
        """
        Clears all registered services (useful for testing resets).
        """
        with self._lock:
            self._services.clear()
