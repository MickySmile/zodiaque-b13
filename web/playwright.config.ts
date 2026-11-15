import { defineConfig, devices } from '@playwright/test'

const PORT = 4173
const PORT_API = 8013

// Tests de bout en bout et d'accessibilité : Chromium seul, sur la version construite de
// l'interface, branchée sur l'API locale réelle (moteur, DE440s, GeoNames). Rien n'est simulé.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `uv run uvicorn api.main:app --port ${PORT_API} --log-level warning`,
      cwd: '..',
      url: `http://127.0.0.1:${PORT_API}/health`,
      // Jamais de serveur déjà lancé : on ne teste pas une version périmée.
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npm run build && npm run preview -- --port ${PORT} --strictPort`,
      env: { B13_API: `http://127.0.0.1:${PORT_API}` },
      url: `http://localhost:${PORT}`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
