export type OpeningChapter = { label: string; title: readonly [string, string]; copy: string };

export const OPENING_AUDIENCE =
  "NASA Space Apps · for fire brigades, civil defense and land managers";

export const OPENING_CHAPTERS: readonly OpeningChapter[] = [
  {
    label: "Our planet",
    title: ["Is this fire normal?", "Here, this season."],
    copy: "FIRMS shows where fire is. firesync tells you if it's normal.",
  },
  {
    label: "The record",
    title: ["Different sensors.", "One shared history."],
    copy: "MODIS and VIIRS harmonized into one monthly record since 2003, with the uncertainty shown.",
  },
  {
    label: "Your place",
    title: ["The present.", "In context."],
    copy: "Compare the last 7 days with what is typical for the same area and season.",
  },
];

export const OPENING_DATA_CREDIT =
  "Data: NASA FIRMS · MODIS C6.1 (Aqua) · VIIRS C2 (S-NPP, NOAA-20)";

// The harmonized record uses MODIS from Aqua only and one VIIRS at a time: S-NPP until 2 Nov 2026, NOAA-20 after.
export const SPACECRAFT_LABELS = [
  { sensor: "MODIS", spacecraft: "Aqua" },
  { sensor: "VIIRS", spacecraft: "S-NPP → NOAA-20" },
] as const;
