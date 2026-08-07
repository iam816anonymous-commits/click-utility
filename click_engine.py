import pyautogui
from pynput import keyboard
from PySide6.QtCore import QObject, Signal
from typing import Optional

# Set PyAutoGUI safety values
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True  # Move mouse to corner to abort

class ClickEngine(QObject):
    """
    Handles mouse click dispatch, macro sequence delays, and global hotkeys triggers.
    Inherits from QObject to safely emit Qt Signals when hotkeys are triggered from a background thread.
    """
    start_signal = Signal()
    stop_signal = Signal()
    teach_signal = Signal()
    teach_cursor_signal = Signal()
    emergency_signal = Signal()

    def __init__(self):
        super().__init__()
        self.listener: Optional[keyboard.Listener] = None

    def trigger_click(self, x: int, y: int, action_type: str = "Left Click"):
        """
        Synthesizes a highly precise physical mouse click event at screen coordinate (x, y)
        by using moveTo() + mouseDown() + mouseUp() sequences with micro-delays to eliminate
        coordinate drift caused by high DPI scaling setups.
        """
        import time

        # Save original cursor position to restore after clicking (human-like)
        ox, oy = pyautogui.position()

        if action_type == "Left Click":
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(0.02)
            pyautogui.mouseDown(button='left')
            time.sleep(0.02)
            pyautogui.mouseUp(button='left')
        elif action_type == "Double Click":
            # Highly precise double-click
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(0.02)
            pyautogui.mouseDown(button='left')
            time.sleep(0.01)
            pyautogui.mouseUp(button='left')
            time.sleep(0.05)
            pyautogui.mouseDown(button='left')
            time.sleep(0.01)
            pyautogui.mouseUp(button='left')
        elif action_type == "Right Click":
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(0.02)
            pyautogui.mouseDown(button='right')
            time.sleep(0.02)
            pyautogui.mouseUp(button='right')
        else:
            # Default fallback left click
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(0.02)
            pyautogui.mouseDown(button='left')
            time.sleep(0.02)
            pyautogui.mouseUp(button='left')

        # Restore original cursor spot
        pyautogui.moveTo(ox, oy, duration=0.1)

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
