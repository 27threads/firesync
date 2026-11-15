import { chapterAt, journeyProgress, mercatorLatitude, openingLayout, smoothPhase, tilePosition } from './globeTransition';

describe('globe opening geometry', () => {
  it('stacks the copy over the globe below the tablet width and puts it beside the globe above', () => {
    expect(openingLayout(375)).toBe('stacked');
    expect(openingLayout(768)).toBe('stacked');
    expect(openingLayout(959)).toBe('stacked');
    expect(openingLayout(960)).toBe('side');
    expect(openingLayout(1280)).toBe('side');
  });

  it('eases between two points of the scroll and stays flat outside them', () => {
    expect(smoothPhase(0.1, 0.2, 0.6)).toBe(0);
    expect(smoothPhase(0.4, 0.2, 0.6)).toBeCloseTo(0.5);
    expect(smoothPhase(0.9, 0.2, 0.6)).toBe(1);
  });

  it('puts the equator and the prime meridian at the middle of the tile grid', () => {
    expect(mercatorLatitude(0)).toBeCloseTo(0);
    expect(tilePosition(0, 0, 4)).toEqual({ x: 8, y: 8 });
  });

  it('measures how far the opening has been scrolled, from 0 to 1', () => {
    // Seção de 3000 px numa janela de 1000 px: o caminho do scroll é 2000 px.
    expect(journeyProgress(0, 3000, 1000)).toBe(0);
    expect(journeyProgress(-1000, 3000, 1000)).toBe(0.5);
    expect(journeyProgress(-5000, 3000, 1000)).toBe(1);
    expect(journeyProgress(200, 3000, 1000)).toBe(0);
  });

  it('shows one chapter of the opening text for each part of the scroll', () => {
    expect(chapterAt(0)).toBe(0);
    expect(chapterAt(0.3)).toBe(1);
    expect(chapterAt(0.7)).toBe(2);
  });
});
