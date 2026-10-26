// Auth hooks
export { useAuth } from './useAuth';

// Focused mutation hooks
export { useUpdateUser } from './useUpdateUser';
export { useLogout } from './useLogout';

// Email auth hooks
export { useEmailLogin, useEmailSignup, useEmailLink } from './useEmailAuth';

// Admin panel hooks
export { useAdminGuard } from './useAdminGuard';
export { useAdminLabels } from './useAdminLabels';
export {
  useAdminList,
  type AdminList,
  type AdminListFilters,
  type AdminListParams,
  type AdminSortDir,
  type UseAdminListOptions,
} from './useAdminList';
export { useDebouncedValue } from './useDebouncedValue';

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
