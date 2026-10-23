import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api/catalog': {
        target: 'http://localhost:8001',
        rewrite: (path) => path.replace(/^\/api\/catalog/, ''),
      },
      '/api/waitlist': {
        target: 'http://localhost:8003',
        rewrite: (path) => path.replace(/^\/api\/waitlist/, ''),
      },
      '/api/booking': {
        target: 'http://localhost:8002',
        rewrite: (path) => path.replace(/^\/api\/booking/, ''),
      },
    },
  },
})
