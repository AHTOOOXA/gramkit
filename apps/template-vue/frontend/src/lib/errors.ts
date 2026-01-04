/**
 * Base error for initialization failures
 */
export class InitializationError extends Error {
  constructor(
    message: string,
    public cause?: unknown
  ) {
    super(message);
    this.name = 'InitializationError';
  }
}

/**
 * SDK not ready or unavailable
 */
export class SDKError extends Error {
  constructor(
    message: string,
    public cause?: unknown
  ) {
    super(message);
    this.name = 'SDKError';
  }
}

/**
 * Process start endpoint failed
 */
export class ProcessStartError extends Error {
  constructor(
    message: string,
    public cause?: unknown
  ) {
    super(message);
    this.name = 'ProcessStartError';
  }
}

/**
 * Invalid or missing initData
 */
export class InitDataError extends Error {
  constructor(
    message: string,
    public cause?: unknown
  ) {
    super(message);
    this.name = 'InitDataError';
  }
}
