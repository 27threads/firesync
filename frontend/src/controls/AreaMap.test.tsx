import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AreaMap } from './AreaMap';

describe('AreaMap', () => {
  it('opens on the NASA GIBS base map, with the CARTO map as the alternative', () => {
    render(<AreaMap focusBbox={null} focusPoint={null} onSelectPolygon={vi.fn()} />);

    expect(screen.getByRole('button', { name: /NASA GIBS/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /CARTO/ })).toHaveAttribute('aria-pressed', 'false');
  });
});
