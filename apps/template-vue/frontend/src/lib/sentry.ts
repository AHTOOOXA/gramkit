import * as Sentry from '@sentry/vue';
import type { App } from 'vue';

export function initSentry(app: App) {
  // Only initialize in production to prevent dev noise and accidental DSN usage
  if (import.meta.env.PROD) {
    Sentry.init({
      app,
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.VITE_ENVIRONMENT ?? 'development',
      tracesSampleRate: 1.0, // 100% - fine for low traffic (<1k DAU)
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],
      tracePropagationTargets: [
        'localhost',
        /^https:\/\/local\.gramkit\.ru/,
        /^https:\/\/.*\.gramkit\.ru/,
      ],
      replaysSessionSampleRate: 0.5,  // 50% of normal sessions
      replaysOnErrorSampleRate: 1.0,  // 100% when errors occur
      beforeSend(event, hint) {
        const error = hint.originalException;
        if (isPostHogError(error)) return null;
        if (event.contexts) {
          delete event.contexts.initData;
          delete event.contexts.telegram;
        }
        return event;
      },
    });
  }
}

function isPostHogError(error: unknown): boolean {
  const errorString = String(error);

  const stackString = (error as Error)?.stack ?? '';
  return (
    errorString.includes('posthog') ||
    stackString.includes('posthog') ||
    stackString.includes('app.posthog.com')
  );
}

export { Sentry };
