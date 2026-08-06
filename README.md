# 🎯 Native AutoClicker AI Desktop Utility

> A highly performant, lightweight, and extensible **Windows-native desktop automation utility** built using Python, PySide6 (Qt6), OpenCV, MSS, pynput, and pytesseract.

---

## 🏛️ Project Architecture

The application is fully modularized based on the recommended production desktop architecture:

```
native/
├── main.py              # Application Coordinator & Multithreading Main Loop
├── ui.py                # PySide6 (Qt) Layouts, Dialogs, Click Sequence Builder & Teach Overlays
├── capture_engine.py    # MSS-powered high-speed screen, region, & crop capture
├── match_engine.py      # OpenCV template match algorithm (Normalized Cross-Correlation)
├── ocr_engine.py        # pytesseract OCR engine with UI image preprocessing (Grayscale, Resize 2x, Thresholding)
├── click_engine.py      # Global Hotkey Hooks & pynput/pyautogui Mouse Controller
├── test_engines.py      # Unit test suite verifying match algorithms & sequence model
├── requirements.txt     # Pip Package dependencies list
└── targets/             # Folder containing trained target PNG crops
```

---

## 🚀 Installation & Local Setup

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your operating system.

### 2. Tesseract OCR Installation (For OCR Text Mode)
The OCR Text Match feature utilizes Tesseract OCR.
* **Windows:** Download the installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and add Tesseract to your system PATH.
* **macOS:** Install via Homebrew: `brew install tesseract`
* **Linux (Ubuntu/Debian):** Install via apt: `sudo apt-get install tesseract-ocr`

### 3. Install Dependencies
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
5. Provide a rule name, choose trigger type:
   - **Image Template Match**: Locates the visual target.
   - **OCR Text Match**: Reads screen text and locates the specified word.
   - **Absolute Cursor Position**: Triggers instantly at the captured coordinates.
   - **Window-Relative Position**: Triggers relative to the active window top-left corner, ensuring accurate clicks even if the window is moved on the screen!
6. Slide the confidence threshold (default **90%** avoids false clicks like clicking a profile picture instead of a dashboard option).
7. Configure the **Click Sequence Builder** below!

### 3. Click Sequence Builder (Multiple Click Steps)
Instead of just clicking the matched target center once, you can configure complex multi-step click sequence macros:
* **Add custom steps**: Click `➕ Add Click Step` after specifying:
  - **Action Type**: Single Click, Double Click, or Right Click.
  - **Relative Pixel Offset (X, Y)**: Offset coordinates from the matched template center (e.g. click 100px to the right).
  - **Delay**: Custom delay (Seconds) before the next action executes.
* **Delete steps**: Use the individual trash can (`🗑️`) button to delete any step you entered in the builder if not needed.

### 4. Rule Deletion
You can clean up rules instantly by clicking the **🗑️ Delete** button in the "Actions" column in the main Dashboard table. This safely removes the rule from memory and cleans up the associated template file on disk.

### 5. Running Tests
You can run the headless-compatible unit tests anytime using pytest:
```bash
python -m pytest test_engines.py
```
