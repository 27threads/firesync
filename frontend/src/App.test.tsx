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

  it('puts now before history: indicators and the last 7 days come before the calendar', () => {
    render(<App />);
    const order = [
      screen.getByRole('region', { name: /key indicators/i }),
      screen.getByRole('region', { name: /last 7 days/i }),
      screen.getByRole('grid', { name: /fire calendar/i }),
      screen.getByRole('region', { name: /seasonal pattern/i }),
      screen.getByRole('region', { name: /years ranked/i }),
    ];
    for (let i = 1; i < order.length; i++) {
      expect(order[i - 1].compareDocumentPosition(order[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
});
