import type { Indicators } from '../api/types';
import { buildIndicators } from './indicatorsModel';

interface IndicatorRowProps {
  indicators: Indicators;
  isDemo: boolean;
}

export function IndicatorRow({ indicators, isDemo }: IndicatorRowProps) {
  return (
    <section className="indicators" aria-label={isDemo ? 'Key indicators (demo data)' : 'Key indicators'}>
      <dl className="indicators__list">
        {buildIndicators(indicators).map((tile) => (
          <div key={tile.id} className="indicators__tile">
            <dt>{tile.label}</dt>
            <dd className="indicators__value">{tile.value}</dd>
            <dd className="indicators__detail">{tile.detail}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
