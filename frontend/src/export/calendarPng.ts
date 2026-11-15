import type { CalendarMonth } from '../api/types';
import { buildCalendar, MONTH_NAMES } from '../calendar/calendarModel';
import { makeColorScale } from '../calendar/colorScale';

// PNG do calendário desenhado direto no canvas a partir dos meses da tela,
// com área, período, origem dos dados e crédito ao NASA FIRMS.

export interface CalendarPngMeta {
  areaLabel: string;
  periodLabel: string;
  isDemo: boolean;
}

const INK = '#15181b';
const SOFT = '#4b535c';
const PAPER = '#fbfbfa';
const FONT = "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

export async function renderCalendarPng(months: CalendarMonth[], meta: CalendarPngMeta): Promise<Blob> {
  const model = buildCalendar(months);
  const color = model.positiveExtent ? makeColorScale(model.positiveExtent) : null;
  const cw = 54;
  const ch = 20;
  const gap = 2;
  const left = 64;
  const top = 108;
  const rows = model.years.length;
  const width = left + 12 * (cw + gap) + 40;
  const height = top + rows * (ch + gap) + 80;
  const scale = 2;

  const canvas = document.createElement('canvas');
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('This browser cannot draw the image.');
  ctx.scale(scale, scale);

  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = INK;
  ctx.font = `600 18px ${FONT}`;
  ctx.fillText('firesync · Monthly fire detections, VIIRS scale', 24, 36);
  ctx.fillStyle = SOFT;
  ctx.font = `13px ${FONT}`;
  ctx.fillText(`${meta.areaLabel} · ${meta.periodLabel} (UTC)`, 24, 58);
  if (meta.isDemo) {
    ctx.fillStyle = '#8a5800';
    ctx.font = `600 13px ${FONT}`;
    ctx.fillText('Demo data: illustrative values from the API contract example, not measurements.', 24, 78);
  }

  ctx.fillStyle = SOFT;
  ctx.font = `11px ${FONT}`;
  ctx.textAlign = 'center';
  MONTH_NAMES.forEach((name, i) => ctx.fillText(name, left + i * (cw + gap) + cw / 2, top - 8));

  const firstYear = model.years[0]?.year ?? 0;
  model.years.forEach((row, r) => {
    const y = top + r * (ch + gap);
    ctx.fillStyle = SOFT;
    ctx.textAlign = 'right';
    ctx.fillText(String(row.year), left - 8, y + ch / 2 + 4);
    row.cells.forEach((cell, c) => {
      const x = left + c * (cw + gap);
      if (cell.state === 'value' && color) {
        ctx.fillStyle = color(cell.detections);
        ctx.fillRect(x, y, cw, ch);
      } else if (cell.state === 'zero') {
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(x, y, cw, ch);
        ctx.strokeStyle = SOFT;
        ctx.strokeRect(x + 0.5, y + 0.5, cw - 1, ch - 1);
      } else if (cell.state === 'no_data') {
        ctx.fillStyle = '#eceeef';
        ctx.fillRect(x, y, cw, ch);
        ctx.strokeStyle = '#9aa1a8';
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + cw, y + ch);
        ctx.moveTo(x + cw, y);
        ctx.lineTo(x, y + ch);
        ctx.stroke();
      }
      if (cell.estimated && cell.state !== 'no_data') {
        ctx.save();
        ctx.beginPath();
        ctx.rect(x, y, cw, ch);
        ctx.clip();
        ctx.strokeStyle = 'rgba(255,255,255,0.55)';
        ctx.lineWidth = 1;
        for (let k = -ch; k < cw; k += 5) {
          ctx.beginPath();
          ctx.moveTo(x + k, y + ch);
          ctx.lineTo(x + k + ch, y);
          ctx.stroke();
        }
        ctx.restore();
      }
      if (cell.incomplete) {
        ctx.save();
        ctx.setLineDash([3, 2]);
        ctx.strokeStyle = INK;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x + 1.25, y + 1.25, cw - 2.5, ch - 2.5);
        ctx.restore();
      }
      if (cell.provisional) {
        ctx.fillStyle = INK;
        ctx.beginPath();
        ctx.arc(x + cw - 4.5, y + 4.5, 2.4, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  });

  const sw = model.sensorSwitch;
  if (sw) {
    const r = sw.year - firstYear;
    const yTop = top + r * (ch + gap) - 1;
    const yBottom = yTop + ch + gap;
    const xCol = left + sw.monthIndex * (cw + gap) - 1;
    const right = left + 12 * (cw + gap);
    ctx.strokeStyle = INK;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(left - 4, yBottom);
    ctx.lineTo(xCol, yBottom);
    ctx.lineTo(xCol, yTop);
    ctx.lineTo(right, yTop);
    ctx.stroke();
  }

  const footY = top + rows * (ch + gap) + 26;
  ctx.textAlign = 'left';
  ctx.fillStyle = SOFT;
  ctx.font = `11px ${FONT}`;
  ctx.fillText(
    'Cividis, log scale. Hatched: estimated from MODIS Aqua with a P5–P95 range. Dashed: incomplete. Dot: provisional. Line: Feb 2012, VIIRS begins.',
    24,
    footY,
  );
  ctx.fillText('Data: NASA FIRMS, MODIS C6.1 (Aqua) and VIIRS C2 (S-NPP, NOAA-20). Counts are detections, not fires.', 24, footY + 18);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Could not create the image.'))), 'image/png');
  });
}
