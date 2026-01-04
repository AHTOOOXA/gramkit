import { createApiError, type ApiError } from './types';

/**
 * Classify HTTP error by status code
 * Expects FastAPI format: {"detail": "message"}
 */
export function classifyHttpError(status: number, body?: Record<string, unknown>): ApiError {
  // Extract message from FastAPI format
  const message = (typeof body?.detail === 'string' ? body.detail : null)
    ?? (typeof body?.message === 'string' ? body.message : null)
    ?? `Request failed (${status})`;

  // Recoverable = server errors or rate limiting (can retry)
  // Not recoverable = client errors (retrying won't help)
  const recoverable = status >= 500 || status === 429 || status === 0;

  return createApiError(message, status, recoverable);
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
