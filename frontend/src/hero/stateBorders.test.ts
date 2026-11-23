import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { STATE_BORDER_STYLE, stateLabels, stateLabelsVisible, type StatesCollection } from './stateBorders';

const states = JSON.parse(readFileSync(resolve(__dirname, '../../public/brazil-states.geojson'), 'utf-8')) as StatesCollection;

describe('state borders file (IBGE, made by data-pipeline/lugares.py --estados)', () => {
  it('has the 26 states and the Federal District, each with its abbreviation and a label point in Brazil', () => {
    expect(states.features.map((f) => f.properties.state).sort()).toHaveLength(27);
    for (const { properties } of states.features) {
      expect(properties.state).toMatch(/^[A-Z]{2}$/);
      const [lon, lat] = properties.label;
      expect(lon).toBeGreaterThan(-75);
      expect(lon).toBeLessThan(-28);
      expect(lat).toBeGreaterThan(-34);
      expect(lat).toBeLessThan(6);
    }
  });

  it('stays small enough for a phone', () => {
    expect(readFileSync(resolve(__dirname, '../../public/brazil-states.geojson')).byteLength).toBeLessThan(400_000);
  });
});

describe('stateLabels', () => {
  it('puts each abbreviation at its label point, as [lat, lon] for the map', () => {
    expect(stateLabels(states).find((l) => l.state === 'PA')?.latlng).toEqual(
      [...states.features.find((f) => f.properties.state === 'PA')!.properties.label].reverse(),
    );
  });
});

describe('stateLabelsVisible', () => {
  it('hides the abbreviations in the whole-Brazil view and shows them once the map is closer', () => {
    expect(stateLabelsVisible(4)).toBe(false);
    expect(stateLabelsVisible(5)).toBe(true);
    expect(stateLabelsVisible(9)).toBe(true);
  });
});

it('draws only a thin line: no fill that would cover the risk colours', () => {
  expect(STATE_BORDER_STYLE.fill).toBe(false);
  expect(STATE_BORDER_STYLE.weight).toBeLessThanOrEqual(1.5);
});
