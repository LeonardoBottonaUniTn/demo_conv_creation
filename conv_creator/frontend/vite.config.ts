import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(async () => {
  const vueModule = await import('@vitejs/plugin-vue')
  const devtoolsModule = await import('vite-plugin-vue-devtools')

  // Guard against environments where the plugins are re-exported without a default
  const vue =
    (vueModule as any).default ??
    (vueModule as any).vuePlugin ??
    (() => {
      throw new Error('Failed to load @vitejs/plugin-vue')
    })
  const vueDevTools =
    (devtoolsModule as any).default ??
    (devtoolsModule as any).VitePluginVueDevTools ??
    (() => {
      throw new Error('Failed to load vite-plugin-vue-devtools')
    })

  return {
    plugins: [vue(), vueDevTools()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        // Allow importing static backend files from the sibling backend/ directory
        backend: fileURLToPath(new URL('../backend', import.meta.url)),
      },
    },
  }
})
