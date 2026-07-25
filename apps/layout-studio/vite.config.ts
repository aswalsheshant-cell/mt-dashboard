import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
    // Allow Vite to resolve TypeScript source packages in the monorepo
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
  },
  optimizeDeps: {
    // Pre-bundle workspace packages from their TypeScript source
    include: [
      '@mt-dashboard/layout-schema > zod',
    ],
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          dndkit: ['@dnd-kit/core', '@dnd-kit/modifiers', '@dnd-kit/utilities'],
          charts: ['recharts'],
          state: ['zustand'],
          schema: ['zod'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/unit/setup.ts'],
    // Exclude Playwright e2e tests — they are run separately via `playwright test`
    exclude: ['tests/e2e/**', 'node_modules/**'],
  },
});
