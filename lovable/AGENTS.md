<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.

## What Lovable manages

Rules outside this block are the project's own. Change the pieces below in
Lovable, not by hand. With the [Lovable MCP](https://mcp.lovable.dev)
connected, `send_message` asks Lovable to do it; otherwise ask the user to
use the editor.

- **Database.** Do not add or edit `supabase/migrations/` or `drizzle/`.
  Ask Lovable to change the schema.
- **Generated files.** Do not edit a file whose header says it is automatically
  generated.
- **AI gateway.** Keep model calls on Lovable's gateway, and keep
  `LOVABLE_API_KEY` out of browser code.
- **Connectors.** Lovable provides native connectors. `list_connectors` shows
  which are enabled; `add_connector` only returns the dashboard link. When a
  connector is enabled, calls go through the connector gateway and need
  `LOVABLE_API_KEY`. When Lovable does not provide one, users can bring their
  own key and store it in Secrets.
- **Secrets.** Lovable manages them. Do not put secret values in the repo.
<!-- LOVABLE:END -->

## Application architecture
- Keep routing on TanStack Start, with content-specific metadata and separate Explore, Method and Data routes; this preserves the project's framework and typed navigation.
- Keep fixture types/formatting in fire-data, browser-only API requests in fire-api and focused visualizations in firesync components; scientific values must not be computed by presentation code.
- Import Leaflet/Geoman only through a lazy client-only map; their browser dependencies must not execute during SSR.
- Use only the external browser API through VITE_API_URL (recent workspace defaults to localhost:8000); the supplied briefing documents recent bbox requests and GeoJSON calendar requests, while coordinate and export envelopes still require confirmation.
- Use global semantic design tokens for all visual roles; D3-generated Cividis colors are reserved for data marks.
- Keep calendar month selection click/keyboard-driven and details in normal document flow; passive pointer movement must not open overlays or obscure the record.
- Compare years in a focused monthly line visualization with January–December on the horizontal axis and supplied monthly counts; preserve missing-month gaps and mark incomplete/provisional observations without extrapolation.
- Load the immersive historical map lazily on the client and decode official NASA GIBS vector tiles; label fixed-date snapshots separately from the harmonized fixture so geographic observations never imply annual totals.
- Render the opening with a lazy client-only Three.js scene and token-based materials; satellite geometry and orbital motion are explicitly illustrative, independent of historical selection, and never substitute for geographic observations or alerts.
- Preload the Earth image and defer spacecraft downloads and map initialization until it is textured to prioritize the opening; apply idle rotation only to single-sample texture coordinates, preserving the original unrotated morph vertices and camera path. Discard original back-hemisphere depth only during flattening to prevent folded duplicate geography.
- Use NASA public-domain Aqua and Suomi NPP GLBs as the MODIS/VIIRS platforms, with credits beside the files; preserve their geometry and label orbital paths and relative scale as illustrative.
- Keep every binary asset (Earth textures, spacecraft models, country boundaries) as a real file in `src/assets/`, imported with `?url`, never as a Lovable-hosted `*.asset.json` pointer: the app must run from a git clone with `npm install` and `npm run dev`, without Lovable hosting.
- Drive the pinned opening transition from native document scroll through a frame-smoothed shared progress ref; gate map interaction on loaded imagery and a finished blend, keep an explicit return-to-globe control, and disable spatial motion for reduced-motion users.
- Morph the opening's geographic mesh from sphere to Mercator while moving the camera toward its surface; share framing and NASA tile URLs with Leaflet, blend the exact destination tiles onto the mesh before handoff, and wait for both surfaces so imagery and coastlines persist. Share selected geometry with the index calendar and retain independent demo labeling.
- Keep historical year controls in the data visualizations, not the illustrative opening; opening controls must affect the actual scene or geographic selection.
- Restore the immersive map's shared surface center and zoom only after its reverse-scroll blend is fully hidden, cancelling inertia and preserving selected geometry; every subsequent globe handoff must remain aligned without a visible reset.
- Keep the recent workspace separate from the unchanged orbital scene; use the existing lazy Leaflet surface, viewport-keyed abortable requests and compact Geoman area controls so overlays cannot change the geographic handoff.
- Keep both geographic surfaces at fixed full-viewport dimensions throughout scrolling to avoid repeated renderer resizing and atlas reloads; fade overlay navigation out of interaction during descent and use standard backdrop-filter with semantic glass tokens on map controls only.
- Reserve a native sticky-scroll hold after geographic arrival, separate from zoom progress and chapter destinations; briefly defer wheel zoom on activation so the arrival gesture does not move the map.
- On home-page mount, normalize its hash through TanStack navigation and reset to the globe; allow subsequent in-page record links normally so reload does not bypass the opening.
- Preload a reduced-resolution Earth texture for the actual interactive globe, then upgrade with a separate full-resolution texture; never show a frozen scene snapshot as loading feedback.
- Use one registered texture during the geographic morph instead of crossfading differently registered Earth imagery; finish idle texture rotation before atlas activation to prevent duplicated coastlines without changing camera or vertices.
- Keep recent fixture, rules and API requests in dedicated browser-safe modules; demo viewport counts use only the supplied geometry, never the national total whose other geometry is absent.

- Keep recent-map information click-open with compact glass controls and one detail panel at a time; the geographic surface must remain the primary view.

- Share the map's 24h summary; filter states only with official bounds.
