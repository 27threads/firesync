export interface OpeningChapter {
  label: string;
  title: readonly [string, string];
  copy: string;
}

export const OPENING_AUDIENCE = 'NASA Space Apps 2026 · for fire brigades, civil defense and land managers';

export const OPENING_CHAPTERS: readonly OpeningChapter[] = [
  {
    label: 'Our planet',
    title: ['Is this fire normal?', 'Here, this season.'],
    copy: "NASA FIRMS shows where fire is. firesync tells you if it's normal.",
  },
  {
    label: 'The record',
    title: ['Two satellites.', 'One fire history.'],
    copy: 'MODIS and VIIRS harmonized into one monthly record since 2003, with the uncertainty shown.',
  },
  {
    label: 'Your place',
    title: ['The present.', 'In context.'],
    copy: 'Compare the last 7 days with what is typical for the same area and season.',
  },
];

export const OPENING_DATA_CREDIT = 'Data: NASA FIRMS · MODIS C6.1 (Aqua) · VIIRS C2 (S-NPP, NOAA-20)';

// A série usa o MODIS só do Aqua e um VIIRS por vez: S-NPP até 2 nov 2026, NOAA-20 depois.
export const SPACECRAFT_LABELS = [
  { sensor: 'MODIS', spacecraft: 'Aqua' },
  { sensor: 'VIIRS', spacecraft: 'S-NPP → NOAA-20' },
] as const;
