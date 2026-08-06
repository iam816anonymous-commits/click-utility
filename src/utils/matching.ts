export interface Target {
  id: string;
  name: string;
  thumbnail: string; // data URI
  width: number;
  height: number;
  trainedX: number;
  trainedY: number;
  clickOffsetX: number; // relative to center
  clickOffsetY: number; // relative to center
  confidenceThreshold: number; // 0 to 100
  cooldown: number; // in seconds
  searchArea: 'whole_screen' | 'region';
  regionBox?: { x: number; y: number; w: number; h: number };
  active: boolean;
  lastTriggered: number; // timestamp
}

export interface MatchResult {
  x: number; // center x of the match
  y: number; // center y of the match
  confidence: number; // 0 to 100
  matchedBox: { x: number; y: number; w: number; h: number };
}

/**
 * Computes the best match of template within screenData using Sum of Absolute Differences (SAD)
 * with Early Termination for maximum performance.
 */
export function findTemplateMatch(
  screenData: ImageData,
  templateData: ImageData,
  searchRegion?: { x: number; y: number; w: number; h: number }
): MatchResult | null {
  const sw = screenData.width;
  const sh = screenData.height;
  const tw = templateData.width;
  const th = templateData.height;

  if (tw > sw || th > sh) return null;

  // Define search boundary
  let startX = 0;
  let startY = 0;
  let endX = sw - tw;
  let endY = sh - th;

  if (searchRegion) {
    startX = Math.max(0, searchRegion.x);
    startY = Math.max(0, searchRegion.y);
    endX = Math.min(sw - tw, searchRegion.x + searchRegion.w - tw);
    endY = Math.min(sh - th, searchRegion.y + searchRegion.h - th);
  }

  if (startX > endX || startY > endY) return null;

  const sPixels = screenData.data;
  const tPixels = templateData.data;

  let bestSAD = Infinity;
  let bestX = -1;
  let bestY = -1;

  const maxPixelDiff = 765; // 255 * 3 (R, G, B)
  const maxPossibleDiff = maxPixelDiff * tw * th;

  // Let's optimize: if the template is large, we can subsample its check to be faster,
  // or we can use early termination. Early termination is extremely powerful.
  // To make it even faster, let's step by 2 or 3 in the first pass if the search space is large,
  // or just run early termination. Let's do early termination which is 100% accurate.

  // To avoid performance issues on big images, we can do a coarse pass (step of 2 or 3) and then fine search.
  // Let's implement a dual-pass search for extreme speed.
  const isLargeSearch = (endX - startX) * (endY - startY) > 80000;
  const step = isLargeSearch ? 2 : 1;

  for (let y = startY; y <= endY; y += step) {
    for (let x = startX; x <= endX; x += step) {
      let sad = 0;
      let matched = true;

      for (let ty = 0; ty < th; ty++) {
        const sy = y + ty;
        const sOffsetRow = sy * sw * 4;
        const tOffsetRow = ty * tw * 4;

        for (let tx = 0; tx < tw; tx++) {
          const sx = x + tx;
          const sIdx = sOffsetRow + sx * 4;
          const tIdx = tOffsetRow + tx * 4;

          // Compute absolute differences in R, G, B channels
          const dr = Math.abs(sPixels[sIdx] - tPixels[tIdx]);
          const dg = Math.abs(sPixels[sIdx + 1] - tPixels[tIdx + 1]);
          const db = Math.abs(sPixels[sIdx + 2] - tPixels[tIdx + 2]);

          sad += dr + dg + db;

          // Early termination check
          if (sad >= bestSAD) {
            matched = false;
            break;
          }
        }
        if (!matched) break;
      }

      if (matched && sad < bestSAD) {
        bestSAD = sad;
        bestX = x;
        bestY = y;
      }
    }
  }

  // Fine search pass around the best coarse coordinate (if step was > 1)
  if (step > 1 && bestX !== -1 && bestY !== -1) {
    const fineStartX = Math.max(startX, bestX - step);
    const fineStartY = Math.max(startY, bestY - step);
    const fineEndX = Math.min(endX, bestX + step);
    const fineEndY = Math.min(endY, bestY + step);

    for (let y = fineStartY; y <= fineEndY; y++) {
      for (let x = fineStartX; x <= fineEndX; x++) {
        let sad = 0;
        let matched = true;

        for (let ty = 0; ty < th; ty++) {
          const sy = y + ty;
          const sOffsetRow = sy * sw * 4;
          const tOffsetRow = ty * tw * 4;

          for (let tx = 0; tx < tw; tx++) {
            const sx = x + tx;
            const sIdx = sOffsetRow + sx * 4;
            const tIdx = tOffsetRow + tx * 4;

            const dr = Math.abs(sPixels[sIdx] - tPixels[tIdx]);
            const dg = Math.abs(sPixels[sIdx + 1] - tPixels[tIdx + 1]);
            const db = Math.abs(sPixels[sIdx + 2] - tPixels[tIdx + 2]);

            sad += dr + dg + db;

            if (sad >= bestSAD) {
              matched = false;
              break;
            }
          }
          if (!matched) break;
        }

        if (matched && sad < bestSAD) {
          bestSAD = sad;
          bestX = x;
          bestY = y;
        }
      }
    }
  }

  if (bestX === -1 || bestY === -1) return null;

  // Calculate confidence percentage
  const confidence = maxPossibleDiff > 0 ? 100 * (1.0 - bestSAD / maxPossibleDiff) : 100;

  return {
    x: bestX + tw / 2,
    y: bestY + th / 2,
    confidence: Number(confidence.toFixed(1)),
    matchedBox: {
      x: bestX,
      y: bestY,
      w: tw,
      h: th,
    },
  };
}
