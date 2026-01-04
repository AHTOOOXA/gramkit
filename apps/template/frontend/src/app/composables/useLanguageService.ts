import { computed, watch } from 'vue';
import { useQueryClient } from '@tanstack/vue-query';
import { i18n, saveLocale, SUPPORTED_LOCALES, type SupportedLocale } from '@app/i18n';
import { useUpdateCurrentUserUsersMePatch, useGetCurrentUserUsersMeGet, getCurrentUserUsersMeGetQueryKey } from '@/gen/hooks';

export type { SupportedLocale };

/**
 * Language service composable with smart guest handling.
 *
 * Features:
 * - Only updates backend for authenticated users (not guests)
 * - Always updates UI locale for immediate feedback
 * - Syncs user language preference to i18n locale
 */
export function useLanguageService() {
  const queryClient = useQueryClient();
  const locale = i18n.global.locale;

  const { data: user } = useGetCurrentUserUsersMeGet({
    query: { staleTime: 5 * 60 * 1000 },
  });

  const { mutateAsync: updateUser } = useUpdateCurrentUserUsersMePatch();

  const currentLocale = computed(() => locale.value as SupportedLocale);
  const isGuest = computed(() => !user.value || user.value.user_type === 'GUEST');

  // Sync language between user profile and i18n
  watch(
    [() => user.value?.language_code, () => user.value?.user_type],
    ([userLang, userType]) => {
      // Skip for guests
      if (!userType || userType === 'GUEST') {
        return;
      }

      // User is authenticated
      if (userLang) {
        // User has a saved language preference - use it (backend wins)
        const lang = userLang as SupportedLocale;
        if (SUPPORTED_LOCALES.includes(lang) && lang !== locale.value) {
          locale.value = lang;
          saveLocale(lang); // Keep localStorage in sync
        }
      } else {
        // New user with no language_code - save their current locale to backend
        // This persists their guest choice (from localStorage) to their profile
        const currentLang = locale.value as SupportedLocale;
        if (SUPPORTED_LOCALES.includes(currentLang)) {
          void updateUser({ data: { language_code: currentLang } }).then(() => {
            queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() });
          }).catch((error) => {
            console.error('Failed to save initial language preference:', error);
          });
        }
      }
    },
    { immediate: true }
  );

  const changeLanguage = async (newLocale: SupportedLocale) => {
    if (!SUPPORTED_LOCALES.includes(newLocale)) {
      console.error(`Unsupported locale: ${newLocale}`);
      return;
    }

    // Always update UI locale immediately (works for both guests and authenticated)
    locale.value = newLocale;

    // Save to localStorage for persistence across refreshes
    saveLocale(newLocale);

    // Only update backend for authenticated users (not guests)
    if (!isGuest.value) {
      try {
        await updateUser({ data: { language_code: newLocale } });
        queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() });
      } catch (error) {
        console.error('Failed to save language preference:', error);
        // UI is already updated, so user sees the change even if backend fails
      }
    }
  };

  return {
    currentLocale,
    supportedLocales: SUPPORTED_LOCALES,
    changeLanguage,
    isGuest,
    isSupported: (loc: string): loc is SupportedLocale =>
      SUPPORTED_LOCALES.includes(loc as SupportedLocale),
  };
}
