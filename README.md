# 🎯 AutoClicker AI Workspace

> A modern, interactive **Teach-and-Click Visual Macro Automation Platform** designed to simulate and educate users on classical computer vision and DOM automation strategies.

Developed using **Vite, React, TypeScript, and Tailwind CSS**, featuring an on-screen operating system sandbox, drag-to-crop pixel training, real-time scanning loops, a live console, and complete copy-pasteable production automation code snippets.

---

## 🚀 Interactive Workspace Overview

This application simulates a visual desktop automation system that allows you to **"teach"** a macro to click elements once, and **automatically tracks and clicks them** whenever they reappear on the screen.

### Core Features

1. **Simulated Desktop Sandbox**:
   - Includes draggable and interactive virtual application windows (e.g., **Coin Miner Idle Game**, **System Warning security agent**, and a **Mock Web Browser**).
   - Dynamically spawns moving targets like yellow `CLAIM REWARD!` buttons and critical modals.
2. **Interactive Training Modes**:
   - **Pixel Match Mode (Computer Vision)**: Click and drag any rectangle on the desktop to crop a template image. The program records the pixel matrix, dimensions, and offset.
   - **CSS Selector Mode (Browser Automation)**: Hover over web browser elements to inspect their tags and teach the program their direct DOM CSS selector pathways.
3. **Real-Time Monitoring Core**:
   - Toggle the active scan loop on/off.
   - Live sliding controls for scanning frequency (up to 20Hz) and confidence tolerances.
   - Displays real-time matching highlights and animated pulsing green circles on successful automated clicks.
4. **Live Scan Logs Console**:
   - A streaming console displaying real-time matching statistics, SAD calculations, trigger reports, and macro logs.

---

## ⚙️ Computer Vision Core: SAD Match Engine

The pixel-based matching engine is implemented from scratch in pure **TypeScript** (`src/utils/matching.ts`) to operate with **zero latency** directly on HTML5 Canvas `ImageData`.

### The Algorithm
The system utilizes a **Sum of Absolute Differences (SAD)** formula normalized across R, G, and B color channels:

$$\text{SAD}(x, y) = \sum_{dy=0}^{H-1} \sum_{dx=0}^{W-1} \left( |R_{\text{screen}} - R_{\text{template}}| + |G_{\text{screen}} - G_{\text{template}}| + |B_{\text{screen}} - B_{\text{template}}| \right)$$

To turn the resulting SAD error score into a readable match confidence percentage:

$$\text{Confidence} = 100 \times \left(1.0 - \frac{\text{SAD}}{\text{Max Possible SAD}}\right)$$

Where $\text{Max Possible SAD} = 255 \times 3 \times W \times H$.

### Performance Optimizations
To achieve 10–20 screen scans per second smoothly in the browser, the match engine implements two critical speedups:
1. **Early Termination**: As the nested template loops run, the accumulated SAD error is compared to the current best match. If the error exceeds the best match, the loop breaks instantly, saving millions of calculations.
2. **Dual-Pass Coarse-to-Fine Search**: For large templates, the engine first runs a coarse pass checking every $2^{\text{nd}}$ pixel. Once the best coarse candidate coordinate is located, it executes a full-resolution local fine search within a tightly bounded neighborhood.

---

## 🏛️ The 4 Production Automation Architectures

The workspace includes copyable, robust code templates explaining how to implement each of the four core automation patterns in production environments:

### Option 1: Image Matching (Simplest)
- **Concept**: Repeatedly grabs screenshots and uses OpenCV template matching to find the pixel coordinate of the cropped button, then clicks it using mouse controllers.
- **Libraries**: `OpenCV (cv2)`, `MSS` (fast screen grabs), `PyAutoGUI` / `pynput` (mouse control).
- **Pros/Cons**: Perfect for static applications and games, but fails on dark/light mode changes, text reflow, or screen scaling adjustments.

### Option 2: OCR-based Matching (Dynamic Text)
- **Concept**: Reads text on the screen using optical character recognition, parses word locations, and clicks the center coordinates of matching phrases.
- **Libraries**: `Tesseract OCR (pytesseract)`, `PaddleOCR`, `EasyOCR`.
- **Pros/Cons**: Works even if button colors or designs change slightly, but is computationally expensive and slow for fast real-time tasks.

### Option 3: OS UI Automation (Native OS Access)
- **Concept**: Communicates directly with the operating system accessibility layer to inspect the desktop window hierarchy and invoke native click events.
- **Libraries**: `pywinauto`, `UIAutomation` (Windows), `Atomac` (macOS).
- **Pros/Cons**: 100% reliable, works even if windows are covered or minimized, but is limited to supported native apps and platform-specific code.

### Option 4: Browser Automation (Web Apps)
- **Concept**: Drives a headless browser directly using direct DOM API selectors (CSS/XPath).
- **Libraries**: `Playwright`, `Selenium`, `Puppeteer`.
- **Pros/Cons**: Fast, robust, and completely independent of window sizes or physical mouse cursors. Ideal for web automation.

---

## 🛠️ Local Development & Build Setup

This project uses **Bun** as its package manager and runtime.

### Prerequisites
Make sure you have [Bun](https://bun.sh/) installed:
```bash
curl -fsSL https://bun.sh/install | bash
```

### Installation
Clone the repository and install dependencies:
```bash
bun install
```

### Run the Dev Server
Launch Vite's hot-reloading development server on port 3000:
```bash
__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=.com bun run dev --host 0.0.0.0 --port 3000
```
Open [http://localhost:3000/](http://localhost:3000/) in your browser.

### Compile Production Build
Generate fully optimized, production-ready static assets under `/dist`:
```bash
bun run build
```

---

## 📝 License
Educational Sandbox Simulation Project. Free to use, adapt, and build upon. Custom CAD/SAD template match engine copyright © 2026.
