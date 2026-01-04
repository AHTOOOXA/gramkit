'use client';

import { useCallback, useEffect } from 'react';
import { useLocale } from 'next-intl';

import { useUpdateUser } from '@/hooks';
import { usePathname, useRouter } from '@/i18n/navigation';
import { useGetCurrentUserUsersMeGet } from '@/src/gen/hooks';

const SUPPORTED_LOCALES = ['en', 'ru'] as const;

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export function useLanguageService() {
  const currentLocale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const { data: user } = useGetCurrentUserUsersMeGet({
    query: { staleTime: 5 * 60 * 1000 },
  });
  const { mutateAsync: updateUser } = useUpdateUser();

  const switchLocale = useCallback(
    (locale: SupportedLocale) => {
      // next-intl's router.replace handles locale switching automatically
      // pathname from next-intl is already without locale prefix
      router.replace(pathname, { locale });
    },
    [pathname, router]
  );

  // Sync user language to i18n locale (only for authenticated users)
  useEffect(() => {
    // Skip sync for guest users - they can't persist language preference
    // Guest users should use URL-based locale (controlled by NEXT_LOCALE cookie)
    if (!user || user.user_type === 'GUEST') {
      return;
    }

    if (!user.language_code) {
      return;
    }

    const userLang = user.language_code as SupportedLocale;

    // Check if language is supported
    if (!SUPPORTED_LOCALES.includes(userLang)) {
      console.warn(
        `[useLanguageService] Unsupported language: ${userLang}, defaulting to en`
      );
      return;
    }

    // If user's language differs from current locale, switch
    if (userLang !== currentLocale) {
      switchLocale(userLang);
    }
  }, [user?.language_code, currentLocale, switchLocale, user]);

  const changeLanguage = useCallback(
    async (locale: SupportedLocale) => {
      if (!SUPPORTED_LOCALES.includes(locale)) {
        console.error(`Unsupported locale: ${locale}`);
        return;
      }

      // Update user preference in backend (only for authenticated users)
      if (user && user.user_type !== 'GUEST') {
        await updateUser({ data: { language_code: locale } });
      }

      // Switch i18n locale (works for both guests and authenticated users)
      switchLocale(locale);
    },
    [user, updateUser, switchLocale]
  );

  return {
    currentLocale: currentLocale as SupportedLocale,
    supportedLocales: SUPPORTED_LOCALES,
    changeLanguage,
    isSupported: (locale: string): locale is SupportedLocale =>
      SUPPORTED_LOCALES.includes(locale as SupportedLocale),
  };
}
