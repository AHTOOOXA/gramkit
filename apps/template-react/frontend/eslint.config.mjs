import { FlatCompat } from '@eslint/eslintrc';
import js from '@eslint/js';
import nextPlugin from '@next/eslint-plugin-next';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

const compat = new FlatCompat({
  baseDirectory: import.meta.dirname,
});

export default tseslint.config(
  // Base configs
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,

  // Framework configs
  {
    files: ['**/*.{js,mjs,cjs,ts,jsx,tsx}'],
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
      '@next/next': nextPlugin,
    },
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ['*.mjs', '*.js'],
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // React rules
      'react/react-in-jsx-scope': 'off', // Not needed in Next.js
      'react/prop-types': 'off', // Using TypeScript
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // Next.js rules
      '@next/next/no-html-link-for-pages': 'error',
      '@next/next/no-img-element': 'warn',

      // TypeScript rules
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/consistent-type-imports': [
        'error',
        {
          prefer: 'type-imports',
          fixStyle: 'inline-type-imports',
        },
      ],
      '@typescript-eslint/no-misused-promises': [
        'error',
        {
          checksVoidReturn: {
            attributes: false,
          },
        },
      ],
    },
  },

  // Middleware-specific rules: prevent basePath issues
  {
    files: ['middleware.ts', 'middleware.js'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: 'NewExpression[callee.name="URL"]',
          message:
            'Do not use `new URL()` in middleware - it ignores basePath. Use `createRedirect()` from lib/middleware-utils.ts instead.',
        },
      ],
    },
  },

  // Ignore patterns
  {
    ignores: [
      '**/node_modules/**',
      '**/.next/**',
      '**/out/**',
      '**/dist/**',
      '**/build/**',
      '**/.turbo/**',
      '**/types/api.d.ts', // Generated file
      'src/schema/**', // Generated schema files
      'src/gen/**', // Generated Kubb files
      'components/ui/**', // shadcn/ui components (generated)
      'hooks/use-mobile.ts', // shadcn/ui hook (generated)
      'kubb.config.ts', // Kubb config
      'eslint.config.mjs', // Config file
      'postcss.config.mjs', // Config file
    ],
  }
);
