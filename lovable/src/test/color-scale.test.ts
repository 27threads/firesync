import { describe, expect, it } from "vitest";
import { countColor, ZERO_COLOR, COUNT_BINS } from "@/lib/recent-data";

describe("faixas de cor dos hot spots por área (Figma)", () => {
  it("zero tem cor própria, fora da rampa", () => {
    expect(countColor(0)).toBe(ZERO_COLOR);
    expect(COUNT_BINS.map((b) => b.color)).not.toContain(ZERO_COLOR);
  });
  it("cada faixa tem a sua cor e a rampa escurece com a contagem", () => {
    const lum = (hex: string) => {
      const n = parseInt(hex.slice(1), 16);
      return 0.2126 * (n >> 16) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    };
    const cores = [1, 3, 10, 30].map(countColor);
    expect(new Set(cores).size).toBe(4);
    for (let i = 1; i < cores.length; i++) expect(lum(cores[i]!)).toBeLessThan(lum(cores[i - 1]!));
  });
  it("os limites das faixas são 1–2, 3–9, 10–29 e 30 ou mais", () => {
    expect(countColor(2)).toBe(countColor(1));
    expect(countColor(9)).toBe(countColor(3));
    expect(countColor(29)).toBe(countColor(10));
    expect(countColor(5000)).toBe(countColor(30));
  });
});
