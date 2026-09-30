import { describe, it, expect } from 'vitest';
import {
  computeLetterbox,
  normalizedToCanvasCoords,
  sourceBoxToCanvasCoords,
} from './overlayMath';

describe('overlayMath letterbox and coordinate transformations', () => {
  it('correctly calculates pillarbox when container is wider than video', () => {
    // Container: 1000x500 (2:1). Video: 400x400 (1:1)
    const lb = computeLetterbox(1000, 500, 400, 400);

    expect(lb.renderHeight).toBe(500);
    expect(lb.renderWidth).toBe(500);
    expect(lb.offsetX).toBe(250); // (1000 - 500) / 2
    expect(lb.offsetY).toBe(0);
    expect(lb.scale).toBe(500 / 400);
  });

  it('correctly calculates letterbox when container is taller than video', () => {
    // Container: 800x800 (1:1). Video: 1920x1080 (16:9)
    const lb = computeLetterbox(800, 800, 1920, 1080);

    expect(lb.renderWidth).toBe(800);
    expect(lb.offsetX).toBe(0);
    expect(lb.renderHeight).toBeCloseTo(800 / (1920 / 1080), 2);
    expect(lb.offsetY).toBeGreaterThan(0);
  });

  it('maps normalized coordinates correctly onto canvas', () => {
    const lb = {
      offsetX: 100,
      offsetY: 50,
      renderWidth: 800,
      renderHeight: 400,
      scale: 1,
    };

    // Center (0.5, 0.5) with dpr = 1
    const pt = normalizedToCanvasCoords(0.5, 0.5, lb, 1);
    expect(pt.canvasX).toBe(100 + 400); // 500
    expect(pt.canvasY).toBe(50 + 200);  // 250

    // With dpr = 2 (Retina displays)
    const pt2 = normalizedToCanvasCoords(0.5, 0.5, lb, 2);
    expect(pt2.canvasX).toBe(1000);
    expect(pt2.canvasY).toBe(500);
  });

  it('maps source box to exact canvas bounding box', () => {
    const lb = {
      offsetX: 0,
      offsetY: 0,
      renderWidth: 1000,
      renderHeight: 500,
      scale: 1,
    };

    // Box [100, 50, 300, 150] on 1000x500 source frame
    const box = sourceBoxToCanvasCoords([100, 50, 300, 150], 1000, 500, lb, 1);
    expect(box.x).toBe(100);
    expect(box.y).toBe(50);
    expect(box.width).toBe(200);
    expect(box.height).toBe(100);
  });
});
