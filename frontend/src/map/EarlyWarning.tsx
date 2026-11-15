import { useId, useState } from 'react';
import type { RecentAlerts } from '../api/types';
import { priorityView, riskLegendView } from './alertsModel';

interface EarlyWarningProps {
  alerts: RecentAlerts | undefined;
  onFocusCell: (latLng: [number, number]) => void;
}

// Aviso antecipado (RFC 0003): a lista "Where to look first" na ordem da API e, quando há notas, a legenda do risco.
// Sem `alerts`, não desenha nada e o mapa fica como antes. As cores do mapa não mudam (decisão 3 do ux-telas.md).
export function EarlyWarning({ alerts, onFocusCell }: EarlyWarningProps) {
  const [showAll, setShowAll] = useState(false);
  const listId = useId();
  const headingId = useId();
  const legendId = useId();
  const priority = priorityView(alerts, showAll);
  const legend = riskLegendView(alerts);
  if (!priority) return null;

  return (
    <section className="early-warning" aria-labelledby={headingId}>
      <div className="early-warning__head">
        <h3 id={headingId} className="early-warning__title">
          Where to look first
        </h3>
        <span className="early-warning__meta">Data through {priority.dataThrough} (UTC)</span>
      </div>

      {priority.total === 0 ? (
        <p className="early-warning__empty">No cell to look at first in view.</p>
      ) : (
        <>
          <ol id={listId} className="early-warning__list" aria-labelledby={headingId}>
            {priority.items.map((item) => (
              <li key={item.h3}>
                <button type="button" className="early-warning__item" onClick={() => onFocusCell(item.latLng)}>
                  {item.risk && <span className="early-warning__risk">{item.risk} risk</span>}
                  {item.badge && <span className="map-badge">{item.badge}</span>}
                  <span className="early-warning__fire">{item.fireNow}</span>
                  <span className="visually-hidden">, show on map</span>
                </button>
              </li>
            ))}
          </ol>
          {priority.total > priority.items.length || showAll ? (
            <button
              type="button"
              className="map-btn early-warning__more"
              aria-expanded={showAll}
              aria-controls={listId}
              onClick={() => setShowAll((prev) => !prev)}
            >
              {showAll ? 'Show fewer' : `Show all ${priority.total}`}
            </button>
          ) : null}
        </>
      )}

      {legend && (
        <div className="early-warning__legend" role="group" aria-labelledby={legendId}>
          <p>
            <strong id={legendId}>{legend.title}</strong> <span className="early-warning__meta">{legend.scoredAt}</span>
          </p>
          <ul className="early-warning__tiers">
            {legend.tiers.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
          <p className="early-warning__caveat">{legend.caveat}</p>
          <p className="early-warning__limits">
            <span>Limits:</span> {legend.limits.join(' ')}
          </p>
        </div>
      )}
    </section>
  );
}
