import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // jsdom simula el navegador para probar componentes sin abrir uno de verdad
    environment: 'jsdom',
    setupFiles: ['./src/pruebas/preparar.ts'],
    css: false,
  },
})
