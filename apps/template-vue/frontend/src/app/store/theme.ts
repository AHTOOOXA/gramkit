import { useColorMode } from '@vueuse/core';

/**
 * Global theme mode (light/dark)
 *
 * Uses VueUse's useColorMode with:
 * - Automatic localStorage persistence
 * - System preference detection
 * - Smooth transitions
 */
export const mode = useColorMode({
  attribute: 'class',
  storageKey: 'vueuse-color-scheme',
  disableTransition: false,
});
