import { createApiError, type ApiError } from './types';

/**
 * Pull the message (and machine code) out of a FastAPI error body. Three shapes arrive:
 * - `{"detail": "text"}` — `HTTPException(detail="...")`
 * - `{"detail": {"message", "code", "name"}}` — `BackendException` handlers and `HTTPException(detail={...})`
 * - `{"detail": [{"msg", "loc", ...}]}` — 422 request validation
 */
function readDetail(body?: Record<string, unknown>): { message: string | null; code?: string } {
  const detail = body?.detail;
  if (typeof detail === 'string') return { message: detail };
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined;
    return { message: typeof first?.msg === 'string' ? first.msg : null };
  }
  if (detail && typeof detail === 'object') {
    const { message, code } = detail as Record<string, unknown>;
    return {
      message: typeof message === 'string' ? message : null,
      code: typeof code === 'string' ? code : undefined,
    };
  }
  return { message: typeof body?.message === 'string' ? body.message : null };
}

/**
 * Classify HTTP error by status code
 */
export function classifyHttpError(status: number, body?: Record<string, unknown>): ApiError {
  const { message, code } = readDetail(body);

  // Recoverable = server errors or rate limiting (can retry)
  // Not recoverable = client errors (retrying won't help)
  const recoverable = status >= 500 || status === 429 || status === 0;

  return createApiError(message ?? `Request failed (${status})`, status, recoverable, code);
}

/**
 * Classify network error (no response)
 */
export function classifyNetworkError(error: Error): ApiError {
  // Offline
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return createApiError('You are offline. Please check your connection.', 0, true);
  }

  // Timeout
  if (error.name === 'AbortError' || error.message?.includes('timeout')) {
    return createApiError('Request timed out. Please try again.', 0, true);
  }

  // Generic network error
  return createApiError('Network error. Please check your connection.', 0, true);
}

/**
 * Get user-friendly message from any error
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
}
