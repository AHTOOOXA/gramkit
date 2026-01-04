import './style.css';

// CRITICAL: Inject mock data BEFORE any Telegram SDK imports
// The @twa-dev/sdk freezes window.Telegram.WebApp on import
// Use @core/platform-mock which doesn't import the SDK
import {
  initPlatformMock,
  injectMockInitData,
  isMockModeEnabled,
  getSelectedMockUser,
} from '@core/platform-mock';
import { MOCK_USERS } from '@app/config/mockUsers';

// Initialize mock IMMEDIATELY before any SDK imports
initPlatformMock(MOCK_USERS);
if (isMockModeEnabled()) {
  let selectedUser = getSelectedMockUser();
  if (!selectedUser?.user_id || !selectedUser?.username) {
    console.warn('[Mock] Invalid user in localStorage, using default');
    selectedUser = MOCK_USERS[0] ?? null;
  }
  if (selectedUser) {
    injectMockInitData(selectedUser);
    console.log('[Mock] Injected initData for user:', selectedUser.username);
  }
}

// Now safe to import modules that use Telegram SDK
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query';
import App from './App.vue';
import Router from '@app/router/router';
import { usePlatform } from '@core/platform';
import { LanguageServiceKey } from '@core/injection-keys';
import { isApiError } from '@core/errors';
import { initApp } from '@app/composables/useAppInit';
import { createLanguageService } from '@app/services/language.service';
import { i18n } from '@app/i18n';
import { initSentry, Sentry } from '@/lib/sentry';
import { configureApiClient } from '@/config/kubb-config';

/**
 * @todo async lottie-player loading
 * @todo preload all icons
 * @todo describe thumbnail generation and work
 * @todo describe next/main buttons simulation
 * @todo close confirmation
 * @todo cancel payment toast
 */

const platform = usePlatform();
const { ready, showAlert, setHeaderColor, expand, disableVerticalSwipes } = platform;

// dumb vue router was messing the hash on refresh
const { hash } = location;
let needFixHash = true;

setHeaderColor('#111213');
expand();

if (platform.telegramPlatform !== 'unknown') {
  switch (platform.telegramPlatform) {
    case 'android':
    case 'android_x':
    case 'web':
    case 'weba':
    case 'tdesktop':
      document.body.classList.add('is-material');
      break;
    case 'ios':
    case 'macos':
      document.body.classList.add('is-apple');
      break;
    default:
      document.body.classList.add(`is-${platform.telegramPlatform}`);
      break;
  }
}

/**
 * Some clients may use material/apple base styles, but has some overrides
 * For instance, WebK uses material but more rounded and clean
 */
document.body.classList.add(`is-exact-${platform.telegramPlatform}`);

/**
 * Prepare app data
 *
 * @todo load icons
 * @todo prepare image thumbs
 */
const pinia = createPinia();
const app = createApp(App);

initSentry(app);

// Simple error handlers that just redirect
app.config.errorHandler = (error, instance, info) => {
  console.error('Vue error:', error);
  Sentry.captureException(error, {
    extra: { componentInfo: info },
  });
  Router.push('/error');
};

window.addEventListener('unhandledrejection', event => {
  console.error('Unhandled promise rejection:', event.reason);
  Sentry.captureException(event.reason);
  Router.push('/error');
});

window.addEventListener('error', event => {
  console.error('Runtime error:', event.error);
  Sentry.captureException(event.error);
  Router.push('/error');
});

Router.onError(error => {
  console.error('Router error:', error);
  Sentry.captureException(error);
  Router.push('/error');
});

app.use(pinia);
app.use(i18n);

// Create QueryClient instance with smart retry logic based on error classification
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30000,
      // Smart retry based on error classification
      retry: (failureCount, error) => {
        // ApiError from our classification system
        if (isApiError(error)) {
          // Don't retry non-recoverable errors (4xx client errors)
          if (!error.recoverable) return false;

          // Retry recoverable errors (5xx, network) up to 3 times
          return failureCount < 3;
        }

        // Unknown errors: retry once
        return failureCount < 1;
      },
      // Exponential backoff with max 30 seconds
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
    },
    mutations: {
      // Don't retry mutations by default (user can retry manually)
      retry: false,
    },
  },
});

app.use(VueQueryPlugin, { queryClient });

// Provide language service for core components
app.provide(LanguageServiceKey, createLanguageService());

// Initialize Eruda in dev mode
if (import.meta.env.VITE_DEBUG === 'true') {
  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/eruda';
  script.onload = () => {
    // @ts-expect-error - eruda is loaded dynamically
    window.eruda.init();
  };
  document.body.appendChild(script);
}

// Configure API client BEFORE any API calls
// Note: Mock initialization moved to top of file (before SDK imports)
configureApiClient();

// Initialize app before mounting
(async () => {
  try {
    await initApp(queryClient);

    // Only initialize router and mount app after stores are ready
    app.use(Router);

    // dumb vue router was messing the hash on refresh
    Router.afterEach(() => {
      if (needFixHash) {
        location.hash = hash;
        needFixHash = false;
      }
    });

    app.mount('#app');

    requestAnimationFrame(() => {
      disableVerticalSwipes();
      ready();
    });
  } catch (error) {
    console.error('Failed to initialize app:', error);
    showAlert('Failed to initialize app');
  }
})();
