import { describe, expect, it } from "vitest";
import { countColor, ZERO_COLOR, COUNT_GRADIENT } from "@/lib/recent-data";

const lum = (rgb: string) => {
  const m = rgb.match(/\d+/g)!.map(Number);
  return 0.2126 * m[0]! + 0.7152 * m[1]! + 0.0722 * m[2]!;
};

describe("escala de cor dos hot spots (cividis, logarítmica)", () => {
  it("zero tem cor própria, fora da rampa", () => {
    expect(countColor(0)).toBe(ZERO_COLOR);
    expect(countColor(1)).not.toBe(ZERO_COLOR);
  });
  it("a luminosidade cresce com a contagem, o que se lê sem depender do matiz", () => {
    expect(lum(countColor(10))).toBeGreaterThan(lum(countColor(1)));
    expect(lum(countColor(100))).toBeGreaterThan(lum(countColor(10)));
  });
  it("é logarítmica: 1 a 10 e 10 a 100 mudam a cor na mesma proporção", () => {
    const a = lum(countColor(10)) - lum(countColor(1));
    const b = lum(countColor(100)) - lum(countColor(10));
    expect(Math.abs(a - b)).toBeLessThan(Math.max(a, b) * 0.5);
  });
  it("acima do limite a cor não muda (clamp)", () => {
    expect(countColor(5000)).toBe(countColor(100));
  });
  it("o gradiente da legenda usa a mesma escala", () => {
    expect(COUNT_GRADIENT).toContain(countColor(1));
    expect(COUNT_GRADIENT).toContain(countColor(100));
  });
});
