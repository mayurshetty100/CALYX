// ==============================================================================
// CALYX FRONTEND - VITE CONFIGURATION
// ==============================================================================
// Vite is a modern frontend build tool that provides lightning-fast Hot Module
// Replacement (HMR) during local development and optimized Rollup bundles for production.
// ==============================================================================

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API requests to the Calyx Unified API Gateway during development
    proxy: {
      '/api': {
        target: process.env.VITE_API_GATEWAY_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
