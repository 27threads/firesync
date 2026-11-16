import { fireEvent, render, screen } from '@testing-library/react';
import { OrbitalOpening } from './OrbitalOpening';

// O WebGL não existe no jsdom; a cena 3D tem a própria checagem no navegador.
vi.mock('./OrbitalScene', () => ({ default: () => <div data-testid="scene" /> }));

describe('OrbitalOpening', () => {
  it('opens with the question the tool answers, the NASA data credit and a way into the explorer', () => {
    render(<OrbitalOpening />);
    expect(screen.getByRole('heading', { level: 1, name: /firesync/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /is this fire normal/i })).toBeInTheDocument();
    expect(screen.getByText(/NASA FIRMS · MODIS C6\.1 \(Aqua\) · VIIRS C2/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Explore an area' })).toBeInTheDocument();
  });

  it('scrolls to the explorer from the main button', () => {
    document.body.innerHTML = '<section id="explore"></section>';
    const explore = document.getElementById('explore')!;
    explore.scrollIntoView = vi.fn();
    render(<OrbitalOpening />);
    fireEvent.click(screen.getByRole('button', { name: 'Explore an area' }));
    expect(explore.scrollIntoView).toHaveBeenCalled();
  });

  it('has no pause button or chapter dots: the globe tells its story by scrolling', () => {
    render(<OrbitalOpening />);
    expect(screen.queryByRole('button', { name: /pause the globe|play the globe|chapter/i })).toBeNull();
  });
});
