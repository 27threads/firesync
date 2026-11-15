import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { ClientOnly } from '@tanstack/react-router';
import { Play, Pause } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Header } from './Shell';
import type { AreaSelection } from './AreaMap';
import { journeyTransitionDistance, smoothPhase } from '@/lib/globe-transition';
import { demoInView, recentTotals, type RecentData } from '@/lib/recent-data';
import { number } from '@/lib/fire-data';
const RecentWorkspace = lazy(() => import('./RecentWorkspace'));
const OrbitalScene = lazy(() => import('./OrbitalScene'));
const chapters = [
  { label: 'Our planet', title: <>One Earth.<br />A longer perspective.</>, copy: 'Understand fire activity in the places that matter to you.' },
  { label: 'The record', title: <>Different sensors.<br />One shared history.</>, copy: 'Explore monthly detections from MODIS and VIIRS, since 2003.' },
  { label: 'Your place', title: <>The present.<br />In context.</>, copy: 'Compare recent activity with the seasonal record of an area.' },
];

export function MapOpening({ selection, onSelect }: { selection: AreaSelection | null; onSelect: (area: AreaSelection | null) => void }) {
  const [playing, setPlaying] = useState(true);
  const [chapter, setChapter] = useState(0);
  const [mapActive, setMapActive] = useState(false);
  const [resetForHandoff, setResetForHandoff] = useState(true);
  const [navigationHidden, setNavigationHidden] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [surfaceReady, setSurfaceReady] = useState(false);
  const [globeReady, setGlobeReady] = useState(false);
  const [recentSummary, setRecentSummary] = useState<{ data: RecentData; demo: boolean }>({ data: demoInView({ bbox: [-80, -40, -30, 15], zoom: 4 }), demo: true });
  const totals = recentTotals(recentSummary.data);
  const readiness = useRef(false);
  useEffect(() => { readiness.current = mapReady && surfaceReady; }, [mapReady, surfaceReady]);
  const opening = useRef<HTMLElement>(null);
  const progress = useRef(0);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) setPlaying(false);
  }, []);
  useEffect(() => {
    const element = opening.current;
    if (!element) return;
    let frame = 0;
    let previous = performance.now();
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      const distance = journeyTransitionDistance(element.offsetHeight, window.innerHeight);
      const target = Math.max(0, Math.min(1, -element.getBoundingClientRect().top / distance));
      const now = performance.now();
      const delta = Math.min((now - previous) / 1000, 0.05);
      previous = now;
      const value = reduced.matches ? target : progress.current + (target - progress.current) * (1 - Math.exp(-delta * 9));
      progress.current = Math.abs(target - value) < 0.001 ? target : value;
      const blend = readiness.current ? smoothPhase(value, 0.9, 0.98) : 0;
      element.style.setProperty('--journey-progress', String(value));
      element.style.setProperty('--map-blend', String(blend));
      element.style.setProperty('--surface-approach', String(smoothPhase(value, 0.02, 0.75)));
      element.style.setProperty('--opening-chrome', String(1 - smoothPhase(value, 0.05, 0.35)));
      element.dataset['journeyProgress'] = value.toFixed(3);
      setChapter(value < 0.25 ? 0 : value < 0.6 ? 1 : 2);
      setMapActive(readiness.current && value >= 0.98 && target >= 0.98);
      setResetForHandoff(value <= 0.9 && target <= 0.9);
      setNavigationHidden(value >= 0.35);
      frame = requestAnimationFrame(update);
    };
    update();
    return () => { cancelAnimationFrame(frame); };
  }, []);
  const showChapter = (index: number) => {
    const element = opening.current;
    if (!element) return;
    const destination = [0, 0.3, 1][index] ?? 0;
    window.scrollTo({ top: window.scrollY + element.getBoundingClientRect().top + journeyTransitionDistance(element.offsetHeight, window.innerHeight) * destination, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  };
  const content = chapters[chapter] ?? chapters[0];
  if (!content) return null;
  return <><section className="orbital-opening orbital-journey" ref={opening}><div className="orbital-sticky">
    <div className="orbital-navigation" inert={navigationHidden} aria-hidden={navigationHidden}><Header compactBrand /></div>
    <div className="orbital-stage">
      <ClientOnly fallback={<div className="orbital-canvas" />}><Suspense fallback={<div className="orbital-canvas" />}><OrbitalScene playing={playing} progress={progress} onGlobeReady={() => setGlobeReady(true)} onSurfaceReady={() => setSurfaceReady(true)} /></Suspense></ClientOnly>
      <div className="orbital-copy">
        <span className="eyebrow orbital-kicker">NASA Space Apps · fire observatory</span>
        <h1>firesync<span>.</span></h1>
        <div className="orbital-chapter" key={chapter}><span className="eyebrow">{content.label}</span><h2>{content.title}</h2><p>{content.copy}</p></div>
        <Button size="lg" onClick={() => showChapter(2)}>Explore an area</Button>
        <div className="orbital-presentation-controls">
          <Button variant="ghost" size="icon" aria-label={playing ? 'Pause presentation' : 'Play presentation'} title={playing ? 'Pause presentation' : 'Play presentation'} onClick={() => setPlaying(!playing)}>{playing ? <Pause size={14} /> : <Play size={14} />}</Button>
          {chapters.map((item, index) => <Button key={item.label} variant="ghost" size="icon" className="orbital-step" aria-label={`Show ${item.label.toLowerCase()}`} aria-pressed={index === chapter} title={item.label} onClick={() => showChapter(index)}><span /></Button>)}
        </div>
      </div>
      <div className={`orbital-map-workspace ${mapActive ? 'is-active' : ''}`} aria-hidden={!mapActive} inert={!mapActive}>
         {globeReady && <ClientOnly><Suspense fallback={<div className="map-loading">Loading map…</div>}><RecentWorkspace active={mapActive} resetForHandoff={resetForHandoff} selection={selection} onSelect={onSelect} onReady={() => setMapReady(true)} onReturn={() => showChapter(0)} onRecentSummary={(data, demo) => setRecentSummary({ data, demo })} /></Suspense></ClientOnly>}
      </div>
    </div>
    <div className="orbital-foot"><span>Earth & spacecraft: NASA · Illustrative scale & orbits</span><a href="#investigate">Monthly record</a></div>
  </div></section><section className="opening-context" aria-label="About firesync">
    <p>firesync joins NASA fire detections from MODIS (2003 to early 2012) and VIIRS (from February 2012) into one comparable history for Brazil. It shows where fire is active now, whether recent activity is typical for the season, and how the place compares with past years. Data: NASA FIRMS. Built for fire-response teams, land managers and researchers.</p>
    <div className="opening-recent-strip" aria-label="Last 24 hours summary">
      {recentSummary.demo && <span className="demo-badge">Demo data</span>}
      <span>Last 24 hours <strong>{number(totals.detections)}</strong> fire detections</span>
      <span><strong>{number(totals.critical)}</strong> Critical cells · <strong>{number(totals.attention)}</strong> Attention cells</span>
      <a href="#map" onClick={event => { event.preventDefault(); showChapter(2); }}>Open the map</a>
    </div>
  </section></>;
}