import { useCallback, useEffect, useRef, useState } from 'react';
import example from '../../../docs/api-exemplo.json';
import { fetchCalendar, fetchHealth, fetchRegions } from '../api/client';
import type { AreaInput, CalendarRequest, CalendarResponse, RegionOption } from '../api/types';
import { buildCalendarRequest, DEFAULT_START_MONTH, isDataStale } from '../controls/areaPeriodModel';
import { classifyFailure, describeArea, resultFromResponse, type ResultState } from './explorerModel';

export const demoData = example as unknown as CalendarResponse;

export interface Selection {
  area: AreaInput | null; // null = área de demonstração do JSON de exemplo
  label: string;
  isExample: boolean;
}

export interface Period {
  start: string;
  end: string;
}

export type ApiStatus = 'checking' | 'online' | 'offline';

const DEMO_SELECTION: Selection = {
  area: null,
  label: 'Example area · Amazônia biome',
  isExample: true,
};

export interface Explorer {
  apiStatus: ApiStatus;
  regions: RegionOption[];
  lastMonth: string;
  selection: Selection;
  period: Period;
  result: ResultState;
  shown: { data: CalendarResponse; isDemo: boolean } | null;
  stale: boolean;
  periodIgnoredInDemo: boolean;
  selectArea: (area: AreaInput, period?: Period) => void;
  setPeriod: (period: Period) => void;
  showExample: () => void;
  retry: () => void;
  request: CalendarRequest | null;
}

export function useExplorer(): Explorer {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking');
  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [lastMonth, setLastMonth] = useState(demoData.meta.last_month);
  const [selection, setSelection] = useState<Selection>(DEMO_SELECTION);
  const [period, setPeriodState] = useState<Period>({ start: DEFAULT_START_MONTH, end: demoData.meta.last_month });
  const [result, setResult] = useState<ResultState>({ kind: 'demo' });
  const [lastReady, setLastReady] = useState<CalendarResponse | null>(null);
  const [exampleRegion, setExampleRegion] = useState<RegionOption | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const userActedRef = useRef(false);
  const regionsRef = useRef<RegionOption[]>([]);

  const run = useCallback((area: AreaInput, nextPeriod: Period) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setResult({ kind: 'loading' });
    const req = buildCalendarRequest(area, nextPeriod);
    return fetchCalendar(req, controller.signal).then(
      (response) => {
        if (controller.signal.aborted) return null;
        const next = resultFromResponse(response);
        setResult(next);
        if (next.kind === 'ready') {
          setLastReady(next.data);
          setApiStatus('online');
        }
        return next;
      },
      (err: unknown) => {
        if (controller.signal.aborted) return null;
        const failure = classifyFailure(err);
        setResult(failure);
        if (failure.kind === 'api_unavailable') setApiStatus('offline');
        return failure;
      },
    );
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.allSettled([fetchHealth(controller.signal), fetchRegions(controller.signal)]).then(([health, regionList]) => {
      if (controller.signal.aborted) return;
      if (health.status === 'fulfilled' && health.value.last_month) {
        setLastMonth(health.value.last_month);
        setPeriodState((p) => ({ ...p, end: health.value.last_month }));
      }
      if (regionList.status === 'fulfilled') {
        regionsRef.current = regionList.value;
        setRegions(regionList.value);
      }
      const online = health.status === 'fulfilled' || regionList.status === 'fulfilled';
      setApiStatus(online ? 'online' : 'offline');

      // Com a API no ar, o exemplo deixa de ser o JSON de demonstração e passa a ser a primeira região real.
      const first = regionList.status === 'fulfilled' ? regionList.value[0] : undefined;
      if (!first) return;
      setExampleRegion(first);
      const end = health.status === 'fulfilled' ? health.value.last_month : demoData.meta.last_month;
      const area: AreaInput = { type: 'region', region_id: first.region_id };
      fetchCalendar(buildCalendarRequest(area, { start: DEFAULT_START_MONTH, end }), controller.signal)
        .then((response) => {
          const next = resultFromResponse(response);
          if (next.kind !== 'ready') return;
          if (!userActedRef.current) {
            setSelection({ area, label: first.name, isExample: true });
            setResult(next);
            setLastReady(next.data);
          }
        })
        .catch(() => undefined);
    });
    return () => {
      controller.abort();
      abortRef.current?.abort();
    };
  }, []);

  const selectArea = useCallback(
    (area: AreaInput, nextPeriod?: Period) => {
      userActedRef.current = true;
      setSelection({
        area,
        label: describeArea(area, regionsRef.current),
        isExample: false,
      });
      if (nextPeriod) setPeriodState(nextPeriod);
      void run(area, nextPeriod ?? period);
    },
    [period, run],
  );

  const setPeriod = useCallback(
    (next: Period) => {
      userActedRef.current = true;
      setPeriodState(next);
      if (selection.area) void run(selection.area, next);
    },
    [run, selection.area],
  );

  const showExample = useCallback(() => {
    userActedRef.current = true;
    abortRef.current?.abort();
    if (exampleRegion) {
      const area: AreaInput = { type: 'region', region_id: exampleRegion.region_id };
      setSelection({ area, label: exampleRegion.name, isExample: true });
      void run(area, period);
      return;
    }
    setSelection(DEMO_SELECTION);
    setResult({ kind: 'demo' });
  }, [exampleRegion, period, run]);

  const retry = useCallback(() => {
    if (selection.area) void run(selection.area, period);
  }, [period, run, selection.area]);

  let shown: Explorer['shown'] = null;
  if (result.kind === 'ready') shown = { data: result.data, isDemo: false };
  else if (result.kind === 'demo' || result.kind === 'api_unavailable') shown = { data: demoData, isDemo: true };
  else if (result.kind === 'loading') shown = lastReady ? { data: lastReady, isDemo: false } : { data: demoData, isDemo: true };

  return {
    apiStatus,
    regions,
    lastMonth,
    selection,
    period,
    result,
    shown,
    stale: result.kind === 'ready' && isDataStale(result.data.meta.updated_at),
    periodIgnoredInDemo:
      selection.area === null && (period.start !== DEFAULT_START_MONTH || period.end !== demoData.meta.last_month),
    selectArea,
    setPeriod,
    showExample,
    retry,
    request: selection.area ? buildCalendarRequest(selection.area, period) : null,
  };
}
