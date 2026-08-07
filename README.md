# 🎯 Calibrated Native Automation Studio & Desktop Utility

> A highly performant, lightweight, and extensible **Windows-native desktop automation utility and workflow engine** built using Python, PySide6 (Qt6), OpenCV, MSS, pynput, and pytesseract.

---

## 🏛️ Project Architecture

The application is fully modularized based on the recommended production desktop architecture:

```
native/
├── main.py              # Application Coordinator & Multithreading Main Loop
├── ui.py                # PySide6 (Qt) Layouts, Dialogs, Click Offset Calibration, & Overlays
├── capture_engine.py    # MSS-powered high-speed screen, region, & crop capture
├── match_engine.py      # OpenCV template match algorithm (Canny edges NCC, color histograms correlation)
├── ocr_engine.py        # pytesseract OCR engine with UI image preprocessing (Grayscale, Resize 2x, Thresholding)
├── click_engine.py      # Global Hotkey Hooks & high-precision mouse controller (micro-delays)
├── test_engines.py      # Headless unit test suite verifying calibrations, scoring, & matching
├── requirements.txt     # Pip Package dependencies list
└── targets/             # Folder containing trained target PNG crops
```

---

## 🚀 Advanced Automation Studio Features

This utility incorporates professional-grade automation strategies to compete with platforms like UiPath, Power Automate, and SikuliX, ensuring **pixel-perfect click accuracy** across diverse scaling environments and moved windows:

### 1. User Offset Click Calibration (No Center Clicking!)
* During Teach Mode, the user draws a bounding box over a target UI element.
* Instead of assuming the click target is the template's exact center, the **Target Calibration Click Offset** panel inside the Save Modal allows the user to click the **exact desired point** inside the cropped template preview.
* The system computes and stores `click_offset_x` and `click_offset_y` relative to the template's top-left corner, ensuring perfect clicking alignment regardless of template dimensions.

### 2. Multi-Stage Similar UI Disambiguation
* When matching identical visual components (e.g., repeating navigation sidebar tabs like Dashboard, Content, Analytics, and Community), standard template matchers can false-positive.
* This studio implements a custom candidate scoring system:
  1. **Template Confidence**: `TM_CCOEFF_NORMED` cross-correlation matching.
  2. **Edge Similarity**: Normalized Cross-Correlation over Canny edge-detected black-and-white structures.
  3. **Color Histogram Similarity**: Correlation coefficient comparison of 3D BGR color histograms.
* The matcher computes a composite score, selecting the candidate with the highest overall similarity rather than the first match.

### 3. Dynamic Search Region Restriction Caching
* Searching the entire desktop screen on every frame is CPU-intensive and can lead to false positives.
* Upon the first successful match of a rule, the background scanner **caches the matched bounding box**.
* Subsequent scans are restricted to a padded region surrounding that location. If the target is moved or lost, the scanner gracefully resets back to full screen.

### 4. High-Precision Click Pipeline (Zero DPI Drift)
* Bypasses standard `pyautogui.click()` to prevent coordinate mismatches on high-DPI scaling (e.g., 125%, 150%) and multiple monitor setups.
* Synthesizes click operations using explicit sequence transitions (`moveTo` $\rightarrow$ `mouseDown` $\rightarrow$ `mouseUp`) separated by micro-delays (`0.02s`), ensuring Windows registers clicks on the exact targeted screen coordinates.

### 5. Multi-Stage Pre/Post-Click Verification
* **Pre-Click Verification**: Before clicking, the engine captures a tiny region around the click target on-screen and verifies if the expected pixels from the template still exist. If verification fails, the click is aborted.
* **Post-Click UI State Change**: After clicking, the system captures a region around the click point and determines if the UI changed. If unchanged, it retries once. If it remains unchanged, it logs `Click ineffective` and flags it as a failure, preventing infinite loop clicking.

### 6. System DPI & Calibration Wizard
* Launches an interactive Calibration Wizard to auto-evaluate active primary monitor resolutions, PySide6 Device Pixel Ratio scaling ratios, and verify alignment correction parameters.

### 7. Real-Time HUD Debug Overlay
* Activating debug visual mode renders a transparent fullscreen HUD drawing:
  - Green bounding boxes around all candidate target templates.
  - A red crosshair at the exact scheduled calibration click coordinate.
  - Text metadata including: template dimensions, detected top-left, click offset shift, DPI scaling ratios, confidence scores, and verification status.
* Pauses for exactly **1 second** before performing clicking events, letting developers verify mouse calibration live.

---

## 🎮 How to Use & Operating Instructions

To launch the native desktop application, execute `main.py` using Python:
```bash
python main.py
```

### 1. Global Hotkey Mappings
Global keyboard hooks operate even when the application dashboard is minimized:

| Hotkey | Action | Description |
| --- | --- | --- |
| 🟢 **F8** | **Start Monitor** | Activates the background screen scanning and matching thread. |
| ⏸ **F9** | **Stop Monitor** | Suspends the scanning loop safely. |
| 🎯 **F10** | **Teach Button** | Minimizes windows and presents a crosshair overlay. Draw a box over target elements to teach them! |
| 🚨 **Esc** | **Panic Emergency Stop** | Instantly stops all loops and aborts any pending click inputs. |

### 2. Rule Configuration Modal
Upon releasing a drawn box during visual teaching (F10):
1. **DPI-Calibrated Bounding Box**: The dialog opens with a custom, click-responsive image loader showing the cropped template.
2. **Set Click Coordinates**: Click directly inside the template image box to establish your precise target pixel.
3. **Set Trigger Options**: Adjust Trigger Mechanism (Image Match, OCR Match, Absolute, Window-Relative), confidence threshold, and rule cooldown.
4. **Sequence Builder**: Add sequential click actions (Single, Double, Right Click) relative to your calibration point with micro-delays.
5. Save safely under active background locks!

---

## 🧪 Running Unit Tests
A robust unit test suite covers everything from coordinate offsets, multi-step click sequence mapping, DPI scaling checks, restricted region cropping, candidate disambiguation scoring, and edge-based templates. Run with:
```bash
python -m pytest test_engines.py
```
