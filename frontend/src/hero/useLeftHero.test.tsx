import { act, render, screen } from '@testing-library/react';
import { useLeftHero } from './useLeftHero';

function Probe() {
  return <p data-testid="state">{useLeftHero() ? 'left' : 'in-hero'}</p>;
}

type Callback = (entries: Array<Pick<IntersectionObserverEntry, 'isIntersecting'>>) => void;
let callback: Callback | null = null;

beforeEach(() => {
  callback = null;
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(cb: Callback) {
        callback = cb;
      }
      observe() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.getElementById('opening-root')?.remove();
});

function addHero() {
  const hero = document.createElement('div');
  hero.id = 'opening-root';
  document.body.appendChild(hero);
}

test('sem abertura na página, o conteúdo fica visível', () => {
  render(<Probe />);
  expect(screen.getByTestId('state')).toHaveTextContent('left');
});

test('enquanto a abertura está na tela, o hero conta como ocupado', () => {
  addHero();
  render(<Probe />);
  act(() => callback?.([{ isIntersecting: true }]));
  expect(screen.getByTestId('state')).toHaveTextContent('in-hero');
});

test('quando a abertura sai da tela, libera o conteúdo', () => {
  addHero();
  render(<Probe />);
  act(() => callback?.([{ isIntersecting: true }]));
  act(() => callback?.([{ isIntersecting: false }]));
  expect(screen.getByTestId('state')).toHaveTextContent('left');
});

test('sem IntersectionObserver, nada some', () => {
  vi.stubGlobal('IntersectionObserver', undefined);
  addHero();
  render(<Probe />);
  expect(screen.getByTestId('state')).toHaveTextContent('left');
});
