'use client';

import {
  injectMockInitData,
  usePlatformMock,
} from '@tma-platform/core-react/platform';
import { usePlatform } from '@/hooks';

export function DebugPanel() {
  const platformMock = usePlatformMock();
  const { isTelegram, isTelegramMobile, isTelegramDesktop, tgPlatform } = usePlatform();

  const handleToggleMock = () => {
    platformMock.toggleMock();

    // Update platform cookie immediately based on new mock state
    // This prevents race condition where server reads old cookie before PlatformDetector runs
    if (typeof window !== 'undefined') {
      const newMockState = !platformMock.isMockEnabled;
      const platform = newMockState ? 'telegram' : 'web';

      // Persist to localStorage BEFORE reload (useEffect won't run in time)
      localStorage.setItem('telegram-platform-mock', newMockState.toString());

      // Set app-namespaced cookie (prevents conflicts between apps)
      const cookieName = `${process.env.APP_NAME ?? 'app'}-platform`;
      document.cookie = `${cookieName}=${platform}; path=/; max-age=31536000; samesite=lax`;

      // If turning mock OFF, clear the mock Telegram object to prevent PlatformDetector
      // from detecting it as real Telegram environment
      if (!newMockState) {
        interface TelegramWindow {
          Telegram?: { WebApp?: { initData?: string } };
        }
        const win = window as TelegramWindow;
        if (win.Telegram?.WebApp?.initData) {
          delete win.Telegram.WebApp.initData;
        }
      }

      // Reload to re-initialize SDK with/without mock data
      window.location.reload();
    }
  };

  const handleUserChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const userId = parseInt(e.target.value);
    const selectedUser =
      platformMock.availableUsers.find((u) => u.user_id === userId) ?? null;

    if (selectedUser) {
      // Update selected user in storage
      platformMock.setSelectedUser(selectedUser);
      // Inject new mock data
      injectMockInitData(selectedUser);
    }

    // Reload to re-initialize SDK with new user
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  // Only show in development
  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div className="fixed top-2 md:top-16 left-2 z-[9999] flex flex-col gap-1 text-xs opacity-30 transition-opacity hover:opacity-100">
      {/* Mock toggle button */}
      <button
        onClick={handleToggleMock}
        className={`cursor-pointer rounded px-2 py-1 font-medium shadow transition-colors ${
          platformMock.isMockEnabled
            ? 'bg-green-500 text-white hover:bg-green-600'
            : 'bg-yellow-500 text-black hover:bg-yellow-600'
        }`}
      >
        {platformMock.isMockEnabled ? '📱 TG ON' : '🌐 TG OFF'}
      </button>

      {/* Platform detection debug info */}
      <div className="rounded bg-purple-600 px-2 py-1 font-mono text-white shadow">
        {isTelegram ? `TG:${tgPlatform}` : 'Web'} | {isTelegramMobile ? 'mob' : isTelegramDesktop ? 'desk' : 'web'}
      </div>

      {/* User selector (only when mock is enabled) */}
      {platformMock.isMockEnabled &&
        platformMock.availableUsers.length > 0 && (
          <select
            value={platformMock.selectedUser?.user_id ?? ''}
            onChange={handleUserChange}
            className="cursor-pointer rounded bg-blue-500 px-2 py-1 font-medium text-white shadow outline-none hover:bg-blue-600"
          >
            {platformMock.availableUsers.map((user) => (
              <option
                key={user.user_id}
                value={user.user_id}
                className="bg-gray-800"
              >
                {user.username}
              </option>
            ))}
          </select>
        )}
    </div>
  );
}
