/**
 * Simplified API error - only what's actually used
 */
export interface ApiError extends Error {
  status: number;
  recoverable: boolean;
  /** Machine-readable error code from `detail.code` (e.g. "NoChatMessagesError"), when the backend sends one */
  code?: string;
}

/**
 * Create an ApiError instance
 */
export function createApiError(message: string, status: number, recoverable: boolean, code?: string): ApiError {
  const error = new Error(message) as ApiError;
  error.name = 'ApiError';
  error.status = status;
  error.recoverable = recoverable;
  if (code) error.code = code;
  return error;
}

/**
 * Type guard to check if error is ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && 'status' in error && 'recoverable' in error;
}
