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

## ⚡ Real-Time Website Automation Strategies

When automating **real-time websites** (such as high-frequency trading dashboards, ticket queues, or WebSocket-driven portals), traditional interval-based polling is too slow and resource-heavy. Production setups use the following low-latency techniques:

1. **MutationObserver (Sub-Millisecond Reactions)**:
   - Instead of checking the page every 100ms, a `MutationObserver` hooks directly into the browser's DOM rendering engine. It fires a callback **microtask** immediately when elements are injected or modified, clicking them in under `1ms`.
2. **requestAnimationFrame (V-Sync Alignment)**:
   - For canvas-based web elements, aligning polling with the screen's refresh rate (V-Sync) via `requestAnimationFrame` ensures matching is synchronized with the browser's paint cycle, running up to 144 times/sec without causing thread locks.
3. **Bypassing Click Protections (Event Synthesis)**:
   - Real-time websites often block naive `.click()` calls. To look fully human and bypass bot shields, automate elements by dispatching a sequence of trust-conforming events: `pointerdown` → `mousedown` → `pointerup` → `mouseup` → `click` with randomized client coordinate vectors.

---

## 🏛️ Production Automation Architectures (5 Options)

The workspace includes copyable, robust code templates explaining how to implement each of the five core automation patterns:

- **Option 1: Image Matching (Simplest)**: OpenCV template matching + pyautogui. Ideal for desktop apps & retro games.
- **Option 2: OCR-based Matching**: Character recognition via Tesseract. Best for elements with dynamic styles but static text.
- **Option 3: OS UI Automation**: Hooking native Windows accessibility trees via `pywinauto`. Reliable, works on hidden windows.
- **Option 4: Browser Automation**: Direct Chromium control with `Playwright`. Excellent for robust, multi-step web scraping.
- **Option 5: Real-Time Web Userscript**: Injection scripts (Tampermonkey) combining event-driven `MutationObserver` with `requestAnimationFrame` for maximum speed.

---

## 🛠️ Local Development & Build Setup

This project uses **Bun** as its package manager and runtime.

### Installation
```bash
bun install
```

### Run the Dev Server
```bash
__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=.com bun run dev --host 0.0.0.0 --port 3000
```
Open [http://localhost:3000/](http://localhost:3000/) in your browser.

### Compile Production Build
```bash
bun run build
```

---

## 📝 License
Educational Sandbox Simulation Project. Free to use, adapt, and build upon. Custom CAD/SAD template match engine copyright © 2026.
