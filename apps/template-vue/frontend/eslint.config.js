import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import eslintConfigPrettier from 'eslint-config-prettier'
import pluginUnusedImports from 'eslint-plugin-unused-imports'

export default [
  // Vue recommended rules
  ...pluginVue.configs['flat/recommended'],

  // TypeScript rules
  ...vueTsEslintConfig(),

  // Prettier compatibility (disables conflicting rules)
  eslintConfigPrettier,

  // Custom rules
  {
    plugins: {
      'unused-imports': pluginUnusedImports,
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-empty-interface': 'off',

      // Auto-remove unused imports
      '@typescript-eslint/no-unused-vars': 'off', // Disable base rule
      'unused-imports/no-unused-imports': 'error',
      'unused-imports/no-unused-vars': ['warn', {
        vars: 'all',
        varsIgnorePattern: '^_',
        args: 'after-used',
        argsIgnorePattern: '^_',
      }],

      // Enforce core/app/schema aliases instead of deprecated @/ alias
      // Exception: @/components/ui/* and @/lib/* are allowed (shadcn-vue library)
      // AND enforce core public API usage (no deep imports into core internals)
      'no-restricted-imports': ['error', {
        patterns: [
          {
            group: ['@/app/*', '@/core/*', '@/schema/*', '@/composables/*', '@/store/*', '@/assets/*', '@/utils/*'],
            message: 'Use @core, @app, or @schema aliases instead of deprecated @/ alias.\nException: @/components/ui/* and @/lib/* are allowed for shadcn-vue library.',
          },
          {
            group: ['@core/*/*', '@core/*/*/*'],
            message: 'Import from @core or @core/* public APIs (max one level deep).\n\nExamples:\n  ✅ import { usePlatform } from \'@core\'\n  ✅ import { usePlatform } from \'@core/platform\'\n  ❌ import { usePlatform } from \'@core/platform/usePlatform\'\n\nNote: Type-only imports (import type) from deep paths are allowed for flexibility.\n\nThis ensures core can be refactored without breaking dependent projects.',
          },
        ],
      }],
    },
  },

  // Allow require() in config files
  {
    files: ['*.config.js', '*.config.cjs'],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },

  // Allow @/ alias in shadcn-vue components (third-party library code)
  {
    files: ['src/components/ui/**/*', 'src/lib/utils.ts'],
    rules: {
      'no-restricted-imports': 'off',
      'vue/require-default-prop': 'off', // shadcn components don't always have defaults
    },
  },

  // Ignores
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '.vite/**', // Vite dev server cache
      '*.log',
      'src/schema/api.d.ts', // Generated OpenAPI types
      'src/gen/**', // Generated Kubb client code
      'src/components/ui/**', // shadcn-vue components (generated)
      'src/lib/utils.ts', // shadcn-vue utils (generated)
    ],
  },
]
