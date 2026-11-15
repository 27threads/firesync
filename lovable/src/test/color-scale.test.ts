import { describe, expect, it } from "vitest";
import { countColor, ZERO_COLOR, COUNT_GRADIENT } from "@/lib/recent-data";

describe("escala de cor dos hot spots (cividis, logarítmica)", () => {
  it("zero tem cor própria, fora da rampa", () => {
    expect(countColor(0)).toBe(ZERO_COLOR);
    expect(countColor(1)).not.toBe(ZERO_COLOR);
  });
  it("contagens maiores têm cores diferentes e crescentes em luminosidade", () => {
    const lum = (hex: string) => {
      const m = hex.match(/\d+/g)!.map(Number);
      return 0.2126 * m[0]! + 0.7152 * m[1]! + 0.0722 * m[2]!;
    };
    expect(lum(countColor(100))).toBeGreaterThan(lum(countColor(10)));
    expect(lum(countColor(10))).toBeGreaterThan(lum(countColor(1)));
  });
  it("acima do limite a cor não muda (clamp)", () => {
    expect(countColor(5000)).toBe(countColor(100));
  });
  it("o gradiente da legenda usa a mesma escala", () => {
    expect(COUNT_GRADIENT).toContain(countColor(1));
    expect(COUNT_GRADIENT).toContain(countColor(100));
  });
});
