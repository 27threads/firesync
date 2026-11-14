import { interpolateCividis } from 'd3-scale-chromatic';
import { makeColorScale } from './colorScale';

describe('makeColorScale (cividis, logarithmic)', () => {
  const color = makeColorScale([1, 1000]);

  it('maps the smallest positive count to the start of cividis', () => {
    expect(color(1)).toBe(interpolateCividis(0));
  });

  it('maps the largest count to the end of cividis', () => {
    expect(color(1000)).toBe(interpolateCividis(1));
  });

  it('is logarithmic: 10× more detections moves the same distance on the ramp', () => {
    expect(color(10)).toBe(interpolateCividis(1 / 3));
    expect(color(100)).toBe(interpolateCividis(2 / 3));
  });

  it('works when every month has the same count', () => {
    expect(() => makeColorScale([5, 5])(5)).not.toThrow();
  });
});
