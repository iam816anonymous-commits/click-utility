import React, { useState } from 'react';
import type { Target } from '../utils/matching';
import { Play, Pause, Trash2, Settings, Terminal, BookOpen, HelpCircle, ToggleLeft, ToggleRight, Check, Copy } from 'lucide-react';

interface DashboardProps {
  targets: Target[];
  onToggleTargetActive: (id: string) => void;
  onDeleteTarget: (id: string) => void;
  onUpdateTargetThreshold: (id: string, threshold: number) => void;
  onUpdateTargetSearchArea: (id: string, area: 'whole_screen' | 'region') => void;
  automationActive: boolean;
  onToggleAutomation: () => void;
  scanInterval: number;
  onUpdateScanInterval: (val: number) => void;
  logs: { id: string; time: string; text: string; type: 'info' | 'success' | 'warning' | 'error' }[];
  onClearLogs: () => void;
  onTeachPixel: () => void;
  onTeachBrowser: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  targets,
  onToggleTargetActive,
  onDeleteTarget,
  onUpdateTargetThreshold,
  onUpdateTargetSearchArea,
  automationActive,
  onToggleAutomation,
  scanInterval,
  onUpdateScanInterval,
  logs,
  onClearLogs,
  onTeachPixel,
  onTeachBrowser,
}) => {
  const [activeTab, setActiveTab] = useState<'manager' | 'logs' | 'docs'>('manager');
  const [selectedSnippet, setSelectedSnippet] = useState<'python-cv' | 'python-ocr' | 'python-win' | 'playwright'>('python-cv');
  const [copied, setCopied] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const snippets = {
    'python-cv': `import cv2
import mss
import numpy as np
import pyautogui
import time

# Option 1: OpenCV Template Matching (Fast Desktop Automation)
def auto_click_target(template_path, threshold=0.85):
    # Load cropped target image
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    th, tw = template.shape[:2]

    # Initialize ultra-fast Screen Capture (MSS)
    with mss.mss() as sct:
        monitor = sct.monitors[1] # Primary monitor
        print("[*] Monitoring screen for target...")

        while True:
            # Capture full screen
            screenshot = np.array(sct.grab(monitor))
            # Convert BGRA to BGR for OpenCV
            screen_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

            # Perform Template Matching
            result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # Check confidence
            if max_val >= threshold:
                # Find center offset of target
                click_x = max_loc[0] + tw // 2
                click_y = max_loc[1] + th // 2

                print(f"[+] Found target! Conf: {max_val:.2f}. Clicking [{click_x}, {click_y}]")
                pyautogui.click(click_x, click_y)

                # Cooldown to avoid double clicks
                time.sleep(5)

            time.sleep(0.2) # Scan 5 times per second

if __name__ == "__main__":
    auto_click_target("accept_button.png", threshold=0.90)`,

    'python-ocr': `import cv2
import mss
import numpy as np
import pyautogui
import pytesseract # Requires Tesseract-OCR binary
import time

# Option 2: OCR Text-based Automation
def click_button_with_text(target_text, region=None):
    with mss.mss() as sct:
        monitor = sct.monitors[1]

        while True:
            # Capture screen / region
            img = np.array(sct.grab(monitor))
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

            # Run Tesseract OCR to find bounding boxes of words
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
            n_boxes = len(data['text'])

            for i in range(n_boxes):
                word = data['text'][i].strip()
                if target_text.lower() in word.lower():
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]

                    # Compute center of text
                    click_x = x + w // 2
                    click_y = y + h // 2

                    print(f"[+] Found text '{word}'! Clicking [{click_x}, {click_y}]")
                    pyautogui.click(click_x, click_y)
                    time.sleep(5) # Cooldown
                    break

            time.sleep(0.5)`,

    'python-win': `import time
from pywinauto import Application

# Option 3: Native Windows UI Automation
def automate_windows_app():
    print("[*] Hooking into system window...")
    # Connect to a running Windows application by title
    app = Application(backend="uia").connect(title_re=".*System Warning.*")

    # Locate the dialog element
    dialog = app.window(title_re=".*System Warning.*")

    while True:
        try:
            # Look up element directly from OS accessibility API
            ok_button = dialog.child_window(title="OK", control_type="Button")

            if ok_button.exists(timeout=1):
                print("[+] OK Button appeared! Performing native click action.")
                ok_button.click()
                time.sleep(5)
        except Exception as e:
            # Element not visible or active
            pass

        time.sleep(0.5)`,

    'playwright': `import asyncio
from playwright.async_api import async_playwright

# Option 4: Browser Automation (Direct DOM queries)
async def run_browser_macro():
    async with async_playwright() as p:
        # Launch real headful/headless Chromium instance
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://fast-rewards.mock/claim")
        print("[*] Monitoring web portal elements...")

        while True:
            try:
                # 1. Automate Step 1 (Download Now)
                download_btn = page.locator("button#btn-download")
                if await download_btn.is_visible(timeout=500):
                    print("[+] Found Download Button. Clicking...")
                    await download_btn.click()
                    continue

                # 2. Automate Step 2 (Continue)
                continue_btn = page.locator("button.action-continue")
                if await continue_btn.is_visible(timeout=500):
                    print("[+] Found Continue Button. Clicking...")
                    await continue_btn.click()
                    continue

                # 3. Automate Step 3 (Claim Cash Reward)
                claim_btn = page.locator('a[href="/claim-cash"]')
                if await claim_btn.is_visible(timeout=500):
                    print("[+] Claim Button active. Collecting bonus!")
                    await claim_btn.click()
                    continue

            except Exception:
                pass

            await asyncio.sleep(0.5)

asyncio.run(run_browser_macro())`
  };

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl h-full">
      {/* Control Panel Headers */}
      <div className="bg-slate-950 p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleAutomation}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-semibold transition shadow-md cursor-pointer ${
              automationActive
                ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white'
            }`}
          >
            {automationActive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{automationActive ? 'STOP MONITOR' : 'START MONITOR'}</span>
          </button>

          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-3 py-1.5 rounded-lg">
            <span className="text-xs text-slate-400 font-medium">Scan Frequency:</span>
            <span className="text-xs font-mono text-purple-400 font-bold">{(1000 / scanInterval).toFixed(1)}Hz</span>
            <input
              type="range"
              min={100}
              max={2000}
              step={100}
              value={scanInterval}
              onChange={(e) => onUpdateScanInterval(Number(e.target.value))}
              className="w-20 accent-purple-500 cursor-pointer"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onTeachPixel}
            disabled={automationActive}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              automationActive
                ? 'bg-slate-800/50 text-slate-500 border-slate-800 cursor-not-allowed'
                : 'bg-purple-600/10 text-purple-400 border-purple-500/30 hover:bg-purple-600/20'
            }`}
          >
            <span className="text-sm">🎯</span>
            <span>Teach Target (Pixel)</span>
          </button>
          <button
            onClick={onTeachBrowser}
            disabled={automationActive}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border transition cursor-pointer ${
              automationActive
                ? 'bg-slate-800/50 text-slate-500 border-slate-800 cursor-not-allowed'
                : 'bg-blue-600/10 text-blue-400 border-blue-500/30 hover:bg-blue-600/20'
            }`}
          >
            <span className="text-sm">🌐</span>
            <span>Teach Web Element</span>
          </button>
        </div>
      </div>

      {/* Workspace Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-950 px-2">
        <button
          onClick={() => setActiveTab('manager')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-bold transition-all relative ${
            activeTab === 'manager'
              ? 'text-purple-400 border-b-2 border-purple-500 bg-slate-900/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Settings className="w-4 h-4" />
          <span>TARGET MANAGER ({targets.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-bold transition-all relative ${
            activeTab === 'logs'
              ? 'text-purple-400 border-b-2 border-purple-500 bg-slate-900/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Terminal className="w-4 h-4" />
          <span>LIVE SCAN LOGS</span>
          {logs.length > 0 && (
            <span className="bg-red-500 text-white font-bold rounded-full px-1.5 py-0.5 text-[9px] min-w-4 text-center">
              {logs.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('docs')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-bold transition-all relative ${
            activeTab === 'docs'
              ? 'text-purple-400 border-b-2 border-purple-500 bg-slate-900/40'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>PRODUCTION IMPLEMENTATION SNIPPETS</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 min-h-[350px]">
        {activeTab === 'manager' && (
          <div className="flex flex-col gap-4">
            {targets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center text-slate-500 gap-3 border border-dashed border-slate-800 rounded-xl">
                <HelpCircle className="w-12 h-12 text-slate-600 stroke-[1.5]" />
                <div>
                  <p className="font-semibold text-slate-400">No macro targets trained yet.</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm">
                    Click "Teach Target" above to select elements on the Simulated Desktop and watch them click automatically!
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {targets.map((tgt) => (
                  <div
                    key={tgt.id}
                    className={`border rounded-xl p-4 flex flex-col justify-between transition ${
                      tgt.active
                        ? 'bg-slate-900/70 border-slate-700/80 shadow-md'
                        : 'bg-slate-950/40 border-slate-800/60 opacity-60'
                    }`}
                  >
                    <div>
                      {/* Top bar info */}
                      <div className="flex items-start justify-between gap-2 mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 bg-slate-950 rounded border border-slate-700 flex items-center justify-center overflow-hidden shrink-0">
                            {tgt.thumbnail.startsWith('data:') ? (
                              <img src={tgt.thumbnail} alt={tgt.name} className="max-w-full max-h-full object-contain" />
                            ) : (
                              <span className="text-xs font-mono text-blue-400 font-bold">{tgt.thumbnail}</span>
                            )}
                          </div>
                          <div>
                            <h4 className="font-bold text-sm text-slate-200 leading-tight flex items-center gap-1.5">
                              {tgt.name}
                            </h4>
                            <span className="text-[10px] font-mono text-slate-500 block mt-0.5">
                              {tgt.id.startsWith('dom-') ? `DOM Selector automation` : `Image Match • ${tgt.width}x${tgt.height} px`}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => onToggleTargetActive(tgt.id)}
                            className="text-slate-400 hover:text-white transition"
                            title={tgt.active ? 'Disable macro' : 'Enable macro'}
                          >
                            {tgt.active ? (
                              <ToggleRight className="w-8 h-8 text-purple-400" />
                            ) : (
                              <ToggleLeft className="w-8 h-8 text-slate-600" />
                            )}
                          </button>
                          <button
                            onClick={() => onDeleteTarget(tgt.id)}
                            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-red-400 transition"
                            title="Delete target"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Configurations for Targets */}
                      {!tgt.id.startsWith('dom-') && (
                        <div className="space-y-3 pt-2 border-t border-slate-800">
                          {/* Confidence Slider */}
                          <div className="flex flex-col gap-1">
                            <div className="flex justify-between text-[11px] font-medium text-slate-400">
                              <span>Min Match Confidence:</span>
                              <span className="text-purple-400 font-bold">{tgt.confidenceThreshold}%</span>
                            </div>
                            <input
                              type="range"
                              min={50}
                              max={99}
                              value={tgt.confidenceThreshold}
                              onChange={(e) => onUpdateTargetThreshold(tgt.id, Number(e.target.value))}
                              className="w-full accent-purple-500 h-1 rounded"
                            />
                          </div>

                          {/* Search Region selector */}
                          <div className="flex items-center justify-between text-[11px] font-medium text-slate-400">
                            <span>Search Area:</span>
                            <div className="flex gap-1 bg-slate-950 p-0.5 rounded border border-slate-800">
                              <button
                                onClick={() => onUpdateTargetSearchArea(tgt.id, 'whole_screen')}
                                className={`px-2 py-1 rounded text-[10px] transition ${
                                  tgt.searchArea === 'whole_screen'
                                    ? 'bg-purple-600 text-white font-bold'
                                    : 'hover:text-slate-200'
                                }`}
                              >
                                Full Screen
                              </button>
                              <button
                                onClick={() => onUpdateTargetSearchArea(tgt.id, 'region')}
                                className={`px-2 py-1 rounded text-[10px] transition ${
                                  tgt.searchArea === 'region'
                                    ? 'bg-purple-600 text-white font-bold'
                                    : 'hover:text-slate-200'
                                }`}
                              >
                                Restricted Box
                              </button>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* DOM Automator configs info */}
                      {tgt.id.startsWith('dom-') && (
                        <div className="text-[11px] text-slate-400 space-y-1 bg-blue-950/20 border border-blue-900/30 p-2.5 rounded-lg mt-2">
                          <div className="flex justify-between">
                            <span>Query Method:</span>
                            <span className="font-mono text-blue-400">playwright.locator()</span>
                          </div>
                          <div className="flex justify-between">
                            <span>CSS Selector:</span>
                            <span className="font-mono text-slate-300 truncate max-w-[160px]" title={tgt.thumbnail}>
                              {tgt.thumbnail}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="mt-4 pt-2 border-t border-slate-800 flex justify-between items-center text-[10px] text-slate-500 font-mono">
                      <span>Cooldown: {tgt.cooldown}s</span>
                      <span>
                        Last Trigger:{' '}
                        {tgt.lastTriggered > 0
                          ? new Date(tgt.lastTriggered).toLocaleTimeString()
                          : 'Never'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="flex flex-col gap-3 h-full">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 font-mono">
                Real-time scanning activity (10-20 scans/sec when running)
              </span>
              <button
                onClick={onClearLogs}
                className="text-[11px] font-semibold text-purple-400 hover:text-purple-300 transition"
              >
                Clear console
              </button>
            </div>

            <div className="flex-1 bg-slate-950 rounded-xl p-3 font-mono text-xs overflow-y-auto border border-slate-800 h-[280px]">
              {logs.length === 0 ? (
                <div className="text-slate-600 h-full flex items-center justify-center text-center italic">
                  <span>Console Idle. Start monitoring to stream logs...</span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {logs.slice().reverse().map((log) => {
                    let color = 'text-slate-400';
                    if (log.type === 'success') color = 'text-emerald-400';
                    if (log.type === 'warning') color = 'text-amber-400';
                    if (log.type === 'error') color = 'text-red-400';

                    return (
                      <div key={log.id} className="flex gap-2 items-start leading-relaxed border-b border-slate-900 pb-1">
                        <span className="text-slate-600 shrink-0 select-none">[{log.time}]</span>
                        <span className={color}>{log.text}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'docs' && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-400">
              Depending on your specific application environment, choose the best automation architecture option to run in production. Here is clean, production-ready source code for each of the 4 options discussed.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <button
                onClick={() => setSelectedSnippet('python-cv')}
                className={`px-3 py-2 rounded-lg text-xs font-semibold border transition text-center ${
                  selectedSnippet === 'python-cv'
                    ? 'bg-purple-600/25 text-purple-400 border-purple-500'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                1. Image Match (OpenCV)
              </button>
              <button
                onClick={() => setSelectedSnippet('python-ocr')}
                className={`px-3 py-2 rounded-lg text-xs font-semibold border transition text-center ${
                  selectedSnippet === 'python-ocr'
                    ? 'bg-purple-600/25 text-purple-400 border-purple-500'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                2. OCR (Tesseract)
              </button>
              <button
                onClick={() => setSelectedSnippet('python-win')}
                className={`px-3 py-2 rounded-lg text-xs font-semibold border transition text-center ${
                  selectedSnippet === 'python-win'
                    ? 'bg-purple-600/25 text-purple-400 border-purple-500'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                3. UI Automation (Native)
              </button>
              <button
                onClick={() => setSelectedSnippet('playwright')}
                className={`px-3 py-2 rounded-lg text-xs font-semibold border transition text-center ${
                  selectedSnippet === 'playwright'
                    ? 'bg-purple-600/25 text-purple-400 border-purple-500'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                4. Browser (Playwright)
              </button>
            </div>

            <div className="relative bg-slate-950 border border-slate-800 rounded-xl overflow-hidden p-3 text-xs leading-relaxed max-h-[380px] overflow-y-auto font-mono text-slate-300">
              <div className="absolute right-3 top-3 z-10">
                <button
                  onClick={() => copyToClipboard(snippets[selectedSnippet])}
                  className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1 transition"
                  title="Copy code"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <pre className="whitespace-pre overflow-x-auto tab-size-4 pr-16">{snippets[selectedSnippet]}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
