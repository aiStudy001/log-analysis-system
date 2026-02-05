import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/tests/setup.ts'],
    include: ['src/tests/**/*.test.ts'],
  },
  resolve: {
    alias: {
      '$lib': path.resolve(__dirname, './src/lib')
    }
  }
})
