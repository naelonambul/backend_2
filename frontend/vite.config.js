import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDirectory = dirname(fileURLToPath(import.meta.url))
const repositoryRoot = resolve(frontendDirectory, '..')

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, repositoryRoot, '')
  const frontendEnv = loadEnv(mode, frontendDirectory, '')
  const frontendOrigin = frontendEnv.FRONTEND_ORIGIN || rootEnv.FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
  const backendOrigin = frontendEnv.BACKEND_ORIGIN || rootEnv.BACKEND_ORIGIN || 'https://api.nenene.n-e.kr'
  const frontendUrl = new URL(frontendOrigin)

  return {
    envDir: frontendDirectory,
    plugins: [vue()],
    define: {
      __FRONTEND_ORIGIN__: JSON.stringify(frontendOrigin),
      __BACKEND_ORIGIN__: JSON.stringify(backendOrigin),
    },
    server: {
      host: frontendUrl.hostname,
      port: Number(frontendUrl.port || 5173),
      proxy: {
        '/user': backendOrigin,
        '/board/': backendOrigin,
      },
    },
  }
})
