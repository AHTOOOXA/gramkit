import { ref, onMounted, onUnmounted, type Ref } from 'vue';

/**
 * Generic media query detection composable.
 * Returns reactive boolean for whether the media query matches.
 *
 * @param query - CSS media query string (e.g., "(max-width: 768px)")
 * @returns Ref<boolean> - true if query matches, false otherwise
 *
 * @example
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * const isDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
 */
export function useMediaQuery(query: string): Ref<boolean> {
  const matches = ref(false);
  let mediaQueryList: MediaQueryList | null = null;

  const updateMatches = (e: MediaQueryListEvent | MediaQueryList) => {
    matches.value = e.matches;
  };

  onMounted(() => {
    // Check if window exists (SSR safety)
    if (typeof window === 'undefined') {
      return;
    }

    mediaQueryList = window.matchMedia(query);
    matches.value = mediaQueryList.matches;

    // Listen for changes
    mediaQueryList.addEventListener('change', updateMatches);
  });

  onUnmounted(() => {
    if (mediaQueryList) {
      mediaQueryList.removeEventListener('change', updateMatches);
    }
  });

  return matches;
}
