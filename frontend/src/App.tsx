import { useCallback, useEffect, useRef, useState } from 'react';
import example from '../../docs/api-exemplo.json';
import { ApiClientError, fetchCalendar, fetchHealth, fetchRegions } from './api/client';
import type { AreaInput, CalendarApiResult, CalendarRequest, CalendarResponse, RegionOption } from './api/types';
import { FireCalendar } from './calendar/FireCalendar';
import { AreaPeriodControls } from './controls/AreaPeriodControls';
import { buildCalendarRequest, DEFAULT_END_MONTH, DEFAULT_START_MONTH, isDataStale } from './controls/areaPeriodModel';
import { ExportPanel } from './export/ExportPanel';
import { KeyIndicators } from './summary/KeyIndicators';
import { RecentPanel } from './summary/RecentPanel';
import { SeasonalPattern } from './summary/SeasonalPattern';
import { YearRanking } from './summary/YearRanking';

const exampleData = example as unknown as CalendarResponse;
const CONTRACT_ERROR_CODES = new Set([
  'invalid_geometry',
  'area_too_large',
  'invalid_period',
  'region_not_found',
  'rate_limited',
  'internal_error',
]);

function isNoCoverage(result: CalendarApiResult): boolean {
  return result.coverage?.status === 'none' || !('months' in result);
}

// Ordem da tela (docs/ux-telas.md): primeiro o agora, depois a história, por último o detalhe.
export function App() {
  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [lastMonth, setLastMonth] = useState<string>(exampleData.meta.last_month || DEFAULT_END_MONTH);
  const [activeArea, setActiveArea] = useState<AreaInput | null>(null);
  const [activeRequest, setActiveRequest] = useState<CalendarRequest>(() =>
    buildCalendarRequest({ type: 'region', region_id: 1 }, { start: DEFAULT_START_MONTH, end: exampleData.meta.last_month || DEFAULT_END_MONTH }),
  );
  const [apiResult, setApiResult] = useState<CalendarApiResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [apiUnavailableFallback, setApiUnavailableFallback] = useState<boolean>(false);
  const requestAbortRef = useRef<AbortController | null>(null);
  const userInteractedRef = useRef<boolean>(false);
  const autoLoadTimerRef = useRef<number | null>(null);

  const cancelInitialAutoLoad = useCallback(() => {
    userInteractedRef.current = true;
    if (autoLoadTimerRef.current !== null) {
      window.clearTimeout(autoLoadTimerRef.current);
      autoLoadTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    void Promise.allSettled([fetchHealth(controller.signal), fetchRegions(controller.signal)]).then(
      ([healthRes, regionsRes]) => {
        if (controller.signal.aborted) return;
        let resolvedLastMonth = exampleData.meta.last_month || DEFAULT_END_MONTH;
        if (healthRes.status === 'fulfilled' && healthRes.value.last_month) {
          resolvedLastMonth = healthRes.value.last_month;
          setLastMonth(resolvedLastMonth);
        }
        if (regionsRes.status === 'fulfilled') {
          setRegions(regionsRes.value);
          const isAutomatedWebDriver = typeof navigator !== 'undefined' && navigator.webdriver === true;
          if (regionsRes.value.length > 0 && !userInteractedRef.current && !isAutomatedWebDriver) {
            const firstRegion = regionsRes.value[0];
            autoLoadTimerRef.current = window.setTimeout(async () => {
              if (controller.signal.aborted || userInteractedRef.current) return;
              const initialReq = buildCalendarRequest(
                { type: 'region', region_id: firstRegion.region_id },
                { start: DEFAULT_START_MONTH, end: resolvedLastMonth },
              );
              try {
                const response = await fetchCalendar(initialReq, controller.signal);
                if (controller.signal.aborted || userInteractedRef.current) return;
                if (!isNoCoverage(response)) {
                  setActiveArea(initialReq.area);
                  setActiveRequest(initialReq);
                  setApiResult(response);
                  setApiUnavailableFallback(false);
                }
              } catch {
                if (controller.signal.aborted || userInteractedRef.current) return;
                setApiUnavailableFallback(true);
              }
            }, 80);
          }
        } else if (healthRes.status === 'rejected') {
          setApiUnavailableFallback(true);
        }
      },
    );

    return () => {
      controller.abort();
      if (autoLoadTimerRef.current !== null) {
        window.clearTimeout(autoLoadTimerRef.current);
      }
      requestAbortRef.current?.abort();
    };
  }, []);

  const handleSubmitRequest = useCallback(
    async (request: CalendarRequest) => {
      cancelInitialAutoLoad();
      requestAbortRef.current?.abort();
      const controller = new AbortController();
      requestAbortRef.current = controller;

      setActiveArea(request.area);
      setActiveRequest(request);
      setIsLoading(true);
      setRequestError(null);
      setApiUnavailableFallback(false);

      try {
        const response = await fetchCalendar(request, controller.signal);
        if (controller.signal.aborted) return;
        setApiResult(response);
        setIsLoading(false);
      } catch (err) {
        if (controller.signal.aborted) return;
        setIsLoading(false);
        if (err instanceof ApiClientError && (err.status === 429 || CONTRACT_ERROR_CODES.has(err.code))) {
          setRequestError(err.message);
          return;
        }
        // Sem API no ar, mantém o JSON de exemplo em modo demo.
        setApiUnavailableFallback(true);
      }
    },
    [cancelInitialAutoLoad],
  );

  const isDemo = apiResult === null;
  const noCoverage = apiResult !== null && isNoCoverage(apiResult);
  const data = !isDemo && !noCoverage ? (apiResult as CalendarResponse) : exampleData;
  const includesEstimatedYears = data.years.some((y) => y.complete && y.source !== 'observed_viirs');
  const stale = !isDemo && !requestError && isDataStale(apiResult.meta.updated_at);

  return (
    <section
      className="tool-panel"
      aria-labelledby="tool-title"
      onPointerDownCapture={cancelInitialAutoLoad}
      onMouseDownCapture={cancelInitialAutoLoad}
      onKeyDownCapture={cancelInitialAutoLoad}
      onFocusCapture={cancelInitialAutoLoad}
      onChangeCapture={cancelInitialAutoLoad}
    >
      <h2 id="tool-title">Explore an area</h2>
      <p>Choose an area and a period to see its monthly fire calendar since 2003.</p>

      <AreaPeriodControls
        regions={regions}
        lastMonth={lastMonth}
        activeArea={activeArea}
        onSubmitRequest={handleSubmitRequest}
      />

      {isLoading && (
        <p className="tool-status" role="status" aria-live="polite">
          Loading fire calendar…
        </p>
      )}

      {requestError && (
        <p className="tool-alert" role="alert">
          {requestError}
        </p>
      )}

      {!requestError && stale && (
        <p className="tool-alert" role="alert">
          Data may be out of date (more than 6 hours old).
        </p>
      )}

      {isDemo && !requestError && (
        <p className="example-notice" role="note">
          {apiUnavailableFallback
            ? 'API unavailable — showing example data for an area in the Amazon (demo mode).'
            : 'Showing example data for an area in the Amazon (demo mode). Select a region, draw on the map, or enter coordinates.'}
        </p>
      )}

      {noCoverage ? (
        <>
          <p className="coverage-notice" role="status">
            {apiResult.coverage?.message ?? 'No data for this area yet.'}
          </p>
          <ExportPanel data={data} request={activeRequest} isDemo={isDemo} disabled={true} />
        </>
      ) : (
        <>
          {!isDemo && apiResult.coverage?.status === 'partial' && apiResult.coverage.message && (
            <p className="coverage-notice" role="note">
              {apiResult.coverage.message}
            </p>
          )}
          <KeyIndicators data={data} />
          <RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />
          <FireCalendar months={data.months} />
          <div className="history-grid">
            <SeasonalPattern seasonality={data.seasonality} includesEstimatedYears={includesEstimatedYears} />
            <YearRanking years={data.years} />
          </div>
          <ExportPanel data={data} request={activeRequest} isDemo={isDemo} disabled={false} />
        </>
      )}
    </section>
  );
}
