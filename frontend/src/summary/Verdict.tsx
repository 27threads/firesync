import type { RecentWindow } from '../api/types';
import type { TypicalStatus } from './summaryModel';
import { buildVerdict } from './verdictModel';

// A forma do ícone muda junto com a cor, para não depender só da cor (RD04).
const ICONS: Record<TypicalStatus, string> = { above: '▲', within: '●', below: '▼' };

interface VerdictProps {
  window: RecentWindow;
  areaLabel: string;
}

export function Verdict({ window, areaLabel }: VerdictProps) {
  const verdict = buildVerdict(window);
  return (
    <section className={`verdict verdict--${verdict.status}`} aria-label="Fire right now">
      <span className="verdict__icon" aria-hidden="true">
        {ICONS[verdict.status]}
      </span>
      <div className="verdict__body">
        <p className="verdict__area">{areaLabel}</p>
        <h3 className="verdict__headline">{verdict.headline}</h3>
        <p className="verdict__sentence">{verdict.sentence}</p>
        <a className="verdict__why" href="#summary-question">
          Why? See the numbers
        </a>
      </div>
    </section>
  );
}
