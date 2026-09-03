import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev server on 5178, proxying /api to the real FastAPI backend on 8005 --
// same ports as the reference app, so `npm run dev` + the backend's
// `uvicorn main:app --port 8005` just works together with no extra config.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5178,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8005',
        changeOrigin: true,
      },
    },
  },
});
