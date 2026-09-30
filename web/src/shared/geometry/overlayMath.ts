/**
 * Pure coordinate transformation and letterbox geometry math for video overlay.
 */

export interface LetterboxRect {
  offsetX: number; // Letterbox / pillarbox horizontal offset in container
  offsetY: number; // Letterbox vertical offset in container
  renderWidth: number; // Scaled video display width
  renderHeight: number; // Scaled video display height
  scale: number; // Ratio of display pixels to source video pixels
}

/**
 * Compute the letterbox destination rectangle given container and source dimensions.
 * Mimics CSS `object-fit: contain`.
 */
export function computeLetterbox(
  containerWidth: number,
  containerHeight: number,
  videoWidth: number,
  videoHeight: number
): LetterboxRect {
  if (containerWidth <= 0 || containerHeight <= 0 || videoWidth <= 0 || videoHeight <= 0) {
    return { offsetX: 0, offsetY: 0, renderWidth: 0, renderHeight: 0, scale: 1 };
  }

  const containerAspect = containerWidth / containerHeight;
  const videoAspect = videoWidth / videoHeight;

  let renderWidth: number;
  let renderHeight: number;
  let offsetX: number;
  let offsetY: number;

  if (containerAspect > videoAspect) {
    // Pillarbox: video is narrower than container -> black bars on sides
    renderHeight = containerHeight;
    renderWidth = containerHeight * videoAspect;
    offsetX = (containerWidth - renderWidth) / 2;
    offsetY = 0;
  } else {
    // Letterbox: video is wider than container -> black bars on top and bottom
    renderWidth = containerWidth;
    renderHeight = containerWidth / videoAspect;
    offsetX = 0;
    offsetY = (containerHeight - renderHeight) / 2;
  }

  const scale = renderWidth / videoWidth;

  return {
    offsetX,
    offsetY,
    renderWidth,
    renderHeight,
    scale,
  };
}

/**
 * Transform normalized source coordinates [0, 1] to canvas pixels.
 */
export function normalizedToCanvasCoords(
  normX: number,
  normY: number,
  letterbox: LetterboxRect,
  dpr: number = 1
): { canvasX: number; canvasY: number } {
  const cssX = letterbox.offsetX + normX * letterbox.renderWidth;
  const cssY = letterbox.offsetY + normY * letterbox.renderHeight;
  return {
    canvasX: cssX * dpr,
    canvasY: cssY * dpr,
  };
}

/**
 * Transform bounding box in source frame pixels to canvas destination rect.
 */
export function sourceBoxToCanvasCoords(
  bboxXyxy: [number, number, number, number],
  imageWidth: number,
  imageHeight: number,
  letterbox: LetterboxRect,
  dpr: number = 1
): { x: number; y: number; width: number; height: number } {
  if (imageWidth <= 0 || imageHeight <= 0) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }

  const [x1, y1, x2, y2] = bboxXyxy;
  const normX1 = x1 / imageWidth;
  const normY1 = y1 / imageHeight;
  const normX2 = x2 / imageWidth;
  const normY2 = y2 / imageHeight;

  const p1 = normalizedToCanvasCoords(normX1, normY1, letterbox, dpr);
  const p2 = normalizedToCanvasCoords(normX2, normY2, letterbox, dpr);

  return {
    x: p1.canvasX,
    y: p1.canvasY,
    width: p2.canvasX - p1.canvasX,
    height: p2.canvasY - p1.canvasY,
  };
}
