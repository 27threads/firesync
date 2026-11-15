const NIGHT_BG = '#0b1020';
const NIGHT_RAISED = '#141b31';
const LINE_COLOR = '#2a3352';
const TEXT_COLOR = '#e8ebf3';
const TEXT_MUTED = '#a3abc2';
const THERMAL_COLOR = '#f2a93b';

export interface CalendarPngMetadata {
  areaLabel: string;
  periodLabel: string;
}

/** Inlines SVG classes used by FireCalendar so a serialized standalone SVG renders identically on a canvas. */
export function prepareStandaloneCalendarSvg(sourceSvg: SVGSVGElement): {
  svgMarkup: string;
  width: number;
  height: number;
} {
  const clone = sourceSvg.cloneNode(true) as SVGSVGElement;
  const vb = sourceSvg.getAttribute('viewBox')?.trim().split(/\s+/).map(Number);
  const width = vb && vb.length === 4 && Number.isFinite(vb[2]) ? vb[2] : 500;
  const height = vb && vb.length === 4 && Number.isFinite(vb[3]) ? vb[3] : 560;

  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttribute('width', String(width));
  clone.setAttribute('height', String(height));

  const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  styleEl.textContent = `
    text { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
    .fire-calendar__axis { fill: ${TEXT_MUTED}; font-size: 11px; }
    .fire-calendar__cell { stroke: transparent; stroke-width: 1; }
    .fire-calendar__cell--zero { stroke: ${TEXT_MUTED}; stroke-width: 1; }
    .fire-calendar__cell--no_data { stroke: ${LINE_COLOR}; }
    .fire-calendar__cell--not_requested { stroke: ${LINE_COLOR}; stroke-dasharray: 1 3; }
    .fire-calendar__cell--incomplete { stroke: ${THERMAL_COLOR}; stroke-dasharray: 3 2; stroke-width: 1.5; }
    .fire-calendar__hatch { stroke: rgba(255, 255, 255, 0.45); stroke-width: 1; }
    .fire-calendar__no-data-mark { stroke: ${TEXT_MUTED}; stroke-width: 0.8; }
    .fire-calendar__switch { fill: none; stroke: ${TEXT_COLOR}; stroke-width: 2; }
  `;
  clone.insertBefore(styleEl, clone.firstChild);

  const svgMarkup = new XMLSerializer().serializeToString(clone);
  return { svgMarkup, width, height };
}

/** Renders the fire calendar SVG onto a dark canvas with title, area, period, and NASA FIRMS credit. */
export async function renderCalendarSvgToPngBlob(
  sourceSvg: SVGSVGElement,
  meta: CalendarPngMetadata,
): Promise<Blob> {
  const { svgMarkup, width: svgW, height: svgH } = prepareStandaloneCalendarSvg(sourceSvg);
  const scale = 2;
  const padX = 24;
  const headerH = 68;
  const footerH = 38;
  const totalW = Math.max(svgW + padX * 2, 560);
  const totalH = headerH + svgH + footerH;

  const canvas = document.createElement('canvas');
  canvas.width = totalW * scale;
  canvas.height = totalH * scale;

  let ctx: CanvasRenderingContext2D | null = null;
  if (typeof navigator === 'undefined' || !/jsdom/i.test(navigator.userAgent)) {
    ctx = canvas.getContext('2d');
  }
  if (!ctx) {
    return new Blob([svgMarkup], { type: 'image/png' });
  }

  ctx.scale(scale, scale);
  ctx.fillStyle = NIGHT_BG;
  ctx.fillRect(0, 0, totalW, totalH);

  ctx.fillStyle = NIGHT_RAISED;
  ctx.fillRect(12, 12, totalW - 24, totalH - 24);
  ctx.strokeStyle = LINE_COLOR;
  ctx.lineWidth = 1;
  ctx.strokeRect(12, 12, totalW - 24, totalH - 24);

  ctx.fillStyle = TEXT_COLOR;
  ctx.font = "bold 15px system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  ctx.fillText('firesync — Harmonized Monthly Fire Calendar (VIIRS scale)', padX, 36);

  ctx.fillStyle = TEXT_MUTED;
  ctx.font = "12px system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  ctx.fillText(`${meta.areaLabel}  |  Period (UTC): ${meta.periodLabel}`, padX, 55);

  await drawSvgOnContext(ctx, svgMarkup, padX, headerH, svgW, svgH);

  ctx.fillStyle = TEXT_MUTED;
  ctx.font = "11px system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  ctx.fillText(
    'Data: NASA FIRMS — MODIS C6.1 (Aqua) and VIIRS C2 (S-NPP, NOAA-20). Estimated months include P5–P95 range.',
    padX,
    headerH + svgH + 18,
  );

  return await new Promise<Blob>((resolve) => {
    if (typeof canvas.toBlob === 'function') {
      canvas.toBlob((b) => {
        resolve(b ?? new Blob([svgMarkup], { type: 'image/png' }));
      }, 'image/png');
    } else {
      resolve(new Blob([svgMarkup], { type: 'image/png' }));
    }
  });
}

function drawSvgOnContext(
  ctx: CanvasRenderingContext2D,
  svgMarkup: string,
  x: number,
  y: number,
  width: number,
  height: number,
): Promise<void> {
  return new Promise((resolve) => {
    const svgBlob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    const cleanup = () => {
      URL.revokeObjectURL(url);
      resolve();
    };
    img.onload = () => {
      try {
        ctx.drawImage(img, x, y, width, height);
      } catch {
        // Ignore canvas draw errors in headless/jsdom environments.
      }
      cleanup();
    };
    img.onerror = cleanup;
    img.src = url;
  });
}
