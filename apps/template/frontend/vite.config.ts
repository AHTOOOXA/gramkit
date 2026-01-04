import { sentryVitePlugin } from "@sentry/vite-plugin";
import { version } from "./package.json";
import { defineConfig, loadEnv } from 'vite'
import path from 'node:path'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [
      vue(),
      tailwindcss(),
      sentryVitePlugin({
        org: env.VITE_SENTRY_ORG,
        project: env.VITE_SENTRY_PROJECT,
        authToken: env.VITE_SENTRY_AUTH_TOKEN,
        release: {
          name: version,
        }
      })
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@schema': path.resolve(__dirname, './src/schema'),
        '@core': path.resolve(__dirname, '../../../core/frontend/src'),
        '@app': path.resolve(__dirname, './src/app'),
        '@gen': path.resolve(__dirname, './src/gen'),
      },
    },
    server: {
      host: true,
      allowedHosts: [
        'localhost',
        'nginx',  // Docker internal network
        ...(env.VITE_WEB_HOST ? [new URL(env.VITE_WEB_HOST).hostname] : []),
      ],
      // HMR config only applied when accessing via tunnel (not localhost)
      // When on localhost, Vite's default HMR works fine
    },
    build: {
      target: ['es2015', 'chrome87', 'safari13', 'firefox78', 'edge88'],
      sourcemap: process.env.NODE_ENV === 'production'
    },
  };
});
