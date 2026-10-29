import type { MetadataRoute } from 'next'

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '/template-react'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Gramkit (React)',
    short_name: 'Gramkit',
    description: 'Telegram Mini App + web starter on FastAPI and Next.js',
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
