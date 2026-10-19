import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/user': 'http://localhost:8000',
      '/board': 'http://localhost:8000',
    },
  },
})
