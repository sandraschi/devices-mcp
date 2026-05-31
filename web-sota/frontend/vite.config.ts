import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  server: {
    allowedHosts: ['goliath'],
    port: 10716,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:10717', changeOrigin: true },
    },
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
});
