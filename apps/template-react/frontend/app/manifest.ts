import type { MetadataRoute } from 'next'

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '/template-react'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'TMA Template React',
    short_name: 'TMA React',
    description: 'Production-ready template for Telegram Mini Apps with React, Next.js, and TypeScript',
    start_url: basePath || '/',
    display: 'standalone',
    background_color: '#09090b',
    theme_color: '#09090b',
    orientation: 'portrait',
    icons: [
      {
        src: `${basePath}/android-chrome-192x192.png`,
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: `${basePath}/android-chrome-512x512.png`,
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: `${basePath}/apple-touch-icon.png`,
        sizes: '180x180',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  }
}
