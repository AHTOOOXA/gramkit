import { useMediaQuery } from './useMediaQuery';
import type { Ref } from 'vue';

const MOBILE_BREAKPOINT = 768;

/**
 * Mobile device detection using media query.
 * Returns reactive boolean for whether viewport is mobile-sized.
 *
 * @returns Ref<boolean> - true if viewport width < 768px, false otherwise
 *
 * @example
 * const isMobile = useMobile();
 * <template>
 *   <div v-if="isMobile">Mobile view</div>
 *   <div v-else>Desktop view</div>
 * </template>
 */
export function useMobile(): Ref<boolean> {
  return useMediaQuery(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
}
