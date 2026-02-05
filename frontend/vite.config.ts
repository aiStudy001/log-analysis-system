import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte()
  ],
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib')
    }
  },
  optimizeDeps: {
    include: ['marked']  // Ensure marked is bundled
  },
  build: {
    commonjsOptions: {
      include: [/marked/, /node_modules/]  // Include marked in CommonJS handling
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
