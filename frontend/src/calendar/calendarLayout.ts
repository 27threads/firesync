import type { MonthPosition } from './calendarModel';

// Geometria pura do calendário: a mesma célula tem uma posição na faixa cronológica
// (abertura) e uma posição na grade ano × mês (calendário). A animação só interpola as duas.

export interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface GridSpec {
  left: number;
  top: number;
  cellWidth: number;
  cellHeight: number;
  gap: number;
}

export interface StripSpec {
  left: number;
  top: number;
  width: number;
  height: number;
}

export function gridGeometry(position: MonthPosition, firstYear: number, spec: GridSpec): Box {
  return {
    x: spec.left + position.monthIndex * (spec.cellWidth + spec.gap),
    y: spec.top + (position.year - firstYear) * (spec.cellHeight + spec.gap),
    width: spec.cellWidth,
    height: spec.cellHeight,
  };
}

export function stripGeometry(index: number, total: number, spec: StripSpec): Box {
  const width = spec.width / total;
  return { x: spec.left + index * width, y: spec.top, width, height: spec.height };
}

export function transitionColumn(sensorSwitch: MonthPosition | null): number | null {
  return sensorSwitch ? sensorSwitch.monthIndex : null;
}
