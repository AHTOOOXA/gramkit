import posthog from 'posthog-js';

let isInitialized = false;
let hasWarned = false;

export function usePostHog() {
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
