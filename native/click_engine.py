import time
import pyautogui
from pynput import keyboard
from typing import Callable, Optional

# Set PyAutoGUI safety values
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True  # Move mouse to corner to abort

class ClickEngine:
    """
    Handles mouse click dispatch, macro sequence delays, and global hotkeys triggers.
    """
    def __init__(self, on_start: Callable, on_stop: Callable, on_teach: Callable, on_emergency: Callable):
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_teach = on_teach
        self.on_emergency = on_emergency
        self.listener: Optional[keyboard.Listener] = None

    def trigger_click(self, x: int, y: int, action_type: str = "Left Click"):
        """
        Synthesizes a physical mouse click event at screen coordinate (x, y).
        """
        # Save original cursor position to restore after clicking (human-like)
        ox, oy = pyautogui.position()

        if action_type == "Left Click":
            pyautogui.click(x, y)
        elif action_type == "Double Click":
            pyautogui.doubleClick(x, y)
        elif action_type == "Right Click":
            pyautogui.rightClick(x, y)
        else:
            pyautogui.click(x, y) # Default fallback

        # Restore original cursor spot
        pyautogui.moveTo(ox, oy, duration=0.1)

    def start_hotkeys_listener(self):
        """
        Launches global system hotkey listener in the background.
        F8 = Start, F9 = Stop, F10 = Teach, Esc = Emergency Stop
        """
        def on_press(key):
            try:
                if key == keyboard.Key.f8:
                    self.on_start()
                elif key == keyboard.Key.f9:
                    self.on_stop()
                elif key == keyboard.Key.f10:
                    self.on_teach()
                elif key == keyboard.Key.esc:
                    self.on_emergency()
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
