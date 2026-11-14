import { scaleSequentialLog } from 'd3-scale';
import { interpolateCividis } from 'd3-scale-chromatic';

// Escala logarítmica: setembro tem cerca de 30× mais focos que março (docs/arquitetura.md, ponto 8).
// Só recebe contagens positivas; zero e "sem dados" têm estilo próprio, fora da rampa.
export function makeColorScale([min, max]: [number, number]): (detections: number) => string {
  const upper = max > min ? max : min * 10;
  const scale = scaleSequentialLog(interpolateCividis).domain([min, upper]).clamp(true);
  return (detections) => scale(detections);
}
