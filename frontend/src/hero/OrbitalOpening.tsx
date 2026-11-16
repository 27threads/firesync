import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { useMediaQuery } from '../ui/useMediaQuery';
import { chapterAt, journeyProgress, MAP_ARRIVAL_HOLD, smoothPhase, STACKED_OPENING_MAX_WIDTH } from './globeTransition';
import { prefersReducedMotion } from './heroIntro';
import { OPENING_AUDIENCE, OPENING_CHAPTERS, OPENING_DATA_CREDIT } from './openingCopy';

const OrbitalScene = lazy(() => import('./OrbitalScene'));
const HeroMap = lazy(() => import('./HeroMap'));

// Ponto do scroll em que cada capítulo do texto aparece (o mesmo corte de chapterAt).
const CHAPTER_STOPS = [0, 0.3, 0.7];

function goToExplorer() {
  document.getElementById('explore')?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
}

// Abertura: o globo com o Aqua (MODIS) e o Suomi NPP (VIIRS) em órbita desce até o Brasil conforme o scroll.
export function OrbitalOpening() {
  const section = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const [chapter, setChapter] = useState(0);
  const [mapActive, setMapActive] = useState(false);
  const [mountMap, setMountMap] = useState(false);
  // Sem botão de pausa (pedido do Eduardo): o globo para sozinho só com movimento reduzido.
  const [playing] = useState(() => !prefersReducedMotion());
  // A mesma regra de openingLayout, que a cena usa para enquadrar o globo.
  const stacked = useMediaQuery(`(max-width: ${STACKED_OPENING_MAX_WIDTH}px)`);

  useEffect(() => {
    const element = section.current;
    if (!element) return;
    let frame = 0;
    let previous = performance.now();
    const update = () => {
      // A descida usa a altura da seção sem a parada final, em que o mapa em tela cheia fica à mostra.
      const target = journeyProgress(element.getBoundingClientRect().top, element.offsetHeight - window.innerHeight * MAP_ARRIVAL_HOLD, window.innerHeight);
      const now = performance.now();
      const delta = Math.min((now - previous) / 1000, 0.05);
      previous = now;
      const value = prefersReducedMotion() ? target : progress.current + (target - progress.current) * (1 - Math.exp(-delta * 9));
      progress.current = Math.abs(target - value) < 0.001 ? target : value;
      element.style.setProperty('--journey-progress', progress.current.toFixed(3));
      element.style.setProperty('--map-blend', smoothPhase(progress.current, 0.9, 0.98).toFixed(3));
      if (progress.current > 0.4) setMountMap(true);
      setMapActive(progress.current >= 0.98 && target >= 0.98);
      // Com movimento reduzido a seção não rola: o capítulo muda só pelos botões.
      if (!prefersReducedMotion()) setChapter(chapterAt(progress.current));
      frame = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(frame);
  }, []);

  const showChapter = (index: number) => {
    const element = section.current;
    if (!element) return;
    if (prefersReducedMotion()) {
      setChapter(index);
      return;
    }
    const distance = Math.max(1, element.offsetHeight - window.innerHeight * (1 + MAP_ARRIVAL_HOLD));
    const top = window.scrollY + element.getBoundingClientRect().top + distance * (CHAPTER_STOPS[index] ?? 0);
    window.scrollTo({ top, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
  };

  const content = OPENING_CHAPTERS[chapter] ?? OPENING_CHAPTERS[0];

  return (
    <section ref={section} className="opening" data-layout={stacked ? 'stacked' : 'side'} aria-labelledby="opening-title">
      <div className="opening__sticky">
        <Suspense fallback={<div className="orbital-canvas" />}>
          <OrbitalScene playing={playing} progress={progress} />
        </Suspense>
        {mountMap && !prefersReducedMotion() && (
          <Suspense fallback={null}>
            <HeroMap active={mapActive} onReturn={() => showChapter(0)} onNext={goToExplorer} />
          </Suspense>
        )}
        <div className="opening__copy">
          <p className="opening__kicker">{OPENING_AUDIENCE}</p>
          <h1 id="opening-title" className="opening__brand">
            firesync<span>.</span>
          </h1>
          <div className="opening__chapter" key={chapter} aria-live="polite">
            <p className="opening__label">{content.label}</p>
            <h2>
              {content.title[0]}
              <br />
              {content.title[1]}
            </h2>
            <p>{content.copy}</p>
          </div>
          <button type="button" className="btn btn--primary" onClick={goToExplorer}>
            Explore an area
          </button>
          <p className="opening__credit">{OPENING_DATA_CREDIT}</p>
        </div>
        <p className="opening__foot">Earth and spacecraft: NASA · Illustrative scale and orbits</p>
      </div>
    </section>
  );
}
