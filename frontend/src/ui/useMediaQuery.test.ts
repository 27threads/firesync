import { act, renderHook } from '@testing-library/react';
import { useMediaQuery } from './useMediaQuery';

function mockMatchMedia(initial: boolean) {
  const listeners = new Set<() => void>();
  const query = { matches: initial, addEventListener: (_: string, l: () => void) => listeners.add(l), removeEventListener: (_: string, l: () => void) => listeners.delete(l) };
  window.matchMedia = vi.fn(() => query as unknown as MediaQueryList);
  return (next: boolean) => {
    query.matches = next;
    listeners.forEach((l) => l());
  };
}

describe('useMediaQuery', () => {
  afterEach(() => {
    // jsdom não tem matchMedia: volta ao estado original.
    delete (window as { matchMedia?: unknown }).matchMedia;
  });

  it('follows the media query and updates when it changes', () => {
    const change = mockMatchMedia(true);
    const { result } = renderHook(() => useMediaQuery('(max-width: 560px)'));
    expect(result.current).toBe(true);
    act(() => change(false));
    expect(result.current).toBe(false);
  });

  it('is false where the browser has no matchMedia', () => {
    const { result } = renderHook(() => useMediaQuery('(max-width: 560px)'));
    expect(result.current).toBe(false);
  });
});
