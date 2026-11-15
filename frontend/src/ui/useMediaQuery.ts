import { useCallback, useSyncExternalStore } from 'react';

function mediaQuery(query: string): MediaQueryList | null {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(query) : null;
}

/** true enquanto a media query casa; acompanha a mudança (girar o celular, redimensionar a janela). */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = mediaQuery(query);
      list?.addEventListener('change', onChange);
      return () => list?.removeEventListener('change', onChange);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => mediaQuery(query)?.matches ?? false, () => false);
}

/** Celular: os gráficos usam uma geometria estreita para o texto não encolher junto com o SVG. */
export const NARROW_QUERY = '(max-width: 560px)';
