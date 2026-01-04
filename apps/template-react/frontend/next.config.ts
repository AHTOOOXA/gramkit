import type { NextConfig } from 'next';
import path from 'path';

const nextConfig: NextConfig = {
  // Enable Turbopack filesystem cache for fast local development
  // Cache persists between dev server restarts for ~10x faster warm starts
  experimental: {
    turbopackFileSystemCacheForDev: true,
  },

  // Monorepo: trace dependencies from workspace root (for standalone output)
  outputFileTracingRoot: path.join(__dirname, '../../..'),

  // Base path for serving under nginx
  // Local dev: /template-react (default)
  // Production: set NEXT_PUBLIC_BASE_PATH= (empty) for root path
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? '/template-react',

  // No trailing slashes - nginx handles normalization
  // trailingSlash: false is the default

  // Standalone output for Docker
  output: 'standalone',

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 't.me',
      },
      {
        protocol: 'https',
        hostname: 'api.telegram.org',
      },
      {
        protocol: 'https',
        hostname: 'picsum.photos',
      },
      {
        protocol: 'https',
        hostname: 'fastly.picsum.photos',
      },
      {
        protocol: 'https',
        hostname: 'api.dicebear.com',
      },
    ],
  },

  // Disable x-powered-by header
  poweredByHeader: false,

  // React strict mode
  reactStrictMode: true,

  // Allow cross-origin requests from nginx proxy
  allowedDevOrigins: ['local.gramkit.dev'],

  // i18n configuration (handled manually by next-intl without plugin)
  // Plugin doesn't work in Docker/monorepo setup with Turbopack
  // No Next.js i18n routing needed

  // Turbopack configuration (Next.js 16 default)
  // Manually set up next-intl alias since plugin doesn't work in Docker/monorepo
  turbopack: {
    resolveAlias: {
      'next-intl/config': './i18n/request.ts',
    },
  },

  // Webpack configuration (fallback when not using Turbopack)
  webpack: (config: { resolve?: { alias?: Record<string, string> } }) => {
    // Manually set up next-intl alias for Webpack
    config.resolve = config.resolve ?? {};
    config.resolve.alias = config.resolve.alias ?? {};
    config.resolve.alias['next-intl/config'] = './i18n/request.ts';
    return config;
  },

  // Environment variables available to browser
  // API URL is resolved at runtime in kubb-config.ts:
  // - Production: set NEXT_PUBLIC_API_URL=https://api.my-domain.com
  // - Local dev: auto-detected (localhost→8003, domain→/api/template-react)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? '/',
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME ?? 'Template React',
    APP_NAME: process.env.APP_NAME ?? 'template-react',
  },
};

export default nextConfig;
