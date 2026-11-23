import { BASEMAPS, DEFAULT_BASEMAP, latestImageDate, latestImageLabel, viirsTrueColorTiles } from './basemap';

describe('latest satellite image (NASA GIBS, VIIRS true color)', () => {
  it('uses the day before in UTC: today is still being filled as the satellite passes', () => {
    expect(latestImageDate(new Date('2026-11-23T18:00:00Z'))).toBe('2026-11-22');
    expect(latestImageDate(new Date('2026-11-23T00:30:00Z'))).toBe('2026-11-22');
    expect(latestImageDate(new Date('2026-03-01T12:00:00Z'))).toBe('2026-02-28');
  });

  it('asks GIBS for that day, in the web map tiles up to zoom 9', () => {
    expect(viirsTrueColorTiles('2026-11-22')).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/2026-11-22/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg',
    );
    expect(BASEMAPS.latest.maxNativeZoom).toBe(9);
  });

  it('says on screen which day the image shows and where it comes from', () => {
    expect(latestImageLabel('2026-11-22')).toBe('Satellite image of 22 Nov 2026 (NASA VIIRS, NOAA-20)');
  });

  it('keeps the clear Blue Marble view, the same image the globe lands on', () => {
    expect(BASEMAPS.clear.maxNativeZoom).toBe(8);
    expect(BASEMAPS.clear.url).toContain('BlueMarble_ShadedRelief_Bathymetry');
  });
});

it('opens the map on the clear view; the real image of the day is one click away', () => {
  expect(DEFAULT_BASEMAP).toBe('clear');
});
