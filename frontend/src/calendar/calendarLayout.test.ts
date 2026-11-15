import { gridGeometry, stripGeometry, transitionColumn } from './calendarLayout';

describe('calendar layout (strip that folds into the year grid)', () => {
  const grid = { left: 40, top: 20, cellWidth: 30, cellHeight: 12, gap: 2 };

  it('places a month in its column (Jan–Dec) and its year row', () => {
    const cell = gridGeometry({ year: 2012, monthIndex: 1 }, 2003, grid);
    expect(cell).toEqual({ x: 40 + 1 * 32, y: 20 + 9 * 14, width: 30, height: 12 });
  });

  it('keeps chronological order along the strip', () => {
    const strip = { left: 0, top: 100, width: 287, height: 40 };
    const a = stripGeometry(0, 287, strip);
    const b = stripGeometry(1, 287, strip);
    const last = stripGeometry(286, 287, strip);
    expect(a.x).toBe(0);
    expect(b.x).toBeGreaterThan(a.x);
    expect(last.x + last.width).toBeCloseTo(287);
    expect(a.y).toBe(100);
    expect(a.height).toBe(40);
  });

  it('gives every month the same strip width, so no month looks bigger than another', () => {
    const strip = { left: 10, top: 0, width: 574, height: 30 };
    expect(stripGeometry(5, 287, strip).width).toBeCloseTo(2);
    expect(stripGeometry(200, 287, strip).width).toBeCloseTo(2);
  });

  it('returns the column of the first observed month for the sensor transition mark', () => {
    expect(transitionColumn({ year: 2012, monthIndex: 1 })).toBe(1);
    expect(transitionColumn(null)).toBeNull();
  });
});
