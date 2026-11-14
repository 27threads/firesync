import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
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
