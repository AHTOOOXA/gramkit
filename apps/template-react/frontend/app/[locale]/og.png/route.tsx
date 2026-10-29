import { ImageResponse } from 'next/og';

// Link preview card (Telegram, X, Slack, GitHub) at /<locale>/og.png, wired up in
// the marketing layout's metadata. A route handler rather than the
// opengraph-image file convention: that one drops the basePath from the URL it
// puts in og:image. The text stays English in both locales: the bundled OG font
// has no Cyrillic glyphs.
const OG_SIZE = { width: 1200, height: 630 };

const PRIMARY = '#0b9be0';
const PILLS = [
  'Telegram Stars + YooKassa',
  'Admin panel',
  'Bot & broadcasts',
  'Type-safe API',
];

export function GET() {
  return new ImageResponse(
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '72px 80px',
        background:
          'linear-gradient(135deg, #0d1424 0%, #111d33 60%, #0c2a40 100%)',
        color: '#f1f5f9',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
        {/* lucide FlaskConical, the site logo */}
        <svg
          width="56"
          height="56"
          viewBox="0 0 24 24"
          fill="none"
          stroke={PRIMARY}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2" />
          <path d="M6.453 15h11.094" />
          <path d="M8.5 2h7" />
        </svg>
        <span style={{ fontSize: 48, fontWeight: 700, letterSpacing: -1 }}>
          Gramkit
        </span>
        <span
          style={{
            marginLeft: 12,
            fontSize: 22,
            color: PRIMARY,
            border: `2px solid ${PRIMARY}`,
            borderRadius: 999,
            padding: '4px 16px',
          }}
        >
          Open source · MIT
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div
          style={{
            fontSize: 68,
            fontWeight: 700,
            lineHeight: 1.08,
            letterSpacing: -2,
            maxWidth: 980,
          }}
        >
          Telegram Mini App + web starter
        </div>
        <div style={{ fontSize: 28, color: '#94a3b8' }}>
          FastAPI + Next.js or Vue · Postgres · Redis · aiogram
        </div>
      </div>

      <div style={{ display: 'flex', gap: 14 }}>
        {PILLS.map((pill) => (
          <span
            key={pill}
            style={{
              fontSize: 24,
              padding: '10px 20px',
              borderRadius: 14,
              background: 'rgba(11, 155, 224, 0.14)',
              color: '#bae6fd',
            }}
          >
            {pill}
          </span>
        ))}
      </div>
    </div>,
    OG_SIZE
  );
}
