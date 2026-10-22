import posthog from 'posthog-js';

let isInitialized = false;
let hasWarned = false;

const noopPosthog = new Proxy({} as typeof posthog, {
  get: () => () => {},
});

export function usePostHog() {
  if (import.meta.env.SSR) {
    return { posthog: noopPosthog };
  }

  const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
  const posthogHost = import.meta.env.VITE_POSTHOG_HOST;

  // Only initialize once if analytics is configured
  if (!isInitialized && posthogKey) {
    posthog.init(posthogKey, {
      api_host: posthogHost,
      capture_pageview: false,
      autocapture: false,
      capture_heatmaps: false,
      sanitize_properties: (properties, eventName) => {
        if (properties['$current_url']) {
          const url = new URL(properties['$current_url']);
          url.hash = url.hash.split('?')[0].split('#tgWebAppData')[0];
          properties['$current_url'] = url.toString();
        }
        return properties;
      },
    });
    // Same super property as the backend's events, so both split by release. Set by the app's
    // vite.config (package.json version); absent in apps that don't define it.
    const appVersion = import.meta.env.VITE_APP_VERSION;
    if (appVersion) {
      posthog.register({ $app_version: appVersion });
    }
    isInitialized = true;
  } else if (!posthogKey && !hasWarned) {
    console.warn(
      'PostHog analytics not configured. Analytics will be disabled.\n' +
      'To enable: Set VITE_POSTHOG_KEY and VITE_POSTHOG_HOST in your .env file'
    );
    hasWarned = true;
  }

  return {
    posthog,
  };
}
