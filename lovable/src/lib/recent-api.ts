import type { RecentData, Viewport } from "./recent-data";
const base = import.meta.env["VITE_API_URL"]?.replace(/\/$/, "") || "http://localhost:8000";
export class RecentApiError extends Error {
  constructor(
    public status: number,
    public retryAfter: number | null,
    message: string,
  ) {
    super(message);
  }
}
async function request(path: string, signal: AbortSignal, body?: unknown, binary = false) {
  const response = await fetch(`${base}/api/v1/${path}`, {
    signal,
    ...(body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
  });
  if (!response.ok) {
    const retry = response.headers.get("Retry-After");
    const seconds = retry
      ? /^\d+$/.test(retry)
        ? Number(retry)
        : Math.max(0, Math.ceil((Date.parse(retry) - Date.now()) / 1000))
      : null;
    throw new RecentApiError(
      response.status,
      seconds,
      response.status === 429
        ? `Too many requests. Try again${seconds == null ? " later." : ` in ${seconds} s.`}`
        : "API unavailable.",
    );
  }
  return binary ? response.blob() : response.json();
}
export async function fetchRecent(
  view: Viewport,
  hours: number,
  signal: AbortSignal,
): Promise<RecentData> {
  const data = await request(
    `detections/recent?${new URLSearchParams({ bbox: view.bbox.join(","), hours: String(hours), zoom: String(view.zoom), mode: "auto" })}`,
    signal,
  );
  if (
    data.type !== "FeatureCollection" ||
    !Array.isArray(data.features) ||
    typeof data.updated_at !== "string" ||
    data.hours !== hours ||
    typeof data.total_detections !== "number"
  )
    throw new Error("Recent response is incomplete or belongs to another window.");
  return data;
}
// Only the GeoJSON envelope is fully specified by the supplied briefing.
export const fetchAreaHistory = (geometry: unknown, signal: AbortSignal) =>
  request("calendar", signal, { area: { type: "geojson", geometry } });
// Export's envelope was not supplied: do not guess it.
