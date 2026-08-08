import time

class LoggingService:
    """
    Centralized LoggingService for the Calibrated Automation Studio.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.log_callbacks = []

    def register_callback(self, callback):
        """
        Registers a callback function to receive formatted log messages (e.g. ui dashboard logger).
        """
        if callback not in self.log_callbacks:
            self.log_callbacks.append(callback)

    def log(self, message: str, level: str = "INFO"):
        """
        Formats and broadcasts a log message to all registered listeners.
        """
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{level}]"
        if level == "SUCCESS":
            prefix = "[✓]"
        elif level == "WARNING":
            prefix = "[⚠️]"
        elif level == "ERROR":
            prefix = "[🚨]"

        formatted_message = f"[{timestamp}] {prefix} {message}"
        print(formatted_message)

        for cb in self.log_callbacks:
            try:
                cb(formatted_message)
            except Exception:
                pass

    def info(self, msg: str):
        self.log(msg, "INFO")

    def success(self, msg: str):
        self.log(msg, "SUCCESS")

    def warning(self, msg: str):
        self.log(msg, "WARNING")

    def error(self, msg: str):
        self.log(msg, "ERROR")
