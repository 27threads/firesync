import { shapeView } from './shapeView';

describe('shapeView (map view of a selection, used before the map has loaded)', () => {
  it('uses the outer ring of a drawn polygon', () => {
    const view = shapeView({
      kind: 'polygon',
      geometry: { type: 'Polygon', coordinates: [[[-60.5, -3.5], [-59.5, -3.5], [-59.5, -2.5], [-60.5, -2.5], [-60.5, -3.5]]] },
    });
    expect(view.bbox).toEqual([-60.5, -3.5, -59.5, -2.5]);
  });

  it('turns a point and radius into a box around the circle', () => {
    const view = shapeView({ kind: 'point', point: { type: 'point', lat: 0, lon: 10, radius_km: 111.32 } });
    expect(view.bbox[0]).toBeCloseTo(9, 2);
    expect(view.bbox[2]).toBeCloseTo(11, 2);
    expect(view.bbox[1]).toBeCloseTo(-1, 2);
    expect(view.bbox[3]).toBeCloseTo(1, 2);
  });

  it('keeps a region bbox and picks a closer zoom for smaller areas', () => {
    const big = shapeView({ kind: 'bbox', bbox: [-74, -16.3, -43.9, 5.3] });
    const small = shapeView({ kind: 'bbox', bbox: [-60.5, -3.5, -59.5, -2.5] });
    expect(big.bbox).toEqual([-74, -16.3, -43.9, 5.3]);
    expect(small.zoom).toBeGreaterThan(big.zoom);
    expect(big.zoom).toBeGreaterThanOrEqual(2);
  });
});
