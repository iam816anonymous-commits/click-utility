# 🎯 Calibrated Native Automation Studio & Desktop Utility

> An ultra-performant, calibrated **Windows-native desktop automation studio and workflow engine** designed as a highly reliable, modular replacement for Power Automate and UiPath. Built using Python, PySide6 (Qt6), OpenCV, MSS, pynput, and Tesseract OCR.

---

## 🏛️ Modular Project Architecture

The application is modularly structured, ensuring clean separation of concerns and high maintainability (no UI module exceeds 500 lines of code):

```
native/
├── main.py              # Application Coordinator & Multithreading Main Loop
├── ui/                  # Highly Polished Modular PySide6 Package
│   ├── __init__.py      # Package export bindings
│   ├── dashboard.py     # Main Automation Dashboard, Top Toolbar, and Real-Time Stats
│   ├── rule_wizard.py   # Multi-Step Rule Configuration Wizard (Step 1-4) & offsets
│   ├── debug_panel.py   # Fullscreen Transparent HUD Overlay & Match Highlight views
│   ├── console_panel.py # Rich Rich-text logger presenting colorized execution statuses
│   ├── template_manager.py # Stored template cropping previewer and replace options
│   ├── settings.py      # Studio performance, FPS limits, and scale delay controls
│   ├── workflow_editor.py # Pipeline Sequence Workflow Visualizers (WHEN -> VERIFY -> ACTION)
│   └── calibration_dialog.py # DPI mouse calibration tools
├── capture_engine.py    # MSS-powered high-speed screen, region, & crop capture
├── match_engine.py      # OpenCV matching (edges NCC, color histograms, and pre/post validations)
├── ocr_engine.py        # pytesseract OCR engine with UI image preprocessing (Grayscale, Resize 2x, Thresholding)
├── click_engine.py      # Global Hotkey Hooks & high-precision mouse controller (micro-delays)
├── test_engines.py      # Modular unit test suite verifying calibrations, scoring, & matching
└── requirements.txt     # Pip Package dependencies list
```

---

## 🚀 Advanced Automation Studio Engine

This studio incorporates professional-grade automation pipelines to guarantee **pixel-perfect click accuracy** across diverse scaling environments and moved browser windows:

### 1. Advanced Rule Wizard Workflow
* **Step 1 (Trigger)**: Choose matching trigger mechanisms (🖼 Image, 🔤 OCR, 🎯 Absolute, 🪟 Window-Relative).
* **Step 2 (Calibration Click Offset)**: Interactive visual template clicked-point offset. Sets click relative to top-left.
* **Step 3 (Search Region)**: Scope search restriction constraints (Entire Screen, Active Window, Trained Region).
* **Step 4 (Parameters)**: Advanced sliders for confidence thresholds, cooldown delays, and name specifications.
* **Click Sequence Builder**: Exposes an interactive click sequence builder inside Step 4 where users can specify action types, custom offsets, delays, and delete individual steps visually.

### 2. Multi-Stage Pipeline Workflow Engine
Every rule operates on a robust sequential macro pipeline:
$$\text{WHEN} \longrightarrow \text{VERIFY} \longrightarrow \text{WAIT} \longrightarrow \text{ACTION} \longrightarrow \text{VERIFY RESULT} \longrightarrow \text{SUCCESS/RETRY}$$
1. **WHEN**: Scans and locates target matching.
2. **VERIFY**: Analyzes composite candidate scoring (cross-correlation, Canny edges NCC, and color histogram correlation) to disambiguate identical shapes.
3. **WAIT**: Pauses for specified post-verification timing.
4. **ACTION**: Dispatches calibrated click coordinates via explicit DPI-aware clicks (`moveTo` $\rightarrow$ `mouseDown` $\rightarrow$ `mouseUp`).
5. **VERIFY RESULT**: Performs pre-click pixel signature checks and post-click state evaluations (retrying click once if UI is unchanged).

### 3. Interactive DPI & Alignment Calibration Wizard
* Select **⚙️ Calibrate** from the toolbar to launch the interactive calibration assistant.
* The studio spawns a click-responsive target window over your monitor and places an Emerald green concentric crosshair on screen.
* Click precisely on the green target; the wizard evaluates the pixel difference between your cursor coordinates and PySide's device pixel coordinates to compute correction offsets per monitor.

### 4. Real-Time HUD Debug Overlay
Activating debug visual mode renders a transparent fullscreen HUD drawing:
- Green bounding boxes around all candidate target templates.
- A red crosshair at the exact scheduled calibration click coordinate.
- Text metadata including: template dimensions, detected top-left, click offset shift, DPI scaling ratios, confidence scores, and verification status.
- Pauses for exactly **1 second** before performing clicking events, letting developers verify mouse calibration live.

### 5. Multi-Tab Sidebar Panels
* **Console**: Rich HTML log console color-coding successes, info logs, and failure warnings.
* **Debugger**: Sidebar tracker presenting template previews, matching coordinates, state, and execution times.
* **Templates**: Crop previewer showing all target PNG files, and retake/replace/delete triggers.
* **Settings**: Tune scan FPS limits (from 5 to 30 FPS) and click synthesis delay intervals.
* **Workflow**: Pipeline steps visualizer.

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

### 2. Teaching Click calibration spot
Click exactly inside the template image box to establish your precise target pixel. The system stores offsets relative to the top-left rather than center clicking.

---

## 🧪 Running Unit Tests
A robust unit test suite covers everything from coordinate offsets, multi-step click sequence mapping, DPI scaling checks, restricted region cropping, candidate disambiguation scoring, and edge-based templates. Run with:
```bash
python -m pytest test_engines.py
```
