import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/wealth-manager/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1/wealth-manager': 'http://127.0.0.1:5000',
      '/wealth-api': 'http://127.0.0.1:5000',
    },
  },
});

