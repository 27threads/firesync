import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MONTH_NAMES } from './calendar/calendarModel';
import type { AreaInput } from './api/types';
import { AssistantBubble } from './assistant/AssistantBubble';
import { SelectionPanel } from './controls/SelectionPanel';
import { buildExampleStory } from './discovery/exampleStory';
import { prefersReducedMotion } from './hero/heroIntro';
import { HERO_AREA_EVENT } from './hero/heroMapModel';
import { useLeftHero } from './hero/useLeftHero';
import { HistoryPanel } from './history/HistoryPanel';
import { IndicatorRow } from './summary/IndicatorRow';
import { useExplorer } from './state/useExplorer';
import { Summary } from './summary/Summary';
import { Verdict } from './summary/Verdict';

function monthLabel(key: string): string {
  const [y, m] = key.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

// Off unless the build sets VITE_ENABLE_ASSISTANT=true, so the page ships the same without the assistant (RFC 0004).
const ASSISTANT_ENABLED = import.meta.env.VITE_ENABLE_ASSISTANT === 'true';

function scrollToExplore() {
  document.getElementById('explore')?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
}

// Três momentos ligados: entender (abertura), descobrir (exemplo guiado) e investigar (área própria).
export function App() {
  const ex = useExplorer();
  const leftHero = useLeftHero();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [storyIndex, setStoryIndex] = useState(0);

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

  const selectArea: typeof ex.selectArea = (area, period) => {
    setSelectedKey(null);
    ex.selectArea(area, period);
  };

  // An area chosen on the hero map (region, drawing or coordinates) becomes the explorer's area too.
  const selectAreaRef = useRef(selectArea);
  selectAreaRef.current = selectArea;
  useEffect(() => {
    const onHeroArea = (event: Event) => selectAreaRef.current((event as CustomEvent<AreaInput>).detail);
    window.addEventListener(HERO_AREA_EVENT, onHeroArea);
    return () => window.removeEventListener(HERO_AREA_EVENT, onHeroArea);
  }, []);

  // Mesma condição do resumo: sem erro e sem área fora da cobertura.
  const hasAnswer = ['ready', 'demo', 'api_unavailable', 'loading'].includes(ex.result.kind);

  let statusChip = <span className="chip chip--live">NASA FIRMS data</span>;
  if (ex.result.kind === 'loading') statusChip = <span className="chip chip--muted">Loading…</span>;
  else if (showingDemoForOtherArea) statusChip = <span className="chip chip--demo">Demo data, not this area</span>;
  else if (ex.shown?.isDemo) statusChip = <span className="chip chip--demo">Demo data</span>;
  else if (ex.result.kind === 'no_coverage') statusChip = <span className="chip chip--muted">Outside coverage</span>;
  else if (ex.result.kind === 'error' || ex.result.kind === 'rate_limited') statusChip = <span className="chip chip--muted">Not loaded</span>;

  return (
    <>
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

        {/* Right after the hero map: the fire calendar of the chosen area. */}
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

        {ex.shown && hasAnswer && <Verdict window={ex.shown.data.recent.last_7_days} areaLabel={areaLabel} />}

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

      </div>

      {ASSISTANT_ENABLED && (
        <AssistantBubble
          hideBubble={!leftHero}
          onShowCalendar={(action) => {
            selectArea(action.area, action.start && action.end ? { start: action.start, end: action.end } : undefined);
            scrollToExplore();
          }}
        />
      )}
    </>
  );
}
