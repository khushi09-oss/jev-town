import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  build: { assetsInlineLimit: 10000000, cssCodeSplit: false,
    rolldownOptions: { output: { codeSplitting: false } } },
  server: { fs: { deny: ['**/.env', '**/.env.*', '**/*.pem', '**/*.key'] } }
});
