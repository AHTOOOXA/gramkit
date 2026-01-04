/**
 * Simplified API error - only what's actually used
 */
export interface ApiError extends Error {
  status: number;
  recoverable: boolean;
}

/**
 * Create an ApiError instance
 */
export function createApiError(message: string, status: number, recoverable: boolean): ApiError {
  const error = new Error(message) as ApiError;
  error.name = 'ApiError';
  error.status = status;
  error.recoverable = recoverable;
  return error;
}

/**
 * Type guard to check if error is ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && 'status' in error && 'recoverable' in error;
}
