import { useEffect, useState } from 'react';

/**
 * `true` quando a abertura (o globo e a descida até o mapa) já saiu da tela.
 * Serve para o que não deve disputar espaço com o hero, como o botão do assistente.
 * Sem abertura na página (testes, JS desligado) ou sem IntersectionObserver, devolve `true`: nada some sem motivo.
 */
export function useLeftHero(rootId = 'opening-root'): boolean {
  const [left, setLeft] = useState(() => typeof document === 'undefined' || !document.getElementById(rootId));

  useEffect(() => {
    const hero = document.getElementById(rootId);
    if (!hero || typeof IntersectionObserver === 'undefined') {
      setLeft(true);
      return;
    }
    const observer = new IntersectionObserver(([entry]) => setLeft(!entry?.isIntersecting), { threshold: 0 });
    observer.observe(hero);
    return () => observer.disconnect();
  }, [rootId]);

  return left;
}
