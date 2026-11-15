import { gsap } from 'gsap';
import { stripGeometry, type StripSpec } from '../calendar/calendarLayout';

// Abertura: os meses entram como uma faixa cronológica (MODIS à esquerda, VIIRS à direita)
// e se dobram em linhas por ano. A cor de cada mês é a do valor real do começo ao fim;
// só a posição muda. O React já desenha o estado final, então sem a animação nada se perde.

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : true;
}

export function playHeroIntro(svg: SVGSVGElement, overlay: SVGSVGElement, strip: StripSpec): () => void {
  const firstYear = Number(svg.dataset.firstYear);
  const boxes = Array.from(svg.querySelectorAll<SVGSVGElement>('svg.cal-cellbox'));
  const real = boxes.filter((b) => b.dataset.stripI !== undefined);
  const outside = boxes.filter((b) => b.dataset.stripI === undefined);
  const total = real.length;
  if (total === 0) return () => undefined;

  const rowOf = (el: Element) => Number((el.parentElement?.dataset.key ?? '0').slice(0, 4)) - firstYear;
  const stripBox = (el: Element) => stripGeometry(Number((el as SVGSVGElement).dataset.stripI), total, strip);
  const decor = svg.querySelectorAll('[data-decor="axis"], [data-decor="notes"]');
  const switchPath = svg.querySelector<SVGPathElement>('[data-decor="switch"]');
  const highlight = svg.querySelectorAll('.cal-highlight, .cal-selected');

  const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });

  // 1. A faixa se desenha da esquerda para a direita, em ordem cronológica.
  //    O from() já põe cada mês na faixa no instante 0 (immediateRender).
  tl.from(
    real,
    {
      attr: {
        x: (_i: number, el: Element) => stripBox(el).x,
        y: strip.top,
        width: strip.width / total,
        height: strip.height,
      },
      duration: 0.75,
      ease: 'power3.inOut',
      stagger: (_i: number, el: Element) => rowOf(el) * 0.032,
    },
    1.6,
  );
  tl.from(real, { opacity: 0, duration: 0.18, stagger: 0.0026 }, 0.1);
  tl.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.35 }, 0.25);

  // 2. Os rótulos dos sensores saem e cada ano vira uma linha (tween acima, a partir de 1.6 s).
  tl.to(overlay, { opacity: 0, duration: 0.3 }, 1.55);

  // 3. Eixos, notas e a linha da troca de sensor completam a leitura.
  if (outside.length) tl.from(outside, { opacity: 0, duration: 0.3 }, 2.55);
  tl.from(decor, { opacity: 0, duration: 0.4 }, 2.5);
  if (highlight.length) tl.from(highlight, { opacity: 0, duration: 0.3 }, 2.7);
  if (switchPath) {
    const length = switchPath.getTotalLength();
    tl.fromTo(
      switchPath,
      { strokeDasharray: length, strokeDashoffset: length },
      { strokeDashoffset: 0, duration: 0.6, ease: 'power1.inOut', clearProps: 'strokeDasharray,strokeDashoffset' },
      2.55,
    );
  }

  const finish = () => tl.progress(1);
  const host = svg.closest('.hero, .ws-history') ?? svg;
  host.addEventListener('pointerdown', finish, { once: true });
  host.addEventListener('keydown', finish, { once: true });

  return () => {
    host.removeEventListener('pointerdown', finish);
    host.removeEventListener('keydown', finish);
    tl.progress(1).kill();
  };
}
