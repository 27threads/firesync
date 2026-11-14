import { render, screen } from '@testing-library/react';
import { App } from './App';

describe('App (interactive tool shell)', () => {
  it('shows the tool as a labelled region with its heading', () => {
    render(<App />);
    expect(screen.getByRole('region', { name: /explore an area/i })).toBeInTheDocument();
  });

  it('tells the user what to do first', () => {
    render(<App />);
    expect(screen.getByText(/choose an area/i)).toBeInTheDocument();
  });
});
