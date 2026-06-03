import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/video': { target: 'http://localhost:3001' },
      '/api/pipeline': { target: 'http://localhost:3002' },
      '/api/cc': { target: 'http://localhost:8080' },
      '/ws/cc': { target: 'ws://localhost:8080', ws: true }
    }
  }
});
