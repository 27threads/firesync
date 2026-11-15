import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// Os headers do Cloudflare (public/_headers) só valem no site no ar: o npm run dev não os aplica.
function cspDirective(name: string): string[] {
  const headers = readFileSync(join(__dirname, '..', 'public', '_headers'), 'utf-8');
  const csp = headers.match(/Content-Security-Policy:\s*(.+)/)?.[1] ?? '';
  const directive = csp.split(';').map((part) => part.trim().split(/\s+/)).find(([key]) => key === name);
  return directive?.slice(1) ?? [];
}

describe('Content-Security-Policy (public/_headers)', () => {
  it('lets GLTFLoader fetch the blob: textures of the NASA spacecraft models', () => {
    // Sem blob: no connect-src as texturas falham e os satélites saem brancos.
    expect(cspDirective('connect-src')).toContain('blob:');
  });

  it('lets the textures decoded from blob: be drawn', () => {
    expect(cspDirective('img-src')).toContain('blob:');
  });
});
