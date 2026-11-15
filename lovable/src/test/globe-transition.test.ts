import { describe, expect, it, vi } from 'vitest';
import { advanceGlobeRotation, journeyTransitionDistance, MAP_ARRIVAL_HOLD, mercatorLatitude, restoreSurfaceView, smoothPhase, surfaceCameraDistance, SURFACE_VIEW, tilePosition } from '../lib/globe-transition';

describe('geographic surface handoff', () => {
  it('adds gentle forward idle rotation and never reverses it during zoom', () => {
    expect(advanceGlobeRotation(0, 1, 0, true)).toBe(0.015);
    for (const progress of [0.02, 0.1, 0.35, 0.9, 1]) expect(advanceGlobeRotation(0.12, 1, progress, true)).toBe(0.12);
    expect(advanceGlobeRotation(0.12, 1, 0, false)).toBe(0.12);
  });
  it('finishes the zoom before the sticky map releases and holds the destination through extra scrolling', () => {
    for (const [section, viewport] of [[1535, 495], [2532, 844]]) {
      if (section === undefined || viewport === undefined) continue;
      const distance = journeyTransitionDistance(section, viewport);
      const release = section - viewport;
      expect(release - distance).toBeCloseTo(viewport * MAP_ARRIVAL_HOLD);
      expect(Math.min(1, (distance + viewport * 0.5) / distance)).toBe(1);
      expect(distance + viewport * 0.5).toBeLessThan(release);
    }
  });
  it('returns to the same Brazil center and zoom after each map exploration', () => {
    let center = [38.7, -9.1];
    let zoom = 8;
    const stop = vi.fn();
    const map = { stop, setView: vi.fn((next: [number, number], level: number, options: { animate: boolean }) => {
      expect(stop).toHaveBeenCalled();
      expect(options.animate).toBe(false);
      center = next;
      zoom = level;
    }) };
    for (const exploredCenter of [[38.7, -9.1], [0, 130], [-30, -60]]) {
      center = exploredCenter;
      zoom = 8;
      restoreSurfaceView(map);
      expect(center).toEqual([-14, -52]);
      expect(zoom).toBe(4);
    }
    expect(stop).toHaveBeenCalledTimes(3);
  });
  it('lands directly over Brazil in both geographic views', () => {
    expect(SURFACE_VIEW.latitude).toBe(-14);
    expect(SURFACE_VIEW.longitude).toBe(-52);
    expect(SURFACE_VIEW.zoom).toBe(4);
  });
  it('maps texture coordinates to the identical NASA tile coordinate system', () => {
    expect(tilePosition(0, 0, 4)).toEqual({ x: 8, y: 8 });
    const brazil = tilePosition(-14, -52, 4);
    expect(brazil.x).toBeCloseTo(5.688888889, 8);
    expect(brazil.y).toBeCloseTo(8.628507905, 8);
  });
  it('matches the map world width at the final camera distance', () => {
    for (const height of [373, 722, 1690]) {
      const distance = surfaceCameraDistance(height);
      const projectedWorldWidth = 2 * Math.PI * SURFACE_VIEW.radius * height / (2 * distance * Math.tan(SURFACE_VIEW.fov * Math.PI / 360));
      expect(projectedWorldWidth).toBeCloseTo(4096, 6);
    }
  });
  it('preserves the southern geographic center rather than flipping latitude', () => {
    expect(mercatorLatitude(0)).toBeCloseTo(0);
    expect(mercatorLatitude(-7.5)).toBeCloseTo(-0.131274, 5);
  });
  it('keeps the map hidden until the surface zoom is almost complete', () => {
    expect(smoothPhase(0.8, 0.9, 0.98)).toBe(0);
    expect(smoothPhase(0.98, 0.9, 0.98)).toBe(1);
  });
});