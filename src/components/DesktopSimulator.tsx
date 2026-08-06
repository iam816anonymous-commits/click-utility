import React, { useRef, useEffect, useState } from 'react';
import type { Target } from '../utils/matching';
import { RotateCcw, Monitor } from 'lucide-react';

interface DesktopSimulatorProps {
  onCaptureTemplate: (imgData: ImageData, x: number, y: number, w: number, h: number, dataUrl: string) => void;
  onBrowserElementSelected: (selector: string, text: string, x: number, y: number, w: number, h: number) => void;
  isTrainingPixel: boolean;
  isTrainingBrowser: boolean;
  onCancelTraining: () => void;
  activeTargets: Target[];
  onTriggerClick: (x: number, y: number, label: string) => void;
  automationActive: boolean;
  simulationSpeed: number; // multiplier
  addLog: (msg: string, type: 'info' | 'success' | 'warning' | 'error') => void;
  // External triggers to interact with simulator state
  resetSimulator: () => void;
}

// Window state interface
interface AppWindow {
  id: string;
  title: string;
  x: number;
  y: number;
  w: number;
  h: number;
  icon: string;
}

export const DesktopSimulator: React.FC<DesktopSimulatorProps> = ({
  onCaptureTemplate,
  onBrowserElementSelected,
  isTrainingPixel,
  isTrainingBrowser,
  onCancelTraining,
  activeTargets,
  simulationSpeed,
  addLog,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // OS Simulated State
  const [windows, setWindows] = useState<AppWindow[]>([
    { id: 'game', title: 'Coin Miner (Idle Game)', x: 40, y: 50, w: 260, h: 220, icon: '🎮' },
    { id: 'admin', title: 'System Warning', x: 420, y: 70, w: 280, h: 150, icon: '⚠️' },
    { id: 'browser', title: 'Mock Browser - fast-rewards.mock', x: 120, y: 150, w: 460, h: 260, icon: '🌐' },
  ]);

  // Game App State
  const [coins, setCoins] = useState(120);
  const [claimButton, setClaimButton] = useState<{ x: number; y: number; w: number; h: number; visible: boolean; timer: number }>({
    x: 80,
    y: 110,
    w: 100,
    h: 30,
    visible: true,
    timer: 5000,
  });

  // Admin App State
  const [dialogStatus, setDialogStatus] = useState<'pending' | 'resolved' | 'rejected'>('pending');

  // Browser App State
  const [browserStep, setBrowserStep] = useState<1 | 2 | 3>(1); // Step 1: Download -> Step 2: Continue -> Step 3: Claim Reward

  // Mouse / Interaction State
  const [hoveredElement, setHoveredElement] = useState<string | null>(null);
  const [draggedWindow, setDraggedWindow] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Crop / Training State
  const [cropStart, setCropStart] = useState<{ x: number; y: number } | null>(null);
  const [cropCurrent, setCropCurrent] = useState<{ x: number; y: number } | null>(null);

  // Click ripple animations to show where macro clicked
  const [ripples, setRipples] = useState<{ id: string; x: number; y: number; progress: number; color: string; label?: string }[]>([]);

  // Simulation loop for background window activities
  useEffect(() => {
    let lastTime = Date.now();
    const interval = setInterval(() => {
      const now = Date.now();
      const dt = (now - lastTime) * simulationSpeed;
      lastTime = now;

      // 1. Game miner coins ticking
      setCoins((c) => c + Math.floor(dt * 0.005));

      // 2. Claim button spawn logic
      setClaimButton((prev) => {
        let nextTimer = prev.timer - dt;
        if (nextTimer <= 0) {
          // Toggle visibility or move
          const nextVisible = !prev.visible || Math.random() > 0.4;
          const rx = 15 + Math.random() * 120; // Bound within game window coordinates
          const ry = 80 + Math.random() * 80;
          return {
            x: rx,
            y: ry,
            w: 110,
            h: 32,
            visible: nextVisible,
            timer: nextVisible ? 4000 + Math.random() * 3000 : 2000 + Math.random() * 2000,
          };
        }
        return { ...prev, timer: nextTimer };
      });

      // 3. System alert spawn logic: if resolved, respawn after some time
      setDialogStatus((status) => {
        if (status !== 'pending') {
          // 15 seconds cooloff to respawn warning dialog
          const respawnChance = Math.random() * dt * 0.0001;
          if (respawnChance > 0.95) {
            return 'pending';
          }
        }
        return status;
      });

      // Update ripples
      setRipples((rList) =>
        rList
          .map((r) => ({ ...r, progress: r.progress + dt * 0.004 }))
          .filter((r) => r.progress < 1)
      );
    }, 100);

    return () => clearInterval(interval);
  }, [simulationSpeed]);

  // Expose local click trigger for the main control loop
  const triggerRipple = (x: number, y: number, color: string, label?: string) => {
    const id = Math.random().toString();
    setRipples((prev) => [...prev, { id, x, y, progress: 0, color, label }]);
  };

  // Canvas drawing loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return;

    // Clear background
    ctx.fillStyle = '#0f172a'; // dark slate blue wallpaper
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw stylish wallpaper elements (circuit/matrix theme)
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.5)';
    ctx.lineWidth = 1;
    for (let i = 0; i < canvas.width; i += 40) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, canvas.height);
      ctx.stroke();
    }
    for (let j = 0; j < canvas.height; j += 40) {
      ctx.beginPath();
      ctx.moveTo(0, j);
      ctx.lineTo(canvas.width, j);
      ctx.stroke();
    }

    // Floating background glowing circles
    ctx.fillStyle = 'rgba(56, 189, 248, 0.04)';
    ctx.beginPath();
    ctx.arc(150, 120, 100, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(192, 132, 252, 0.04)';
    ctx.beginPath();
    ctx.arc(600, 320, 150, 0, Math.PI * 2);
    ctx.fill();

    // Draw Windows
    windows.forEach((win) => {
      // Background & Shadow
      ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
      ctx.shadowBlur = 15;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 6;

      ctx.fillStyle = '#1e293b'; // Slate dark glass window
      ctx.beginPath();
      ctx.roundRect(win.x, win.y, win.w, win.h, 8);
      ctx.fill();

      // Reset shadows
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;

      // Window Header Border
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(win.x, win.y, win.w, win.h, 8);
      ctx.stroke();

      // Header Fill
      ctx.fillStyle = '#111827';
      ctx.beginPath();
      ctx.roundRect(win.x + 1, win.y + 1, win.w - 2, 28, [7, 7, 0, 0]);
      ctx.fill();

      // Header Title
      ctx.fillStyle = '#f1f5f9';
      ctx.font = 'bold 12px Inter, sans-serif';
      ctx.fillText(`${win.icon} ${win.title}`, win.x + 10, win.y + 18);

      // Window Control dots (mock Close, Minimize, Maximize)
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.arc(win.x + win.w - 15, win.y + 15, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#eab308';
      ctx.beginPath();
      ctx.arc(win.x + win.w - 27, win.y + 15, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#22c55e';
      ctx.beginPath();
      ctx.arc(win.x + win.w - 39, win.y + 15, 4, 0, Math.PI * 2);
      ctx.fill();

      // Window Content Area
      ctx.save();
      ctx.translate(win.x, win.y + 30);
      const cw = win.w;
      const ch = win.h - 30;

      // Render App Specific Content
      if (win.id === 'game') {
        // Coin Miner Game Window Content
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(4, 4, cw - 8, ch - 8);

        // Stats Panel
        ctx.fillStyle = 'rgba(34, 197, 94, 0.15)';
        ctx.fillRect(10, 10, cw - 20, 36);
        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 1;
        ctx.strokeRect(10, 10, cw - 20, 36);

        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 13px Courier, monospace';
        ctx.fillText(`COINS: $${coins.toLocaleString()}`, 20, 32);

        // Miner status
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Courier, monospace';
        ctx.fillText(`STATUS: MINING AT 2.5 H/S`, 20, 56);

        // Drawing Claim Button if visible
        if (claimButton.visible) {
          const bx = claimButton.x;
          const by = claimButton.y;
          const bw = claimButton.w;
          const bh = claimButton.h;

          // Glowing border for claiming
          ctx.strokeStyle = '#eab308';
          ctx.shadowColor = 'rgba(234, 179, 8, 0.4)';
          ctx.shadowBlur = 8;
          ctx.fillStyle = '#eab308';
          ctx.beginPath();
          ctx.roundRect(bx, by, bw, bh, 6);
          ctx.fill();
          ctx.shadowBlur = 0;

          // Text
          ctx.fillStyle = '#000000';
          ctx.font = 'bold 11px Arial, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('CLAIM REWARD!', bx + bw / 2, by + bh / 2 + 4);
          ctx.textAlign = 'left';
        } else {
          // Spinning hourglass indicator
          ctx.fillStyle = '#475569';
          ctx.font = '11px Arial, sans-serif';
          ctx.fillText('Waiting for next drop...', 20, 110);
        }
      } else if (win.id === 'admin') {
        // System Security Dialog Content
        ctx.fillStyle = '#111827';
        ctx.fillRect(4, 4, cw - 8, ch - 8);

        if (dialogStatus === 'pending') {
          // Warning Message
          ctx.fillStyle = '#f87171';
          ctx.font = '12px Arial, sans-serif';
          ctx.fillText('CRITICAL: Remote access request detected.', 15, 30);
          ctx.fillStyle = '#e2e8f0';
          ctx.font = '11px Arial, sans-serif';
          ctx.fillText('Authorize incoming system update?', 15, 48);

          // "OK" button
          const okX = 35;
          const okY = 70;
          const okW = 90;
          const okH = 30;

          ctx.fillStyle = '#3b82f6'; // Bright blue
          ctx.beginPath();
          ctx.roundRect(okX, okY, okW, okH, 4);
          ctx.fill();
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 11px Arial, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('OK (Accept)', okX + okW / 2, okY + okH / 2 + 4);

          // "Cancel" button
          const cX = 145;
          const cY = 70;
          const cW = 90;
          const cH = 30;

          ctx.fillStyle = '#ef4444'; // Red
          ctx.beginPath();
          ctx.roundRect(cX, cY, cW, cH, 4);
          ctx.fill();
          ctx.fillStyle = '#ffffff';
          ctx.fillText('Cancel', cX + cW / 2, cY + cH / 2 + 4);
          ctx.textAlign = 'left';
        } else {
          // Resolved state
          ctx.fillStyle = dialogStatus === 'resolved' ? '#4ade80' : '#f87171';
          ctx.font = 'bold 13px Arial, sans-serif';
          ctx.fillText(
            dialogStatus === 'resolved' ? '✓ UPDATE AUTHORIZED' : '✗ UPDATE REJECTED',
            40,
            50
          );
          ctx.fillStyle = '#64748b';
          ctx.font = '10px Arial, sans-serif';
          ctx.fillText('Autoreloading app in 8 seconds...', 40, 70);
        }
      } else if (win.id === 'browser') {
        // Mock Browser window content
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(4, 4, cw - 8, ch - 8);

        // Address Bar
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(10, 8, cw - 20, 24);
        ctx.strokeStyle = '#334155';
        ctx.strokeRect(10, 8, cw - 20, 24);

        ctx.fillStyle = '#a1a1aa';
        ctx.font = '10px Inter, Arial';
        ctx.fillText('🔒 https://fast-rewards.mock/claim', 20, 24);

        // Main Web View Content
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(10, 40, cw - 20, ch - 50);

        if (browserStep === 1) {
          // Step 1: Download Button
          ctx.fillStyle = '#f1f5f9';
          ctx.font = 'bold 14px Arial';
          ctx.fillText('Step 1: Download package', 30, 75);

          ctx.fillStyle = '#64748b';
          ctx.font = '11px Arial';
          ctx.fillText('Get the official client safely below.', 30, 95);

          // Download button
          const dX = 30;
          const dY = 120;
          const dW = 140;
          const dH = 36;

          // Drawing elements differently for CSS selector simulation
          ctx.fillStyle = '#059669'; // Emerald
          ctx.beginPath();
          ctx.roundRect(dX, dY, dW, dH, 6);
          ctx.fill();

          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Download Now', dX + dW / 2, dY + dH / 2 + 4);
          ctx.textAlign = 'left';
        } else if (browserStep === 2) {
          // Step 2: Continue Button
          ctx.fillStyle = '#f1f5f9';
          ctx.font = 'bold 14px Arial';
          ctx.fillText('Step 2: Install Complete', 30, 75);

          ctx.fillStyle = '#64748b';
          ctx.font = '11px Arial';
          ctx.fillText('Success! Click continue to proceed.', 30, 95);

          // Continue button
          const cX = 30;
          const cY = 120;
          const cW = 140;
          const cH = 36;

          ctx.fillStyle = '#2563eb'; // Indigo Blue
          ctx.beginPath();
          ctx.roundRect(cX, cY, cW, cH, 6);
          ctx.fill();

          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Continue', cX + cW / 2, cY + cH / 2 + 4);
          ctx.textAlign = 'left';
        } else {
          // Step 3: Claim Button
          ctx.fillStyle = '#f1f5f9';
          ctx.font = 'bold 14px Arial';
          ctx.fillText('Step 3: Collect Bonus', 30, 75);

          ctx.fillStyle = '#eab308';
          ctx.font = '11px Arial';
          ctx.fillText('Claim your $50.00 cash award instantly!', 30, 95);

          // Claim button
          const clX = 30;
          const clY = 120;
          const clW = 150;
          const clH = 36;

          ctx.fillStyle = '#d97706'; // Orange-amber
          ctx.beginPath();
          ctx.roundRect(clX, clY, clW, clH, 6);
          ctx.fill();

          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Claim Reward Now', clX + clW / 2, clY + clH / 2 + 4);
          ctx.textAlign = 'left';
        }
      }

      ctx.restore();
    });

    // Draw training / crop tool overlay
    if (isTrainingPixel && cropStart) {
      const cx = cropStart.x;
      const cy = cropStart.y;
      const curX = cropCurrent ? cropCurrent.x : cx;
      const curY = cropCurrent ? cropCurrent.y : cy;

      const rectX = Math.min(cx, curX);
      const rectY = Math.min(cy, curY);
      const rectW = Math.abs(cx - curX);
      const rectH = Math.abs(cy - curY);

      // Darken outside crop
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      ctx.fillRect(0, 0, canvas.width, rectY); // Top
      ctx.fillRect(0, rectY, rectX, rectH); // Left
      ctx.fillRect(rectX + rectW, rectY, canvas.width - (rectX + rectW), rectH); // Right
      ctx.fillRect(0, rectY + rectH, canvas.width, canvas.height - (rectY + rectH)); // Bottom

      // Crop Bounding Box Highlight
      ctx.strokeStyle = '#a855f7'; // Purple focus
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(rectX, rectY, rectW, rectH);
      ctx.setLineDash([]);

      // Width and Height labels
      if (rectW > 5 && rectH > 5) {
        ctx.fillStyle = '#a855f7';
        ctx.fillRect(rectX, rectY - 24, 80, 20);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Courier';
        ctx.fillText(`${rectW}x${rectH} px`, rectX + 6, rectY - 10);
      }
    }

    // Draw browser hover element highlight in Browser Automation Training mode
    if (isTrainingBrowser) {
      // We look for where the mouse is and draw selector borders
      const browserWin = windows.find((w) => w.id === 'browser');
      if (browserWin && hoveredElement) {
        // Highlight elements
        let elementBox: { x: number; y: number; w: number; h: number; selector: string } | null = null;
        const bx = browserWin.x + 10;
        const by = browserWin.y + 70; // Offset of content area

        if (hoveredElement === 'download' && browserStep === 1) {
          elementBox = { x: bx + 20, y: by + 90, w: 140, h: 36, selector: 'button#btn-download' };
        } else if (hoveredElement === 'continue' && browserStep === 2) {
          elementBox = { x: bx + 20, y: by + 90, w: 140, h: 36, selector: 'button.action-continue' };
        } else if (hoveredElement === 'claim-reward' && browserStep === 3) {
          elementBox = { x: bx + 20, y: by + 90, w: 150, h: 36, selector: 'a[href="/claim-cash"]' };
        }

        if (elementBox) {
          ctx.strokeStyle = '#3b82f6'; // Bright DOM blue
          ctx.lineWidth = 2.5;
          ctx.strokeRect(elementBox.x, elementBox.y, elementBox.w, elementBox.h);

          // Selector flag
          ctx.fillStyle = '#3b82f6';
          ctx.fillRect(elementBox.x, elementBox.y - 20, Math.min(220, ctx.measureText(elementBox.selector).width + 12), 20);
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 10px monospace';
          ctx.fillText(elementBox.selector, elementBox.x + 6, elementBox.y - 6);
        }
      }
    }

    // Draw active target search regions if toggled
    activeTargets.forEach((tgt) => {
      if (tgt.active && tgt.searchArea === 'region' && tgt.regionBox) {
        ctx.strokeStyle = 'rgba(234, 179, 8, 0.4)'; // Orange dash
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(tgt.regionBox.x, tgt.regionBox.y, tgt.regionBox.w, tgt.regionBox.h);
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(234, 179, 8, 0.6)';
        ctx.font = '9px Inter';
        ctx.fillText(`Region: ${tgt.name}`, tgt.regionBox.x + 4, tgt.regionBox.y + 12);
      }
    });

    // Draw automated click ripple animation
    ripples.forEach((rip) => {
      const radius = 5 + rip.progress * 35;
      const alpha = 1 - rip.progress;
      ctx.strokeStyle = rip.color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
      ctx.lineWidth = 3 * (1 - rip.progress);
      ctx.beginPath();
      ctx.arc(rip.x, rip.y, radius, 0, Math.PI * 2);
      ctx.stroke();

      // Outer ring
      ctx.strokeStyle = rip.color.replace(')', `, ${alpha * 0.4})`).replace('rgb', 'rgba');
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(rip.x, rip.y, radius + 8, 0, Math.PI * 2);
      ctx.stroke();

      // Display Label
      if (rip.label) {
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
        ctx.font = 'bold 10px Courier New';
        ctx.shadowColor = 'black';
        ctx.shadowBlur = 4;
        ctx.fillText(`🤖 [AUTOCLICK] ${rip.label}`, rip.x + radius + 4, rip.y + 4);
        ctx.shadowBlur = 0;
      }
    });
  }, [windows, coins, claimButton, dialogStatus, browserStep, isTrainingPixel, isTrainingBrowser, cropStart, cropCurrent, hoveredElement, activeTargets, ripples]);

  // Window Focus Helpers
  const bringToFront = (id: string) => {
    setWindows((prev) => {
      const target = prev.find((w) => w.id === id);
      if (!target) return prev;
      const filtered = prev.filter((w) => w.id !== id);
      return [...filtered, target];
    });
  };

  // Click handler
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Handle Training Crops
    if (isTrainingPixel) {
      setCropStart({ x: mx, y: my });
      setCropCurrent({ x: mx, y: my });
      return;
    }

    // Handle Browser Element Selection
    if (isTrainingBrowser) {
      const browserWin = windows.find((w) => w.id === 'browser');
      if (browserWin && hoveredElement) {
        const bx = browserWin.x + 10;
        const by = browserWin.y + 70;

        let selected = null;
        if (hoveredElement === 'download' && browserStep === 1) {
          selected = {
            selector: 'button#btn-download',
            text: 'Download Now',
            x: bx + 20,
            y: by + 90,
            w: 140,
            h: 36,
          };
        } else if (hoveredElement === 'continue' && browserStep === 2) {
          selected = {
            selector: 'button.action-continue',
            text: 'Continue',
            x: bx + 20,
            y: by + 90,
            w: 140,
            h: 36,
          };
        } else if (hoveredElement === 'claim-reward' && browserStep === 3) {
          selected = {
            selector: 'a[href="/claim-cash"]',
            text: 'Claim Reward Now',
            x: bx + 20,
            y: by + 90,
            w: 150,
            h: 36,
          };
        }

        if (selected) {
          onBrowserElementSelected(selected.selector, selected.text, selected.x, selected.y, selected.w, selected.h);
          return;
        }
      }
      onCancelTraining();
      return;
    }

    // Check click targets from top to bottom (reverse windows order)
    const reversedWins = [...windows].reverse();
    let clickedInsideWindow = false;

    for (const win of reversedWins) {
      // Check Header Drag Bar click
      if (mx >= win.x && mx <= win.x + win.w && my >= win.y && my <= win.y + 30) {
        bringToFront(win.id);
        setDraggedWindow(win.id);
        setDragOffset({ x: mx - win.x, y: my - win.y });
        clickedInsideWindow = true;
        break;
      }

      // Check Window content click
      if (mx >= win.x && mx <= win.x + win.w && my >= win.y + 30 && my <= win.y + win.h) {
        bringToFront(win.id);
        clickedInsideWindow = true;

        // Coordinates relative to application window content area
        const rx = mx - win.x;
        const ry = my - (win.y + 30);

        // App Game elements
        if (win.id === 'game') {
          if (claimButton.visible && rx >= claimButton.x && rx <= claimButton.x + claimButton.w && ry >= claimButton.y && ry <= claimButton.y + claimButton.h) {
            // Click claim button!
            setCoins((c) => c + 500);
            setClaimButton((prev) => ({ ...prev, visible: false }));
            triggerRipple(mx, my, 'rgb(234, 179, 8)');
            addLog('Successfully claimed $500 idle coins manually!', 'success');
          }
        }

        // App Admin Alert dialog
        if (win.id === 'admin' && dialogStatus === 'pending') {
          // Check Accept Button
          if (rx >= 35 && rx <= 125 && ry >= 70 && ry <= 100) {
            setDialogStatus('resolved');
            triggerRipple(mx, my, 'rgb(34, 197, 94)');
            addLog('System update accepted manually.', 'info');
            setTimeout(() => {
              setDialogStatus('pending');
              addLog('Security warning alert recycled.', 'warning');
            }, 8000);
          }
          // Check Reject Button
          if (rx >= 145 && rx <= 235 && ry >= 70 && ry <= 100) {
            setDialogStatus('rejected');
            triggerRipple(mx, my, 'rgb(239, 68, 68)');
            addLog('System update rejected manually.', 'error');
            setTimeout(() => {
              setDialogStatus('pending');
            }, 8000);
          }
        }

        // App Browser element triggers
        if (win.id === 'browser') {
          const bx = 10;
          const by = 40;

          // Elements are located at content-relative: bx + 20, by + 90
          if (browserStep === 1) {
            const bxStart = bx + 20;
            const byStart = by + 80;
            if (rx >= bxStart && rx <= bxStart + 140 && ry >= byStart && ry <= byStart + 36) {
              setBrowserStep(2);
              triggerRipple(mx, my, 'rgb(5, 150, 105)');
              addLog('Browser Step 1: Package downloaded successfully.', 'success');
            }
          } else if (browserStep === 2) {
            const bxStart = bx + 20;
            const byStart = by + 80;
            if (rx >= bxStart && rx <= bxStart + 140 && ry >= byStart && ry <= byStart + 36) {
              setBrowserStep(3);
              triggerRipple(mx, my, 'rgb(37, 99, 235)');
              addLog('Browser Step 2: Installer continued.', 'info');
            }
          } else if (browserStep === 3) {
            const bxStart = bx + 20;
            const byStart = by + 80;
            if (rx >= bxStart && rx <= bxStart + 150 && ry >= byStart && ry <= byStart + 36) {
              setBrowserStep(1);
              triggerRipple(mx, my, 'rgb(217, 119, 6)');
              addLog('Browser Step 3: Cash Reward claimed successfully!', 'success');
            }
          }
        }

        break;
      }
    }

    if (!clickedInsideWindow) {
      // Wallpaper empty click
      triggerRipple(mx, my, 'rgb(56, 189, 248)');
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    // Window Dragging logic
    if (draggedWindow) {
      setWindows((prev) =>
        prev.map((w) =>
          w.id === draggedWindow
            ? {
                ...w,
                x: Math.max(0, Math.min(canvas.width - w.w, mx - dragOffset.x)),
                y: Math.max(0, Math.min(canvas.height - w.h, my - dragOffset.y)),
              }
            : w
        )
      );
      return;
    }

    // Training crops tracker
    if (isTrainingPixel && cropStart) {
      setCropCurrent({ x: mx, y: my });
      return;
    }

    // Hover detection inside applications
    let foundHover: string | null = null;
    windows.forEach((win) => {
      if (mx >= win.x && mx <= win.x + win.w && my >= win.y + 30 && my <= win.y + win.h) {
        const rx = mx - win.x;
        const ry = my - (win.y + 30);

        if (win.id === 'browser') {
          const bx = 10;
          const by = 40;
          const bxStart = bx + 20;
          const byStart = by + 80;

          if (browserStep === 1 && rx >= bxStart && rx <= bxStart + 140 && ry >= byStart && ry <= byStart + 36) {
            foundHover = 'download';
          } else if (browserStep === 2 && rx >= bxStart && rx <= bxStart + 140 && ry >= byStart && ry <= byStart + 36) {
            foundHover = 'continue';
          } else if (browserStep === 3 && rx >= bxStart && rx <= bxStart + 150 && ry >= byStart && ry <= byStart + 36) {
            foundHover = 'claim-reward';
          }
        }
      }
    });

    setHoveredElement(foundHover);
  };

  const handleMouseUp = () => {
    setDraggedWindow(null);

    // Finalize pixel training box
    if (isTrainingPixel && cropStart && cropCurrent) {
      const cx = cropStart.x;
      const cy = cropStart.y;
      const curX = cropCurrent.x;
      const curY = cropCurrent.y;

      const rectX = Math.floor(Math.min(cx, curX));
      const rectY = Math.floor(Math.min(cy, curY));
      const rectW = Math.floor(Math.abs(cx - curX));
      const rectH = Math.floor(Math.abs(cy - curY));

      setCropStart(null);
      setCropCurrent(null);

      if (rectW > 5 && rectH > 5) {
        // Capture image from canvas
        const canvas = canvasRef.current;
        if (canvas) {
          const tempCanvas = document.createElement('canvas');
          tempCanvas.width = rectW;
          tempCanvas.height = rectH;
          const tempCtx = tempCanvas.getContext('2d');
          const mainCtx = canvas.getContext('2d');

          if (tempCtx && mainCtx) {
            const imgData = mainCtx.getImageData(rectX, rectY, rectW, rectH);
            tempCtx.putImageData(imgData, 0, 0);
            const dataUrl = tempCanvas.toDataURL();
            onCaptureTemplate(imgData, rectX, rectY, rectW, rectH, dataUrl);
          }
        }
      } else {
        onCancelTraining();
      }
    }
  };

  // Expose triggers directly via state binding
  useEffect(() => {
    // We bind a function globally on the window or similar for triggering clicks visually
    (window as any).triggerMockClick = (x: number, y: number, label: string, color?: string) => {
      // Simulate click trigger in OS
      const canvas = canvasRef.current;
      if (!canvas) return;

      // Add ripple
      triggerRipple(x, y, color || 'rgb(34, 197, 94)', label);

      // Programmatically check if that click lands on active buttons to update application state
      windows.forEach((win) => {
        if (x >= win.x && x <= win.x + win.w && y >= win.y + 30 && y <= win.y + win.h) {
          const rx = x - win.x;
          const ry = y - (win.y + 30);

          if (win.id === 'game') {
            if (claimButton.visible && rx >= claimButton.x && rx <= claimButton.x + claimButton.w && ry >= claimButton.y && ry <= claimButton.y + claimButton.h) {
              setCoins((c) => c + 500);
              setClaimButton((prev) => ({ ...prev, visible: false }));
              addLog(`🤖 Macro matched & automatically clicked Claim Button at [${Math.floor(x)}, ${Math.floor(y)}]!`, 'success');
            }
          }

          if (win.id === 'admin' && dialogStatus === 'pending') {
            // Check Accept Button
            if (rx >= 35 && rx <= 125 && ry >= 70 && ry <= 100) {
              setDialogStatus('resolved');
              addLog(`🤖 Macro matched & automatically resolved critical security alert.`, 'success');
              setTimeout(() => {
                setDialogStatus('pending');
              }, 8000);
            }
          }

          if (win.id === 'browser') {
            const bx = 10;
            const by = 40;
            const bxStart = bx + 20;
            const byStart = by + 80;

            if (browserStep === 1 && rx >= bxStart && rx <= bxStart + 140 && ry >= byStart && ry <= byStart + 36) {
              setBrowserStep(2);
              addLog(`🤖 Auto-Automation step 1: Clicked "Download Now" via CSS Selector!`, 'success');
            } else if (browserStep === 2 && rx >= bxStart && rx <= bxStart + 140 && ry >= byStart && ry <= byStart + 36) {
              setBrowserStep(3);
              addLog(`🤖 Auto-Automation step 2: Clicked "Continue" via CSS Selector!`, 'success');
            } else if (browserStep === 3 && rx >= bxStart && rx <= bxStart + 150 && ry >= byStart && ry <= byStart + 36) {
              setBrowserStep(1);
              addLog(`🤖 Auto-Automation step 3: Clicked "Claim Reward" via CSS Selector!`, 'success');
            }
          }
        }
      });
    };

    return () => {
      delete (window as any).triggerMockClick;
    };
  }, [windows, claimButton, dialogStatus, browserStep]);

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl">
      {/* Top OS Header panel */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950 border-b border-slate-800 text-xs text-slate-400">
        <div className="flex items-center gap-2 font-semibold text-slate-300">
          <Monitor className="w-4 h-4 text-purple-400" />
          <span>SIMULATED DESKTOP SANDBOX (800x500)</span>
          <span className="bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded text-[10px] font-mono animate-pulse">
            LIVE SCREEN
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[10px] font-mono text-slate-400">FPS: 30</span>
          </div>
          <button
            onClick={() => {
              // Quick reset
              setCoins(120);
              setBrowserStep(1);
              setDialogStatus('pending');
              setWindows([
                { id: 'game', title: 'Coin Miner (Idle Game)', x: 40, y: 50, w: 260, h: 220, icon: '🎮' },
                { id: 'admin', title: 'System Warning', x: 420, y: 70, w: 280, h: 150, icon: '⚠️' },
                { id: 'browser', title: 'Mock Browser - fast-rewards.mock', x: 120, y: 150, w: 460, h: 260, icon: '🌐' },
              ]);
              addLog('Reset all simulator application windows and counters.', 'info');
            }}
            className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset OS</span>
          </button>
        </div>
      </div>

      {/* Actual canvas */}
      <div className="relative cursor-default select-none overflow-hidden mx-auto">
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className={`block max-w-full ${
            isTrainingPixel || isTrainingBrowser ? 'cursor-crosshair' : 'cursor-default'
          }`}
        />

        {/* Floating crosshair prompt overlay */}
        {(isTrainingPixel || isTrainingBrowser) && (
          <div className="absolute top-3 left-1/2 transform -translate-x-1/2 bg-purple-600/95 backdrop-blur border border-purple-400 text-white text-xs px-4 py-2.5 rounded-full flex items-center gap-2 shadow-lg animate-bounce pointer-events-none z-10">
            <span className="font-bold">
              {isTrainingPixel ? '🎯 Pixel Capture Mode' : '🌐 CSS Selector Mode'}
            </span>
            <span className="opacity-80">
              {isTrainingPixel
                ? 'Click & drag a rectangle on any element to teach'
                : 'Hover and click a browser element'}
            </span>
            <div className="bg-purple-800 px-2 py-0.5 rounded text-[10px] text-purple-200 font-mono">
              ESC to cancel
            </div>
          </div>
        )}
      </div>

      {/* Taskbar info */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-t border-slate-800 text-[11px] text-slate-500">
        <div className="flex gap-4">
          <span>Active Windows: {windows.length}</span>
          <span>Game Coins: ${coins}</span>
          <span>Security Dialog: <strong className={dialogStatus === 'pending' ? 'text-amber-500' : 'text-emerald-500'}>{dialogStatus.toUpperCase()}</strong></span>
        </div>
        <div className="font-mono text-slate-400">
          OS-Time: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};
