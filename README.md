# 🎯 Native AutoClicker AI Desktop Utility

> A highly performant, lightweight, and extensible **Windows-native desktop automation utility** built using Python, PySide6 (Qt6), OpenCV, MSS, and pynput.

---

## 🏛️ Project Architecture

The application is fully modularized based on the recommended production desktop architecture:

```
native/
├── main.py              # Application Coordinator & Multithreading Main Loop
├── ui.py                # PySide6 (Qt) Layouts, Dialogs & Teach Overlays
├── capture_engine.py    # MSS-powered high-speed screen, region, & crop capture
├── match_engine.py      # OpenCV template match algorithm (Normalized Cross-Correlation)
├── click_engine.py      # Global Hotkey Hooks & pynput/pyautogui Mouse Controller
├── requirements.txt     # Pip Package dependencies list
└── targets/             # Folder containing trained target PNG crops
```

---

## 🚀 Installation & Local Setup

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your operating system.

### 2. Install Dependencies
Create a virtual environment (optional but recommended) and install the packages listed in `requirements.txt`:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required libraries
pip install -r requirements.txt
```

---

## 🎮 How to Use & Operating Instructions

To launch the native desktop application, execute `main.py` using Python:
```bash
python main.py
```

### 1. Global Hotkey Mappings
The utility hooks into the keyboard at the kernel/OS level, enabling global hotkeys that function even when the app is minimized:

| Hotkey | Action | Description |
| --- | --- | --- |
| 🟢 **F8** | **Start Monitor** | Activates the background screen scanning and matching thread. |
| ⏸ **F9** | **Stop Monitor** | Suspends the scanning loop safely. |
| 🎯 **F10** | **Teach Button** | Minimizes windows and presents a crosshair overlay. Draw a box over target elements to teach them! |
| 🚨 **Esc** | **Panic Emergency Stop** | Instantly stops all loops and aborts any pending click inputs. |

### 2. Teaching a Target
1. Press the **Teach Button (F10)** or click the button on the dashboard.
2. The screen will dim, and your cursor will turn into a crosshair.
3. Click and drag a bounding box around any button or image element you wish to automate (e.g. an "OK" button, connection alert, or game coins chest).
4. On release, a Configuration Modal will pop up.
5. Provide a rule name, choose trigger type (Image Match), set mouse action type (Left, Double, or Right click), set cooldown timer, and slide the confidence threshold.
6. Click **Save Rule**. It is stored inside `targets/` and registered into the active **Rules Manager Table** instantly.

### 3. Monitoring & Automation
1. Set the scan frequency using the GUI slider.
2. Click **Start Monitor (F8)**.
3. The background thread will scan your active display, find matches with the specified confidence threshold, restore your original cursor afterwards (human-like), and register logs under the Console!
