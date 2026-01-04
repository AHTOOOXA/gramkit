import { defineConfig } from "@kubb/core";
import { pluginOas } from "@kubb/plugin-oas";
import { pluginTs } from "@kubb/plugin-ts";
import { pluginClient } from "@kubb/plugin-client";
import { pluginVueQuery } from "@kubb/plugin-vue-query";

export default defineConfig({
  // Root directory for config
  root: '.',

  // Input OpenAPI specification
  input: {
    // Use local API endpoint (backend must be running)
    // For schema generation via tunnel: https://local.gramkit.dev/api/template/openapi.json
    path: "http://localhost:8002/openapi.json",
  },

  // Output directory for generated files
  output: {
    path: "./src/gen",
    clean: true,  // Clean before regenerating
  },

  // Plugins (order matters!)
  plugins: [
    // 1. Parse OpenAPI specification
    pluginOas({
      output: false,  // Don't generate OAS files
    }),

    // 2. Generate TypeScript types
    pluginTs({
      output: {
        path: 'models',
        banner: '// @ts-nocheck\n',
      },
      // Group types by tags (optional)
      group: {
        type: 'tag',
        output: './models/{{tag}}',
      },
    }),

    // 3. Generate API client
    pluginClient({
      output: {
        path: 'client',
        banner: '// @ts-nocheck\n',
      },
    }),

    // 4. Generate Vue Query hooks
    pluginVueQuery({
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
