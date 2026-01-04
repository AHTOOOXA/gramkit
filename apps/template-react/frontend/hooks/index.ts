// Auth hooks
export { useAuth } from './useAuth';

// Focused mutation hooks
export { useUpdateUser } from './useUpdateUser';
export { useLogout } from './useLogout';

// Email auth hooks
export { useEmailLogin, useEmailSignup, useEmailLink } from './useEmailAuth';

// Utility hooks
export { useNavigation } from './useNavigation';
export { useAppTheme } from './useAppTheme';
export { useMediaQuery } from './useMediaQuery';
export { useScrollReveal } from './useScrollReveal';

// Platform hooks (re-export)
export {
  useTelegram,
  usePlatform,
  useScroll,
  useLayout,
} from '@tma-platform/core-react';
