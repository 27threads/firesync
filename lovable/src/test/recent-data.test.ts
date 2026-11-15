import { describe, it, expect } from "vitest";
import {
  coordinateArea,
  demoRecent,
  demoInView,
  demoForWindow,
  recentTotals,
  freshness,
  highShare,
  intensityClass,
  priorityInView,
  RECENT_WINDOWS,
  riskFrequency,
  RISK_HORIZON,
} from "@/lib/recent-data";
import { BRAZIL_STATES, priorityInState } from '@/lib/brazil-states';
describe("recent observation rules", () => {
  it('does not reuse the 24-hour demo for 3-day or 7-day windows', () => {
    const view = { bbox: [-70, -20, -40, 10] as [number, number, number, number], zoom: 4 };
    expect(demoForWindow(view, 24)?.total_detections).toBe(46);
    expect(demoForWindow(view, 72)).toBeNull();
    expect(demoForWindow(view, 168)).toBeNull();
  });
  it('derives all strip totals from one supplied recent response', () => {
    expect(recentTotals(demoRecent)).toEqual({ detections: 3833, critical: 1, attention: 0 });
    expect(recentTotals(demoInView({ bbox: [-70, -20, -40, 10], zoom: 4 }))).toEqual({ detections: 46, critical: 1, attention: 0 });
  });
  it('offers all 27 federative units without inventing state membership', () => {
    expect(new Set(BRAZIL_STATES).size).toBe(27);
    expect(BRAZIL_STATES).toContain('Distrito Federal');
    const cells = demoRecent.alerts?.priority ?? [];
    expect(priorityInState(cells, '')).toEqual(cells);
    expect(priorityInState(cells, 'Amazonas')).toEqual([]);
  });
  it("limits coordinate-area radius to 1–200 km", () => {
    expect(() => coordinateArea(-3.1, -60.2, 0.9)).toThrow();
    expect(() => coordinateArea(-3.1, -60.2, 201)).toThrow();
    expect(coordinateArea(-3.1, -60.2, 1).type).toBe("Polygon");
    expect(coordinateArea(-3.1, -60.2, 200).type).toBe("Polygon");
  });
  it("offers past windows of 24, 72 and 168 hours", () =>
    expect(RECENT_WINDOWS).toEqual([24, 72, 168]));
  it("keeps the future horizon fixed at 14 days", () => expect(RISK_HORIZON).toBe(14));
  it("classifies low below 5 MW", () => expect(intensityClass(4.99)).toBe("low"));
  it("classifies medium from 5 to below 25 MW", () => {
    expect(intensityClass(5)).toBe("medium");
    expect(intensityClass(24.99)).toBe("medium");
  });
  it("classifies high at 25 MW or a saturated pixel", () => {
    expect(intensityClass(25)).toBe("high");
    expect(intensityClass(1, true)).toBe("high");
  });
  it("marks updates older than 6 hours as delayed", () =>
    expect(freshness("2026-11-14T00:00:00Z", Date.parse("2026-11-14T06:01:00Z")).state).toBe(
      "delayed",
    ));
  it("marks updates older than 24 hours as outdated", () =>
    expect(freshness("2026-11-14T00:00:00Z", Date.parse("2026-11-15T00:01:00Z")).state).toBe(
      "outdated",
    ));
  it("uses supplied cell percentages and excludes drawn areas", () => {
    const p = demoRecent.alerts?.priority[0];
    if (!p) throw Error("Missing fixture");
    expect(riskFrequency(p, demoRecent)?.share).toBe(0.266);
    expect(riskFrequency(p, demoRecent)?.average).toBe(0.042);
    expect(riskFrequency(p, demoRecent, true)).toBeNull();
  });
  it("uses only supplied geometry for viewport counts", () => {
    expect(demoInView({ bbox: [-70, -20, -40, 10], zoom: 4 }).total_detections).toBe(46);
    expect(demoInView({ bbox: [0, 0, 10, 10], zoom: 4 }).total_detections).toBe(0);
  });
  it("preserves the supplied high-intensity share", () =>
    expect(highShare(demoRecent.features)).toBeCloseTo(8 / 46));
  it("does not relabel absent risk as normal", () =>
    expect(
      priorityInView({ ...demoRecent, alerts: undefined }, { bbox: [-180, -90, 180, 90], zoom: 4 }),
    ).toEqual([]));
});
