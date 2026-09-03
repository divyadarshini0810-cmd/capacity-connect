import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const localApiProxy = {
  '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true },
}

export default defineConfig({
  plugins: [react(), VitePWA({ registerType: 'autoUpdate', manifest: { name: 'Capacity Connect', short_name: 'Capacity Connect', theme_color: '#06111f', background_color: '#06111f', display: 'standalone', icons: [] }, workbox: { globPatterns: ['**/*.{js,css,html,svg,png}'] } })],
  // Matches an explicitly allowed local API origin for zero-setup development.
  server: { port: 4173, strictPort: true, proxy: localApiProxy },
})
