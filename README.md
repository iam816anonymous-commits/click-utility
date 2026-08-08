# 🎯 Professional Calibrated Desktop Automation Studio

> An ultra-performant, enterprise-grade **Windows-native desktop automation studio and workflow engine** designed as a highly reliable, modular replacement for Power Automate, UiPath, and SikuliX. Built using Python 3.12+, PySide6 (Qt6), OpenCV, and MSS.

---

## 🏛️ Modular Project Architecture

The studio follows a clean, single-responsibility, and strictly decoupled layer architecture, avoiding any circular imports:

```
automation_studio/
├── main.py                    # Root entry point & boots AutomationStudioApplication
├── app/
│   ├── __init__.py
│   ├── application.py         # Orchester and boots the QApplication lifecycle
│   ├── dependency_container.py # Thread-safe singleton Dependency Injection container
│   ├── startup.py             # Handles services registration & DB migrations on startup
│   └── shutdown.py            # Teardowns thread pools and unregisters hotkeys safely
├── capture/
│   ├── __init__.py
│   └── capture_engine.py      # High-performance MSS region screen capturer
├── matching/
│   ├── __init__.py
│   └── template_matcher.py    # OpenCV matching (SSD, multi-matches NMS, Canny NCC, and BGR histograms)
├── mouse/
│   ├── __init__.py
│   └── click_engine.py        # Safe moveTo checks, retries, and Win32 SendInput clicks
├── windows/
│   ├── __init__.py
│   ├── coordinate_manager.py  # Stage 3 immutable coordinate result & Stage 5 bounds checker
│   └── dpi_manager.py         # Dynamic DPI scale factors and monitor metrics
├── database/
│   ├── __init__.py
│   └── sqlite_manager.py      # Embedded SQL-backed database for rules, configurations, and stats
└── tests/                     # Clean independent unit testing suite
    ├── __init__.py
    ├── test_container.py      # Verifies dependency registration & resolves singletons
    ├── test_database.py       # Verifies SQL schema creations & rule CRUD operations
    ├── test_coordinates.py    # Verifies DPI scaling math & bounds validators
    └── test_matcher.py        # Verifies Canny edge matches, multi-matches NMS, & BGR filters
```

---

## 🚀 Advanced Automation Studio Engine

This studio incorporates professional-grade automation pipelines to guarantee **pixel-perfect click accuracy** across diverse scaling environments and displays:

### 1. Step-by-Step Interactive Rule Wizard
* **Step 1 (Trigger)**: Select macro triggers (🖼 Template, 🔤 OCR, 🎯 Absolute, 🪟 Window-Relative).
* **Step 2 (Teach Template)**: Draw crop boxes over targets directly from inside the Wizard, temporarily hiding dialogs to capture clean templates using the `CaptureEngine` singleton.
* **Step 3 (Calibrate Click Offset)**: Precise relative offset pickers allowing users to click exact desired pixels.
* **Step 4 (Search Region)**: Scope search restriction constraints (Entire Screen, Active Window, Trained Region).
* **Step 5 (Verification checklist)**: Detailed on-screen visual checklists confirming: `Template Found`, `Single Match`, `Click Point Inside`, `Window Valid`, `DPI Valid`, `Offset Valid`, etc.

### 2. Multi-Stage Pipeline Workflow Engine
Every rule operates on a robust sequential macro pipeline:
$$\text{WHEN} \longrightarrow \text{VERIFY} \longrightarrow \text{WAIT} \longrightarrow \text{ACTION} \longrightarrow \text{VERIFY RESULT} \longrightarrow \text{SUCCESS/RETRY}$$
1. **WHEN**: Scans and locates target matching.
2. **VERIFY**: Analyzes composite candidate scoring (cross-correlation, Canny edges NCC, and color histogram correlation) to disambiguate identical shapes.
3. **WAIT**: Pauses for specified post-verification timing.
4. **ACTION**: Dispatches calibrated click coordinates via explicit DPI-aware clicks (`moveTo` $\rightarrow$ `mouseDown` $\rightarrow$ `mouseUp`).
5. **VERIFY RESULT**: Performs pre-click pixel signature checks and post-click state evaluations (retrying click once if UI is unchanged).

---

## 🎮 How to Use & Operating Instructions

To launch the native desktop application, execute `main.py` using Python:
```bash
python main.py
```

### 🧪 Running Unit Tests
A robust, mock-shielded unit test suite runs completely headlessly on any platform (e.g. CI/CD) without requiring active X11 displays. Run with:
```bash
python -m pytest automation_studio/tests
```
---

## 📦 Legacy Version (v1 Archive)
For backwards compatibility, all previous source files are fully archived under the `legacy_v1/` directory as a reference package.
You can execute and test legacy code by running:
```bash
python legacy_v1/main.py
python -m pytest legacy_v1/test_engines.py
```
