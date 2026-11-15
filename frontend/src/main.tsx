import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/archivo/wdth.css';
import { App } from './App';
import { OrbitalOpening } from './hero/OrbitalOpening';
import './styles.css';

const toolRoot = document.getElementById('tool-root');
if (!toolRoot) {
  throw new Error('index.html is missing the #tool-root element');
}

createRoot(toolRoot).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// A abertura com o globo substitui o texto fixo do #opening-root, que fica para quem abre sem JS.
const openingRoot = document.getElementById('opening-root');
if (openingRoot) {
  createRoot(openingRoot).render(
    <StrictMode>
      <OrbitalOpening />
    </StrictMode>,
  );
}
