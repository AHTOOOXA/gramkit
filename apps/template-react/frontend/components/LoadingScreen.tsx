'use client';

/**
 * Invisible loading screen - just background color for seamless transition.
 * Shows while waiting for /process_start API call to complete.
 */
export const LoadingScreen = () => {
  return <div className="h-screen w-screen bg-background" />;
};
