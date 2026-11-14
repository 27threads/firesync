/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // O JSON de exemplo fica em docs/ (fonte de verdade do contrato), fora da pasta do front.
  server: { port: 5173, fs: { allow: ['..'] } },
  preview: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/test-setup.ts'],
  },
});
