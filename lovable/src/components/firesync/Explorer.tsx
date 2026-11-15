import { lazy, Suspense, useEffect, useState } from 'react';
import { ClientOnly } from '@tanstack/react-router';
import { ArrowUpRight, MapPin, SlidersHorizontal, RefreshCw, ChevronDown, Crosshair, Info, LoaderCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Calendar } from './Calendar';
import { HistoryCharts, RecentChart } from './Charts';
import type { AreaSelection } from './AreaMap';
import { apiConfigured, getRegions, type Region } from '@/lib/fire-api';
import { demoData, number, percent } from '@/lib/fire-data';
const AreaMap = lazy(() => import('./AreaMap'));

export function Explorer({ selection: providedSelection, onSelect, hideMap = false }: { selection?: AreaSelection | null; onSelect?: (area: AreaSelection | null) => void; hideMap?: boolean }) {
  const [localSelection, setLocalSelection] = useState<AreaSelection | null>(null);
  const selection = providedSelection === undefined ? localSelection : providedSelection;
  const setSelection = onSelect ?? setLocalSelection;
  const [controls, setControls] = useState(false);
  const [regions, setRegions] = useState<Region[]>([]);
  const [apiState, setApiState] = useState('');
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState('2003');
  const [end, setEnd] = useState('2026');
  const [latitude, setLatitude] = useState('-7.5'); const [longitude, setLongitude] = useState('-59'); const [radius, setRadius] = useState('50');
  async function loadRegions() {
    setLoading(true); setApiState('');
    try { const response = await getRegions(); setRegions(Array.isArray(response) ? response : response.regions); } catch (e) { setApiState(e instanceof Error ? e.message : 'API unavailable.'); } finally { setLoading(false); }
  }
  useEffect(() => { if (apiConfigured) void loadRegions(); }, []);
  const recent = demoData.recent.last_7_days;
  const data = { ...demoData, months: demoData.months.filter(m => m.month.slice(0, 4) >= period && m.month.slice(0, 4) <= end) };
  const areaName = selection?.type === 'geojson' && selection.name ? selection.name : selection ? 'Custom selection' : 'Amazon biome · Example area';
  return <section id="investigate" className="explorer-section"><div className="explorer-heading"><div><span className="eyebrow">Explore a place</span><h2>Every place has a pattern.</h2></div><p>Find the season. Put the present in perspective.</p></div>
    <div className="selection-bar"><div className="area-selection"><MapPin size={17} /><strong>{areaName}</strong><span className="demo-badge">Demo data</span></div><div className="period-selection"><span>Period</span><select aria-label="Start year" value={period} onChange={e => { setPeriod(e.target.value); if (e.target.value > end) setEnd(e.target.value); }}>{Array.from({ length: 24 }, (_, i) => <option key={i}>{2003 + i}</option>)}</select><span>—</span><select aria-label="End year" value={end} onChange={e => { setEnd(e.target.value); if (e.target.value < period) setPeriod(e.target.value); }}>{Array.from({ length: 24 }, (_, i) => <option key={i}>{2003 + i}</option>)}</select><Button variant="outline" size="sm" onClick={() => setControls(!controls)} aria-expanded={controls}><SlidersHorizontal /> Area <ChevronDown /></Button></div></div>
    {controls && <form className="area-controls" onSubmit={e => { e.preventDefault(); setSelection({ type: 'circle', latitude: Number(latitude), longitude: Number(longitude), radius_km: Number(radius) }); }}><label>Latitude<input type="number" min="-90" max="90" step="any" required value={latitude} onChange={e => setLatitude(e.target.value)} /></label><label>Longitude<input type="number" min="-180" max="180" step="any" required value={longitude} onChange={e => setLongitude(e.target.value)} /></label><label>Radius (km)<input type="number" min="0.1" step="any" required value={radius} onChange={e => setRadius(e.target.value)} /></label><Button type="submit"><Crosshair />Select area</Button><label className="region-field">Available regions<select aria-label="Available API regions" disabled={!regions.length} onChange={e => setSelection({ type: 'region', region_id: Number(e.target.value) })}><option value="">{regions.length ? 'Select region' : 'Requires production API'}</option>{regions.map(r => <option key={r.region_id ?? r.id} value={r.region_id ?? r.id}>{r.name}</option>)}</select></label><Button variant="ghost" type="button" onClick={() => { setSelection(null); setLatitude('-7.5'); setLongitude('-59'); }}><RefreshCw />Reset example</Button></form>}
    <div className={`analysis-layout ${hideMap ? 'analysis-without-map' : ''}`}>{!hideMap && <div className="map-panel"><div className="map-label"><span className="live-dot" />Area explorer<span>No point fixtures available</span></div><ClientOnly fallback={<div className="map-loading"><LoaderCircle />Loading map</div>}><Suspense fallback={<div className="map-loading"><LoaderCircle />Loading map</div>}><AreaMap selection={selection} onSelect={setSelection} /></Suspense></ClientOnly><div className="map-caption"><MapPin size={14} /><span>{selection ? 'Selected geometry · No production results loaded' : 'Amazon biome context · Exact example boundary not supplied'}</span></div></div>}
    <aside className="area-summary"><div className="summary-top"><span className="eyebrow">The recent picture</span><span className="demo-badge">Demo data</span></div><h3>Is recent fire activity<br />typical here?</h3><div className="summary-period">Last 7 days <span>08–14 NOV 2026</span></div><div className="recent-stat"><div><strong>{number(recent.detections)}</strong><span>fire detections</span></div><div className="difference-stat"><ArrowUpRight /><strong>{percent(recent.difference_pct)}</strong><span>vs. typical median</span></div></div><RecentChart recent={recent} /><div className="comparison-key"><span className="band-key" />Typical range (P25–P75)<span className="current-key" />Current</div><p className="evidence">Above the typical range for this time of year<span>61 detections vs. a typical range of 35.2–45.5.</span></p><div className="mtd-stat"><span>Month to date<strong>{number(demoData.recent.month_to_date.detections)} detections</strong></span><span>{percent(demoData.recent.month_to_date.difference_pct)}<small>vs. typical median</small></span></div><p className="update-note">Data through 14 Nov 2026 · Current month incomplete.<br />Recent months are provisional.</p><a href="#history" className="history-link">See the longer history</a></aside></div>
    <div className="demo-notice"><Info size={16} /><p><strong>Illustrative data, not a measured finding.</strong> {selection ? 'Your selection is outlined on the map. The calendar and summary still show the supplied example, not results for this area.' : 'The supplied fixture contains made-up values for an 8,707 km² area in the Amazon biome. Its exact boundary is not included.'} {apiConfigured ? 'The missing api.md contract must be confirmed before production queries can be submitted.' : 'Production API is not connected.'}</p><Button variant="ghost" size="sm" onClick={loadRegions} disabled={loading}>{loading ? <LoaderCircle className="spin" /> : <RefreshCw />}{loading ? 'Checking' : 'Check API'}</Button></div>{apiState && <div className="api-message" role="status">{apiState}<Button variant="outline" size="sm" onClick={loadRegions}>Try again</Button></div>}
    <div id="history" className="full-history"><Calendar data={data} /><HistoryCharts data={demoData} /></div>
  </section>;
}