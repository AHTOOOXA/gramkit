import * as Sentry from '@sentry/react';

export function initSentry() {
  // Only initialize in production to prevent dev noise and accidental DSN usage
  if (process.env.NODE_ENV === 'production') {
    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
      environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? 'development',
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
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
  const stackString = (error as Error)?.stack ?? '';
  return (
    errorString.includes('posthog') ||
    stackString.includes('posthog') ||
    stackString.includes('app.posthog.com')
  );
}

export { Sentry };
