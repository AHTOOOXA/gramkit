import { defineConfig } from '@kubb/core';
import { pluginClient } from '@kubb/plugin-client';
import { pluginOas } from '@kubb/plugin-oas';
import { pluginReactQuery } from '@kubb/plugin-react-query';
import { pluginTs } from '@kubb/plugin-ts';

export default defineConfig({
  // Root directory for config
  root: '.',

  // Input OpenAPI specification
  input: {
    // Local backend (make up APP=template-react → :8003). Without a stack, dump app.openapi()
    // to a file and run `OPENAPI_PATH=<file> pnpm generate`.
    path: process.env.OPENAPI_PATH ?? 'http://localhost:8003/openapi.json',
  },

  // Output directory for generated files
  output: {
    path: './src/gen',
    clean: true, // Clean before regenerating
  },

  // Plugins (order matters!)
  plugins: [
    // 1. Parse OpenAPI specification
    pluginOas(),

    // 2. Generate TypeScript types
    pluginTs({
      output: {
        path: 'models',
        banner: '// @ts-nocheck\n',
      },
    }),

    // 3. Generate API client
    pluginClient({
      output: {
        path: 'client',
        banner: '// @ts-nocheck\n',
      },
    }),

    // 4. Generate React Query hooks
    pluginReactQuery({
      output: {
        path: 'hooks',
        banner: '// @ts-nocheck\n',
      },
      // Configure mutations
      mutation: {
        methods: ['post', 'put', 'patch', 'delete'],
      },
    }),
  ],
});
