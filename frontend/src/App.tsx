import { useCallback, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { MONTH_NAMES } from './calendar/calendarModel';
import { SelectionPanel } from './controls/SelectionPanel';
import { buildExampleStory } from './discovery/exampleStory';
import { HeroCalendar } from './hero/HeroCalendar';
import { prefersReducedMotion } from './hero/heroIntro';
import { HistoryPanel } from './history/HistoryPanel';
import { IndicatorRow } from './summary/IndicatorRow';
import { MapStage } from './map/MapStage';
import { useExplorer } from './state/useExplorer';
import { Summary } from './summary/Summary';

function monthLabel(key: string): string {
  const [y, m] = key.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

function scrollToExplore() {
  document.getElementById('explore')?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
}

// Três momentos ligados: entender (abertura), descobrir (exemplo guiado) e investigar (área própria).
export function App() {
  const ex = useExplorer();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [storyIndex, setStoryIndex] = useState(0);
  const heroHost = typeof document !== 'undefined' ? document.getElementById('hero-viz') : null;

  const shownData = ex.shown?.data ?? null;
  const story = useMemo(() => (shownData ? buildExampleStory(shownData) : null), [shownData]);
  const step = ex.selection.isExample && story ? story[storyIndex] : null;

  const months = shownData?.months ?? [];
  const periodLabel = months.length ? `${monthLabel(months[0].month)} – ${monthLabel(months[months.length - 1].month)}` : `${ex.period.start} – ${ex.period.end}`;
  const showingDemoForOtherArea = ex.result.kind === 'api_unavailable' && !ex.selection.isExample;
  const areaLabel = ex.shown?.isDemo ? 'Example area, Amazônia biome (demo data)' : ex.selection.label;

  const openExample = useCallback(
    (monthKey: string | null) => {
      ex.showExample();
      setStoryIndex(0);
      setSelectedKey(monthKey);
      scrollToExplore();
    },
    [ex],
  );

  const selectArea: typeof ex.selectArea = (area) => {
    setSelectedKey(null);
    ex.selectArea(area);
  };

  let statusChip = <span className="chip chip--live">NASA FIRMS data</span>;
  if (ex.result.kind === 'loading') statusChip = <span className="chip chip--muted">Loading…</span>;
  else if (showingDemoForOtherArea) statusChip = <span className="chip chip--demo">Demo data, not this area</span>;
  else if (ex.shown?.isDemo) statusChip = <span className="chip chip--demo">Demo data</span>;
  else if (ex.result.kind === 'no_coverage') statusChip = <span className="chip chip--muted">Outside coverage</span>;
  else if (ex.result.kind === 'error' || ex.result.kind === 'rate_limited') statusChip = <span className="chip chip--muted">Not loaded</span>;

  return (
    <>
      {heroHost &&
        createPortal(
          <HeroCalendar months={ex.hero.data.months} areaLabel={ex.hero.label} isDemo={ex.hero.isDemo} onOpenExample={openExample} />,
          heroHost,
        )}

      <div className="workspace">
        <div className="selection-bar">
          <h2 id="explore-title" className="selection-bar__title">
            Explore an area
          </h2>
          <dl className="selection-bar__fields">
            <div>
              <dt>Area</dt>
              <dd>{ex.selection.label}</dd>
            </div>
            <div>
              <dt>Period</dt>
              <dd>{periodLabel}</dd>
            </div>
          </dl>
          <div className="selection-bar__status">{statusChip}</div>
        </div>

        {showingDemoForOtherArea && (
          <p className="dark-notice" role="status">
            <strong>API unavailable.</strong> Your area is outlined on the map, but the figures below belong to the demo example.
          </p>
        )}

        {ex.shown && <IndicatorRow indicators={ex.shown.data.indicators} isDemo={ex.shown.isDemo} />}

        <div className="ws-top">
          <div className="ws-map">
            <SelectionPanel
              regions={ex.regions}
              apiStatus={ex.apiStatus}
              selection={ex.selection}
              period={ex.period}
              lastMonth={ex.lastMonth}
              onSelectArea={selectArea}
              onSetPeriod={ex.setPeriod}
              onShowExample={() => openExample(null)}
            />
            <MapStage
              shape={ex.selection.shape}
              startOnArrival={ex.selection.isExample}
              onSelectPolygon={(geometry) => selectArea({ type: 'geojson', geometry })}
            />
          </div>
          <Summary
            shown={ex.shown}
            result={ex.result}
            stale={ex.stale}
            selectionIsExample={ex.selection.isExample}
            periodIgnoredInDemo={ex.periodIgnoredInDemo}
            story={story}
            storyIndex={storyIndex}
            onStoryIndex={setStoryIndex}
            onRetry={ex.retry}
          />
        </div>

        <HistoryPanel
          shown={ex.shown}
          result={ex.result}
          selectedKey={selectedKey}
          onSelectKey={setSelectedKey}
          highlightMonthIndex={step?.monthIndex ?? null}
          highlightYear={step?.year ?? null}
          areaLabel={areaLabel}
          periodLabel={periodLabel}
          request={ex.request}
        />
      </div>
    </>
  );
}
