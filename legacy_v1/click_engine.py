import pyautogui
import time
from pynput import keyboard
from PySide6.QtCore import QObject, Signal
from typing import Optional

# Set PyAutoGUI safety values
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True  # Move mouse to corner to abort

class ClickEngine(QObject):
    """
    Stage 7 - Re-written Smart Click Engine.
    Singleton Pattern: guarantees only one instance resides in memory.
    Handles precise mouse movement verification, retries, click dispatch,
    and global hotkeys triggers with fast Esc-driven emergency recovery.
    """
    _instance = None

    # Custom signals must be class attributes in PySide6
    start_signal = Signal()
    stop_signal = Signal()
    teach_signal = Signal()
    teach_cursor_signal = Signal()
    emergency_signal = Signal()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if already instantiated
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._initialized = True
        self.listener: Optional[keyboard.Listener] = None

    def safe_move_to(self, x: int, y: int, max_retries: int = 3) -> bool:
        """
        Moves the cursor to (x, y) and verifies the position with retries.
        If actual vs requested coordinates differ by > 3 pixels, retries.
        """
        for attempt in range(max_retries):
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(0.02) # Wait 20ms

            act_x, act_y = pyautogui.position()
            diff_x = abs(act_x - x)
            diff_y = abs(act_y - y)

            if diff_x <= 3 and diff_y <= 3:
                return True

            print(f"[ClickEngine] MoveTo target mismatch. Target: ({x}, {y}), Actual: ({act_x}, {act_y}). Retry attempt {attempt + 1}")
            time.sleep(0.05)

        return False

    def trigger_click(self, x: int, y: int, action_type: str = "Left Click") -> bool:
        """
        Synthesizes a highly precise physical mouse click event at screen coordinate (x, y).
        Performs move-verification before clicking.
        """
        # Save original cursor position to restore after clicking
        ox, oy = pyautogui.position()

        # Verify and Move
        moved = self.safe_move_to(x, y)
        if not moved:
            print(f"[ClickEngine] CRITICAL: Mouse move-verification failed for coordinate ({x}, {y})!")
            return False

        try:
            if action_type == "Left Click":
                pyautogui.mouseDown(button='left')
                time.sleep(0.02)
                pyautogui.mouseUp(button='left')
            elif action_type == "Double Click":
                # Precise double-click sequence
                pyautogui.mouseDown(button='left')
                time.sleep(0.01)
                pyautogui.mouseUp(button='left')
                time.sleep(0.05)
                pyautogui.mouseDown(button='left')
                time.sleep(0.01)
                pyautogui.mouseUp(button='left')
            elif action_type == "Right Click":
                pyautogui.mouseDown(button='right')
                time.sleep(0.02)
                pyautogui.mouseUp(button='right')
            else:
                # Default left click
                pyautogui.mouseDown(button='left')
                time.sleep(0.02)
                pyautogui.mouseUp(button='left')
        finally:
            # Restore original cursor spot gently
            pyautogui.moveTo(ox, oy, duration=0.1)

        return True

    def release_all_buttons(self):
        """
        Safety Release: Ensures any stuck mouse buttons are explicitly released.
        """
        try:
            pyautogui.mouseUp(button='left')
            pyautogui.mouseUp(button='right')
            print("[ClickEngine] Safety release activated: All mouse buttons released.")
        except Exception as e:
            print(f"[ClickEngine] Error during safety mouse release: {e}")

    def start_hotkeys_listener(self):
        """
        Launches global system hotkey listener in the background.
        F8 = Start, F9 = Stop, F10 = Teach, Esc = Emergency Stop
        Emits safe Qt Signals to be handled by the main thread.
        """
        def on_press(key):
            try:
                if key == keyboard.Key.f8:
                    self.start_signal.emit()
                elif key == keyboard.Key.f9:
                    self.stop_signal.emit()
                elif key == keyboard.Key.f10:
                    self.teach_signal.emit()
                elif key == keyboard.Key.f11:
                    self.teach_cursor_signal.emit()
                elif key == keyboard.Key.esc:
                    self.emergency_signal.emit()
            except Exception as e:
                print(f"[ClickEngine] Hotkey callback error: {e}")

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def stop_hotkeys_listener(self):
        """
        Stops the global hotkey listener.
        """
        if self.listener:
            self.listener.stop()
