import { describe, expect, it } from "vitest";
import {
  OPENING_AUDIENCE,
  OPENING_CHAPTERS,
  OPENING_DATA_CREDIT,
  SPACECRAFT_LABELS,
} from "../lib/opening-copy";

describe("opening copy", () => {
  it("labels the spacecraft the harmonized record actually uses: Aqua for MODIS, S-NPP then NOAA-20 for VIIRS", () => {
    expect(SPACECRAFT_LABELS).toEqual([
      { sensor: "MODIS", spacecraft: "Aqua" },
      { sensor: "VIIRS", spacecraft: "S-NPP → NOAA-20" },
    ]);
    expect(JSON.stringify(SPACECRAFT_LABELS)).not.toMatch(/Terra|Suomi/);
  });

  it("opens with the question only firesync answers, followed by the record and the present", () => {
    expect(OPENING_CHAPTERS.map((chapter) => chapter.label)).toEqual([
      "Our planet",
      "The record",
      "Your place",
    ]);
    expect(OPENING_CHAPTERS.map((chapter) => chapter.title)).toEqual([
      ["Is this fire normal?", "Here, this season."],
      ["Different sensors.", "One shared history."],
      ["The present.", "In context."],
    ]);
    expect(OPENING_CHAPTERS[0]?.copy).toBe(
      "FIRMS shows where fire is. firesync tells you if it's normal.",
    );
    expect(OPENING_CHAPTERS[1]?.copy).toBe(
      "MODIS and VIIRS harmonized into one monthly record since 2003, with the uncertainty shown.",
    );
    expect(OPENING_CHAPTERS[2]?.copy).toBe(
      "Compare the last 7 days with what is typical for the same area and season.",
    );
  });

  it("names the NASA products with their versions and says who the tool is for", () => {
    expect(OPENING_DATA_CREDIT).toBe(
      "Data: NASA FIRMS · MODIS C6.1 (Aqua) · VIIRS C2 (S-NPP, NOAA-20)",
    );
    expect(OPENING_AUDIENCE).toBe(
      "NASA Space Apps · for fire brigades, civil defense and land managers",
    );
  });
});
