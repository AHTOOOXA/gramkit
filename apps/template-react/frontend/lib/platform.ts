import { cookies } from 'next/headers';

/**
 * Get platform from app-namespaced cookie (Server Component)
 * @returns 'telegram' | 'web'
 */
export async function getPlatform(): Promise<'telegram' | 'web'> {
  const cookieStore = await cookies();
  const cookieName = `${process.env.APP_NAME ?? 'app'}-platform`;
  const platform = cookieStore.get(cookieName)?.value;

  // Default to 'web' if cookie not set yet (first load)
  return platform === 'telegram' ? 'telegram' : 'web';
}

/**
 * Check if platform is Telegram (Server Component)
 */
export async function isTelegram(): Promise<boolean> {
  const platform = await getPlatform();
  return platform === 'telegram';
}

/**
 * Check if platform is Web (Server Component)
 */
export async function isWeb(): Promise<boolean> {
  const platform = await getPlatform();
  return platform === 'web';
}
