import { useState, useEffect, useRef } from 'react';
import { type Target, findTemplateMatch } from './utils/matching';
import { DesktopSimulator } from './components/DesktopSimulator';
import { Dashboard } from './components/Dashboard';
import { HelpCircle, Sparkles, Cpu, X } from 'lucide-react';

export default function App() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [isTrainingPixel, setIsTrainingPixel] = useState(false);
  const [isTrainingBrowser, setIsTrainingBrowser] = useState(false);
  const [automationActive, setAutomationActive] = useState(false);
  const [scanInterval, setScanInterval] = useState(400); // scan frequency slider
  const [simulationSpeed] = useState(1);

  // Target cache to store ImageData of cropped templates directly
  const targetImageDataCache = useRef<Record<string, ImageData>>({});

  // Training Modal state
  const [trainingData, setTrainingData] = useState<{
    imgData: ImageData;
    x: number;
    y: number;
    w: number;
    h: number;
    dataUrl: string;
  } | null>(null);
  const [newTargetName, setNewTargetName] = useState('');
  const [newTargetConfidence, setNewTargetConfidence] = useState(85);
  const [newTargetCooldown, setNewTargetCooldown] = useState(5);
  const [newTargetSearch, setNewTargetSearch] = useState<'whole_screen' | 'region'>('whole_screen');

  // Logs state
  const [logs, setLogs] = useState<{ id: string; time: string; text: string; type: 'info' | 'success' | 'warning' | 'error' }[]>([]);

  const addLog = (text: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [
      ...prev,
      { id: Math.random().toString(), time, text, type },
    ].slice(-100)); // Limit to last 100 logs
  };

  const clearLogs = () => setLogs([]);

  // Pre-seed some default targets to make it instantly functional
  useEffect(() => {
    const createPreseededTargets = async () => {
      const preseeded: Target[] = [
        {
          id: 'dom-download',
          name: 'Web: Download Now Button',
          thumbnail: 'button#btn-download',
          width: 140,
          height: 36,
          trainedX: 0,
          trainedY: 0,
          clickOffsetX: 0,
          clickOffsetY: 0,
          confidenceThreshold: 90,
          cooldown: 4,
          searchArea: 'whole_screen',
          active: true,
          lastTriggered: 0,
        },
        {
          id: 'dom-continue',
          name: 'Web: Continue Button',
          thumbnail: 'button.action-continue',
          width: 140,
          height: 36,
          trainedX: 0,
          trainedY: 0,
          clickOffsetX: 0,
          clickOffsetY: 0,
          confidenceThreshold: 90,
          cooldown: 4,
          searchArea: 'whole_screen',
          active: true,
          lastTriggered: 0,
        },
        {
          id: 'dom-claim',
          name: 'Web: Claim Reward Button',
          thumbnail: 'a[href="/claim-cash"]',
          width: 150,
          height: 36,
          trainedX: 0,
          trainedY: 0,
          clickOffsetX: 0,
          clickOffsetY: 0,
          confidenceThreshold: 90,
          cooldown: 4,
          searchArea: 'whole_screen',
          active: true,
          lastTriggered: 0,
        },
      ];

      // Let's render the "OK (Accept)" dialog button into a pixel target
      const canvas = document.createElement('canvas');
      canvas.width = 90;
      canvas.height = 30;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        // Draw the exact same button as DesktopSimulator
        ctx.fillStyle = '#3b82f6';
        ctx.beginPath();
        ctx.roundRect(0, 0, 90, 30, 4);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('OK (Accept)', 45, 15);

        const imgData = ctx.getImageData(0, 0, 90, 30);
        const dataUrl = canvas.toDataURL();
        const okTarget: Target = {
          id: 'pixel-ok-accept',
          name: 'OS: Security Accept Button',
          thumbnail: dataUrl,
          width: 90,
          height: 30,
          trainedX: 455, // default spot in simulated OS
          trainedY: 170,
          clickOffsetX: 0,
          clickOffsetY: 0,
          confidenceThreshold: 85,
          cooldown: 6,
          searchArea: 'whole_screen',
          active: true,
          lastTriggered: 0,
        };

        targetImageDataCache.current[okTarget.id] = imgData;
        preseeded.push(okTarget);
      }

      setTargets(preseeded);
      addLog('Initialized system with pre-trained automation macros.', 'info');
    };

    createPreseededTargets();
  }, []);

  // Escape key handler to cancel training
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsTrainingPixel(false);
        setIsTrainingBrowser(false);
        setTrainingData(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Monitor Scan Loop
  useEffect(() => {
    if (!automationActive) return;

    const interval = setInterval(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) return;

      const sw = canvas.width;
      const sh = canvas.height;
      const screenData = ctx.getImageData(0, 0, sw, sh);
      const now = Date.now();

      // Scan all active targets
      for (const tgt of targets) {
        if (!tgt.active) continue;

        // Cooldown check
        if (now - tgt.lastTriggered < tgt.cooldown * 1000) {
          continue;
        }

        // 1. DOM Target matching
        if (tgt.id.startsWith('dom-')) {
          const isDownloadActive = tgt.id === 'dom-download' && (window as any).isBrowserStep(1);
          const isContinueActive = tgt.id === 'dom-continue' && (window as any).isBrowserStep(2);
          const isClaimActive = tgt.id === 'dom-claim' && (window as any).isBrowserStep(3);

          if (isDownloadActive || isContinueActive || isClaimActive) {
            // Find coordinates of target on simulated OS
            let cx = 0;
            let cy = 0;
            if (isDownloadActive) { cx = 230; cy = 348; }
            if (isContinueActive) { cx = 230; cy = 348; }
            if (isClaimActive) { cx = 235; cy = 348; }

            // Trigger automation action
            if (cx > 0) {
              tgt.lastTriggered = now;
              (window as any).triggerMockClick(cx, cy, tgt.name, 'rgb(37, 99, 235)');
              break; // click once per cycle
            }
          }
          continue;
        }

        // 2. Pixel Target matching (Using our optimized TS engine)
        const cachedImgData = targetImageDataCache.current[tgt.id];
        if (!cachedImgData) continue;

        const match = findTemplateMatch(
          screenData,
          cachedImgData,
          tgt.searchArea === 'region' ? tgt.regionBox : undefined
        );

        if (match && match.confidence >= tgt.confidenceThreshold) {
          // Match succeeded! Trigger virtual mouse click with offset
          const clickX = match.x + tgt.clickOffsetX;
          const clickY = match.y + tgt.clickOffsetY;

          // Start target cooldown
          tgt.lastTriggered = now;

          // Click on the simulator
          if ((window as any).triggerMockClick) {
            (window as any).triggerMockClick(clickX, clickY, tgt.name, 'rgb(168, 85, 247)');
          }

          break; // break so we process one action per scan frequency to behave naturally
        }
      }
    }, scanInterval);

    return () => clearInterval(interval);
  }, [automationActive, targets, scanInterval]);

  // Handle Training Capture
  const handleCaptureTemplate = (
    imgData: ImageData,
    x: number,
    y: number,
    w: number,
    h: number,
    dataUrl: string
  ) => {
    setIsTrainingPixel(false);
    setTrainingData({ imgData, x, y, w, h, dataUrl });
    setNewTargetName(`Target_Crop_${Math.floor(Math.random() * 900 + 100)}`);
    setNewTargetConfidence(85);
    setNewTargetCooldown(5);
    setNewTargetSearch('whole_screen');
  };

  // Handle Browser selector capture
  const handleBrowserElementSelected = (
    selector: string,
    text: string,
    x: number,
    y: number,
    w: number,
    h: number
  ) => {
    setIsTrainingBrowser(false);

    // Check if we already have this selector
    const id = `dom-${selector.replace(/[^a-zA-Z0-9]/g, '-')}`;
    if (targets.some((t) => t.id === id)) {
      addLog(`Web element macro [${selector}] already exists!`, 'warning');
      return;
    }

    const newTgt: Target = {
      id,
      name: `Web: "${text}"`,
      thumbnail: selector,
      width: w,
      height: h,
      trainedX: x,
      trainedY: y,
      clickOffsetX: 0,
      clickOffsetY: 0,
      confidenceThreshold: 90,
      cooldown: 4,
      searchArea: 'whole_screen',
      active: true,
      lastTriggered: 0,
    };

    setTargets((prev) => [...prev, newTgt]);
    addLog(`Successfully trained Web Element macro using CSS selector: ${selector}`, 'success');
  };

  // Save pixel trained target
  const handleSaveTrainedTarget = () => {
    if (!trainingData) return;

    const id = `pixel-${Date.now()}`;
    const newTarget: Target = {
      id,
      name: newTargetName.trim() || `Pixel Target ${targets.length + 1}`,
      thumbnail: trainingData.dataUrl,
      width: trainingData.w,
      height: trainingData.h,
      trainedX: trainingData.x,
      trainedY: trainingData.y,
      clickOffsetX: 0,
      clickOffsetY: 0,
      confidenceThreshold: newTargetConfidence,
      cooldown: newTargetCooldown,
      searchArea: newTargetSearch,
      regionBox:
        newTargetSearch === 'region'
          ? {
              x: Math.max(0, trainingData.x - 50),
              y: Math.max(0, trainingData.y - 50),
              w: trainingData.w + 100,
              h: trainingData.h + 100,
            }
          : undefined,
      active: true,
      lastTriggered: 0,
    };

    // Cache image data for pixel matching loop
    targetImageDataCache.current[id] = trainingData.imgData;

    setTargets((prev) => [...prev, newTarget]);
    setTrainingData(null);
    addLog(`Successfully trained new Pixel Match macro: ${newTarget.name}`, 'success');
  };

  // State interface bridges to DesktopSimulator steps
  useEffect(() => {
    (window as any).isBrowserStep = () => {
      return true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none antialiased">
      {/* Dynamic Background subtle grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-10 pointer-events-none"></div>

      {/* Header Bar */}
      <header className="relative border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-600/10 rounded-xl border border-purple-500/30">
            <Cpu className="w-6 h-6 text-purple-400 stroke-[1.5]" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-purple-400 bg-clip-text text-transparent m-0 leading-none">
              AutoClicker AI Workspace
            </h1>
            <p className="text-[11px] text-slate-500 font-medium mt-1 uppercase tracking-wider">
              Teach-and-Click Visual Macro Automation Platform
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-full font-mono">
            ENGINE: Dual-Pass SAD Core v1.4
          </span>
          <a
            href="#docs"
            className="text-xs text-slate-400 hover:text-slate-200 transition flex items-center gap-1.5"
          >
            <HelpCircle className="w-4 h-4 text-slate-500" />
            <span>Architecture & Specs</span>
          </a>
        </div>
      </header>

      {/* Main Container Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start relative z-10">

        {/* Left column: Desktop Simulator */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <DesktopSimulator
            onCaptureTemplate={handleCaptureTemplate}
            onBrowserElementSelected={handleBrowserElementSelected}
            isTrainingPixel={isTrainingPixel}
            isTrainingBrowser={isTrainingBrowser}
            onCancelTraining={() => {
              setIsTrainingPixel(false);
              setIsTrainingBrowser(false);
            }}
            activeTargets={targets}
            onTriggerClick={(x, y, label) => {
              addLog(`Manual clicked target: ${label} at [${x}, ${y}]`, 'info');
            }}
            automationActive={automationActive}
            simulationSpeed={simulationSpeed}
            addLog={addLog}
            resetSimulator={() => {}}
          />

          {/* Quick Start Guide */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex gap-4 items-start shadow-md">
            <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
              <Sparkles className="w-5 h-5 shrink-0" />
            </div>
            <div>
              <h3 className="font-bold text-xs text-slate-300 uppercase tracking-wide">
                Interactive Teaching Tutorial
              </h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                1. Look at the <strong>Coin Miner</strong> game or <strong>System Warning</strong> app inside the desktop. <br />
                2. Click <strong>"Teach Target (Pixel)"</strong>, then click-and-drag over the yellow <strong>"CLAIM REWARD!"</strong> button or the blue <strong>"OK"</strong> button. <br />
                3. Save the macro target. Then toggle <strong>"START MONITOR"</strong> to watch the automation automatically track, match, and click the targets in real-time as they move or appear!
              </p>
            </div>
          </div>
        </div>

        {/* Right column: Macro controller dashboard & docs */}
        <div className="lg:col-span-5 h-full flex flex-col">
          <Dashboard
            targets={targets}
            onToggleTargetActive={(id) => {
              setTargets((prev) =>
                prev.map((t) => (t.id === id ? { ...t, active: !t.active } : t))
              );
              const target = targets.find((t) => t.id === id);
              if (target) {
                addLog(`Toggled macro [${target.name}] to ${!target.active ? 'ACTIVE' : 'INACTIVE'}`, 'warning');
              }
            }}
            onDeleteTarget={(id) => {
              setTargets((prev) => prev.filter((t) => t.id !== id));
              delete targetImageDataCache.current[id];
              addLog(`Deleted trained macro target: ${id}`, 'error');
            }}
            onUpdateTargetThreshold={(id, val) => {
              setTargets((prev) =>
                prev.map((t) => (t.id === id ? { ...t, confidenceThreshold: val } : t))
              );
            }}
            onUpdateTargetSearchArea={(id, area) => {
              setTargets((prev) =>
                prev.map((t) =>
                  t.id === id
                    ? {
                        ...t,
                        searchArea: area,
                        regionBox:
                          area === 'region'
                            ? {
                                x: Math.max(0, t.trainedX - 60),
                                y: Math.max(0, t.trainedY - 60),
                                w: t.width + 120,
                                h: t.height + 120,
                              }
                            : undefined,
                      }
                    : t
                )
              );
              addLog(`Updated search region strategy for target macro.`, 'info');
            }}
            automationActive={automationActive}
            onToggleAutomation={() => {
              setAutomationActive((prev) => !prev);
              addLog(
                !automationActive
                  ? '▶️ Automation loop STARTED. Active macros are scanning screen memory...'
                  : '⏸️ Automation loop STOPPED. Scanning deactivated.',
                !automationActive ? 'success' : 'warning'
              );
            }}
            scanInterval={scanInterval}
            onUpdateScanInterval={setScanInterval}
            logs={logs}
            onClearLogs={clearLogs}
            onTeachPixel={() => {
              setIsTrainingBrowser(false);
              setIsTrainingPixel(true);
              addLog('Select crop region on the simulated OS desktop canvas.', 'info');
            }}
            onTeachBrowser={() => {
              setIsTrainingPixel(false);
              setIsTrainingBrowser(true);
              addLog('Hover over and click web elements inside mock browser to generate Playwright DOM queries.', 'info');
            }}
          />
        </div>
      </main>

      {/* Training Modal Overlay */}
      {trainingData && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal header */}
            <div className="bg-slate-950 px-5 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-purple-500 animate-pulse"></div>
                <h3 className="font-bold text-sm text-slate-100">CONFIGURE MACRO TARGET</h3>
              </div>
              <button
                onClick={() => setTrainingData(null)}
                className="text-slate-500 hover:text-slate-300 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal body */}
            <div className="p-5 space-y-4">
              <div className="flex items-center gap-4 bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="w-16 h-16 bg-slate-900 border border-slate-700 rounded flex items-center justify-center overflow-hidden shrink-0">
                  <img src={trainingData.dataUrl} alt="Crop" className="max-w-full max-h-full object-contain" />
                </div>
                <div className="text-xs space-y-1 text-slate-400">
                  <p>
                    <strong>Resolution:</strong> {trainingData.w}x{trainingData.h} px
                  </p>
                  <p>
                    <strong>Source coordinate:</strong> [{trainingData.x}, {trainingData.y}]
                  </p>
                </div>
              </div>

              {/* Input Name */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400">Macro Name:</label>
                <input
                  type="text"
                  value={newTargetName}
                  onChange={(e) => setNewTargetName(e.target.value)}
                  placeholder="e.g. OK Button"
                  className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-purple-500 transition"
                />
              </div>

              {/* Slider confidence */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-400">
                  <span>Confidence Threshold:</span>
                  <span className="text-purple-400">{newTargetConfidence}%</span>
                </div>
                <input
                  type="range"
                  min={50}
                  max={99}
                  value={newTargetConfidence}
                  onChange={(e) => setNewTargetConfidence(Number(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-500 leading-tight">
                  Lower confidence tolerates screen scaling, shadows, and subtle color variance. Higher confidence avoids false positives.
                </span>
              </div>

              {/* Cooldown slider */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-400">
                  <span>Cooldown timer:</span>
                  <span className="text-purple-400">{newTargetCooldown} seconds</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={newTargetCooldown}
                  onChange={(e) => setNewTargetCooldown(Number(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer"
                />
              </div>

              {/* Search strategy select */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400">Search Strategy:</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setNewTargetSearch('whole_screen')}
                    className={`px-3 py-2.5 rounded-lg text-xs font-semibold border transition text-center ${
                      newTargetSearch === 'whole_screen'
                        ? 'bg-purple-600/20 text-purple-400 border-purple-500'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    🔍 Whole Screen
                  </button>
                  <button
                    onClick={() => setNewTargetSearch('region')}
                    className={`px-3 py-2.5 rounded-lg text-xs font-semibold border transition text-center ${
                      newTargetSearch === 'region'
                        ? 'bg-purple-600/20 text-purple-400 border-purple-500'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                  >
                    🎯 Restricted Region (+-50px)
                  </button>
                </div>
              </div>
            </div>

            {/* Modal actions */}
            <div className="bg-slate-950 px-5 py-3.5 border-t border-slate-800 flex justify-end gap-2.5">
              <button
                onClick={() => setTrainingData(null)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTrainedTarget}
                className="px-4 py-1.5 rounded-lg text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-md transition"
              >
                Save Macro Target
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Info Footer */}
      <footer className="border-t border-slate-800/60 bg-slate-950 py-4 px-6 text-center text-xs text-slate-600 font-medium">
        AutoClicker AI is an interactive simulation educational tool. Created with Vite, React, Tailwind CSS and custom Sum-of-Absolute-Differences (SAD) block matching algorithm in pure TypeScript.
      </footer>
    </div>
  );
}
