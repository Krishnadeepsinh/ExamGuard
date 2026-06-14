import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 450,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) return 'react'
          if (id.includes('node_modules/lucide-react')) return 'icons'
          if (id.includes('node_modules/motion')) return 'motion'
          if (id.includes('node_modules/@mediapipe/tasks-vision')) return 'vision'
        },
      },
    },
  },
})
