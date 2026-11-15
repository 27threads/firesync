import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// O index.html carrega o texto fixo (intro, Method, Data & credits) para a página ficar completa sem JS.
function loadIndexHtml(): Document {
  const html = readFileSync(join(__dirname, '..', 'index.html'), 'utf-8');
  return new DOMParser().parseFromString(html, 'text/html');
}

describe('index.html (static page shell)', () => {
  const doc = loadIndexHtml();

  it('is in English, with a title and a meta description', () => {
    expect(doc.documentElement.lang).toBe('en');
    expect(doc.title).toMatch(/firesync/i);
    const description = doc.querySelector('meta[name="description"]')?.getAttribute('content') ?? '';
    expect(description).toMatch(/MODIS/);
    expect(description).toMatch(/VIIRS/);
  });

  it('credits NASA FIRMS in the header, linked to the FIRMS site', () => {
    const credit = doc.querySelector('header a[href^="https://firms.modaps.eosdis.nasa.gov"]');
    expect(credit?.textContent).toMatch(/NASA FIRMS/);
  });

  it('has a Method section and a Data & credits section', () => {
    const headings = Array.from(doc.querySelectorAll('h2')).map((h) => h.textContent);
    expect(headings).toContain('Method');
    expect(headings).toContain('Data & credits');
  });

  it('lists every data source and mapping library in Data & credits', () => {
    const credits = doc.getElementById('credits')?.textContent ?? '';
    for (const source of [
      'NASA FIRMS',
      'MODIS C6.1',
      'VIIRS C2',
      'IBGE',
      'INPE',
      'Decree 080/2020',
      'NASA EOSDIS GIBS',
      'OpenStreetMap',
      'Leaflet',
      'Leaflet-Geoman',
    ]) {
      expect(credits).toContain(source);
    }
  });

  it('counts detections, never fires', () => {
    const text = doc.body.textContent ?? '';
    expect(text).not.toMatch(/\bnumber of fires\b/i);
    expect(text).toMatch(/detections/i);
  });

  // Resultados da frente B (docs/decisoes-harmonizacao.md, seções 4 e 5, e docs/rfcs/0003-modelo-risco.md).
  it('reports the comparison with INPE, including the biomes that do not fit', () => {
    const method = doc.getElementById('method')?.textContent ?? '';
    expect(method).toMatch(/INPE/);
    expect(method).toContain('−0.6%');
    expect(method).toMatch(/Atlantic Forest/);
    expect(method).toMatch(/Pampa/);
  });

  it('shows the detection curve with alt text and its limits', () => {
    const img = doc.querySelector('#method img[src$="curva_deteccao_2024.png"]');
    expect(img?.getAttribute('alt') ?? '').toMatch(/MODIS/);
    const caption = img?.closest('figure')?.querySelector('figcaption')?.textContent ?? '';
    expect(caption).toMatch(/not used to compute the calendar/);
    expect(caption).toMatch(/2024/);
  });

  it('explains why a trained model was not adopted for the alert', () => {
    const method = doc.getElementById('method')?.textContent ?? '';
    expect(method).toMatch(/machine-learning model/);
    expect(method).toMatch(/0\.9 percentage points/);
    expect(method).toMatch(/rule v1/);
  });

  it('has the mount point for the interactive tool', () => {
    expect(doc.getElementById('tool-root')).not.toBeNull();
  });
});
