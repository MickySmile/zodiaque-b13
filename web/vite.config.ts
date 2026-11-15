import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// L'API locale (uvicorn) : l'interface l'appelle par des adresses relatives, relayées ici.
// Aucun autre hôte n'est contacté.
const API = process.env.B13_API ?? 'http://127.0.0.1:8000'
const relais = { '/api': { target: API, changeOrigin: false } }

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: relais,
    // Les tests lisent les frontières produites par le moteur, hors du dossier web/.
    fs: { allow: ['.', '../generes'] },
  },
  preview: { proxy: relais },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
})
