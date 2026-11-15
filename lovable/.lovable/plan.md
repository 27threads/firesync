# Connect the firesync opening to recent detections

## What will change
- Keep the restored globe and illustrative satellite orbits. Use the supplied question and supporting text, with direct **Explore an area** and **View historical calendar** actions. Keep mobile controls minimal and respect reduced motion.
- Add **Recent satellite detections** with **24 h / 72 h / 7 days** selection, NASA FIRMS attribution, data-update time and observation details when provided.
- Fit the map to a selected place and show only its associated results: detections in the selected window, the separate seven-day seasonal comparison, coverage, update status and corresponding history.
- Keep the monthly calendar, seasonal charts, annual ranking and downloads below the map, preserving scientific uncertainty and incomplete/provisional indicators.
- Separate the explicitly chosen **Demo — example area** from real selections. Show loading, zero detections, missing/partial coverage, stale data and query failures without invented fallback values or danger classifications.

## Required for real-data acceptance
The project does not contain `docs/api.md`. The briefing also says the revised HTTP endpoints are not yet delivered. Provide that contract and the production API URL with working browser access before connecting requests or claiming real-data acceptance. Frontend presentation and honest unavailable states can be implemented first; real detections and matching history remain blocked until those inputs arrive.

## Technical approach
- Preserve TanStack Start, existing components and the external browser API configured through `VITE_API_URL`; do not create a replacement backend.
- Implement documented request/response types only after receiving the contract. Abort superseded requests and key results by selection and time window so previous responses cannot appear under a new place.
- Keep API values and missingness outside presentation calculations; comparisons must come from the API.
- Test area/window association, cancellation and explicit data states. Verify the selection-to-detections-to-history flow with real API responses on desktop and mobile before marking integration complete.