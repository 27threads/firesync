import type { Place } from '../api/types';
import { areaLink, parseAreaLink, placeName, protectedAreas } from './mapLink';

const place = (over: Partial<Place> = {}): Place => ({
  municipality: 'Altamira',
  state: 'PA',
  conservation_units: [],
  indigenous_lands: [],
  ...over,
});

describe('placeName', () => {
  it('names the municipality and the state, as people in the field know the area', () => {
    expect(placeName(place(), -3.2, -52.2)).toBe('Altamira, PA');
  });

  it('falls back to the coordinates when the place is unknown', () => {
    expect(placeName(null, -3.2, -52.2)).toBe('Area near 3.20°S, 52.20°W');
    expect(placeName(undefined, -3.2, -52.2)).toBe('Area near 3.20°S, 52.20°W');
    expect(placeName(place({ municipality: null, state: null }), -3.2, -52.2)).toBe('Area near 3.20°S, 52.20°W');
  });
});

describe('protectedAreas', () => {
  it('lists indigenous lands and conservation units with their kind, in that order', () => {
    expect(protectedAreas(place({ indigenous_lands: ['Kayapó'], conservation_units: ['Parque A', 'Reserva B'] }))).toEqual([
      'Indigenous land: Kayapó',
      'Conservation unit: Parque A',
      'Conservation unit: Reserva B',
    ]);
  });

  it('is empty without a place or without protected areas', () => {
    expect(protectedAreas(null)).toEqual([]);
    expect(protectedAreas(place())).toEqual([]);
  });
});

describe('area link', () => {
  it('points at the cell center and the map view, and reads back the same', () => {
    const link = areaLink('https://firesync.nogranlabs.com.br/', [-52.2346, -3.1234], 'risk');
    expect(link).toBe('https://firesync.nogranlabs.com.br/?at=-3.123,-52.235&view=risk');
    expect(parseAreaLink(new URL(link).search)).toEqual({ lat: -3.123, lon: -52.235, mode: 'risk' });
  });

  it('keeps the page path and drops any old query or hash', () => {
    expect(areaLink('http://localhost:5173/app?x=1#explore', [-60, -3], 'fire')).toBe('http://localhost:5173/app?at=-3.000,-60.000&view=fire');
  });

  it('opens the fire view when the view is missing or unknown', () => {
    expect(parseAreaLink('?at=-3,-60')).toEqual({ lat: -3, lon: -60, mode: 'fire' });
    expect(parseAreaLink('?at=-3,-60&view=other')).toEqual({ lat: -3, lon: -60, mode: 'fire' });
  });

  it('ignores a missing or broken location', () => {
    for (const search of ['', '?view=risk', '?at=abc', '?at=-3', '?at=-91,10', '?at=10,181', '?at=,', '?at=1e999,0']) {
      expect(parseAreaLink(search)).toBeNull();
    }
  });
});
