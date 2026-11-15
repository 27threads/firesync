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

  it('has the mount point for the interactive tool', () => {
    expect(doc.getElementById('tool-root')).not.toBeNull();
  });
});
