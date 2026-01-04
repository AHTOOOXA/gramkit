import { useRouter } from 'vue-router';
import { HOME_ROUTE } from '@app/router/router';

/**
 * App-specific navigation helpers.
 *
 * Provides convenient methods for navigating to common routes in the app.
 * This is app-specific business logic, not generic infrastructure.
 */
export function useNavigation() {
  const router = useRouter();

  const goHome = () => router.push(HOME_ROUTE);
  const goBack = () => router.back();

  return {
    goHome,
    goBack,
  };
}
