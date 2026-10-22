import { useState, useCallback, useEffect } from 'react';

export interface MockUser {
  user_id: number;
  username: string;
  first_name: string;
  last_name?: string;
  photo_url?: string;
  user_type: 'REGISTERED';
  app_username: string;
}

export interface UsePlatformMockReturn {
  /** TG-platform mock: report `platform: 'telegram'` instead of web. */
  isMockEnabled: boolean;
  toggleMock: () => void;
  /** Login-as mock: authenticate as the selected mock user. Independent of TG mock. */
  isUserMockEnabled: boolean;
  toggleUserMock: () => void;
  selectedUser: MockUser | null;
  availableUsers: MockUser[];
  setSelectedUser: (user: MockUser | null) => void;
}

// Two INDEPENDENT debug switches (deliberately decoupled):
//   STORAGE_KEY   → TG-platform mock: usePlatform() reports platform 'telegram'.
//   USER_MOCK_KEY → login-as: inject the selected user's initData + send the
//                   Mock-Platform auth header so the backend authenticates as them.
// Picking a user enables login-as only — you can be a real user on the web platform.
const STORAGE_KEY = 'telegram-platform-mock';
const USER_MOCK_KEY = 'telegram-platform-login-as';
const USER_STORAGE_KEY = 'telegram-platform-mock-user';

// Injectable mock users (provided from app layer)
let _mockUsers: MockUser[] = [];

/**
 * Initialize mock users (call from app bootstrap)
 */
export function initPlatformMock(users: MockUser[]): void {
  _mockUsers = users;
}

/**
 * Create initData string from MockUser
 * Uses custom mock format (not Telegram format) for backend compatibility
 */
export function createMockInitDataString(user: MockUser): string {
  // Send user object in MockUser format (user_id, not id)
  // Backend expects this exact format to identify and create mock users
  const userJson = JSON.stringify({
    user_id: user.user_id,
    username: user.username,
    first_name: user.first_name,
    last_name: user.last_name || '',
    user_type: user.user_type,
    app_username: user.app_username,
    photo_url: user.photo_url,
  });

  const encodedUser = encodeURIComponent(userJson);

  // Create mock initData string with mock_init_data=true flag
  // This format matches Vue template and backend expectations
  const params = [
    `mock_init_data=true`, // Flag for backend to recognize mock users
    `user=${encodedUser}`,
  ];

  return params.join('&');
}

/**
 * Inject mock initData into Telegram WebApp object
 * Call this BEFORE SDK initialization
 * SECURITY: This creates a mock Telegram environment for testing only
 */
export function injectMockInitData(user: MockUser): void {
  const initDataString = createMockInitDataString(user);

  // Inject into window.Telegram.WebApp.initData for SDK to read
  if (typeof window !== 'undefined') {
    try {
      // Create mock Telegram object if it doesn't exist
      if (!(window as any).Telegram) {
        (window as any).Telegram = {};
      }

      // Get existing WebApp properties to preserve them
      const existingWebApp = (window as any).Telegram.WebApp || {};
      const preservedProps: Record<string, any> = {};

      // Copy existing properties (except initData which we're overriding)
      for (const key of Object.keys(existingWebApp)) {
        if (key !== 'initData') {
          preservedProps[key] = existingWebApp[key];
        }
      }

      // Replace the entire WebApp object with a new one that has our initData
      (window as any).Telegram.WebApp = {
        ...preservedProps,
        initData: initDataString,
      };

      console.log('[Mock] Injected mock initData into Telegram.WebApp for user:', user.username, 'ID:', user.user_id);
    } catch (error) {
      console.warn('[Mock] Failed to inject initData:', error);
    }
  }
}

/**
 * Get the currently selected mock user from localStorage
 */
export function getSelectedMockUser(): MockUser | null {
  if (typeof window === 'undefined') return null;

  try {
    // The selected user is only relevant when logging in as them (login-as),
    // which is independent of the TG-platform mock switch.
    const loginAsEnabled = localStorage.getItem(USER_MOCK_KEY) === 'true';
    if (!loginAsEnabled) return null;

    const stored = localStorage.getItem(USER_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
    return _mockUsers[0] || null;
  } catch {
    return null;
  }
}

/**
 * Check if TG-platform mock is enabled (report platform as Telegram).
 */
export function isMockModeEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

/**
 * Check if login-as (user mock) is enabled — authenticate as the selected mock
 * user. Independent of TG-platform mock; gates initData injection + the
 * Mock-Platform auth header.
 */
export function isUserMockEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(USER_MOCK_KEY) === 'true';
  } catch {
    return false;
  }
}

/**
 * Hook for managing Telegram platform mocking in debug mode
 *
 * Auto-initializes on first use, persists state to localStorage.
 * Includes user account selection for testing different user scenarios.
 *
 * IMPORTANT: Call initPlatformMock(users) from app bootstrap before using this hook.
 */
export function usePlatformMock(): UsePlatformMockReturn {
  // Initialize state from localStorage
  const [isMockEnabled, setIsMockEnabled] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });

  const [isUserMockEnabledState, setIsUserMockEnabled] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      return localStorage.getItem(USER_MOCK_KEY) === 'true';
    } catch {
      return false;
    }
  });

  const [selectedUser, setSelectedUserState] = useState<MockUser | null>(() => {
    if (typeof window === 'undefined') return _mockUsers[0] || null;
    try {
      const stored = localStorage.getItem(USER_STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
      return _mockUsers[0] || null;
    } catch {
      return _mockUsers[0] || null;
    }
  });

  // Persist mock enabled state to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_KEY, isMockEnabled.toString());
    } catch (error) {
      console.warn('Failed to save platform mock state to localStorage:', error);
    }
  }, [isMockEnabled]);

  // Persist login-as state to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(USER_MOCK_KEY, isUserMockEnabledState.toString());
    } catch (error) {
      console.warn('Failed to save login-as state to localStorage:', error);
    }
  }, [isUserMockEnabledState]);

  // Persist selected user to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      if (selectedUser) {
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(selectedUser));
      } else {
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    } catch (error) {
      console.warn('Failed to save platform mock user to localStorage:', error);
    }
  }, [selectedUser]);

  const toggleMock = useCallback(() => {
    setIsMockEnabled((prev) => !prev);
  }, []);

  const toggleUserMock = useCallback(() => {
    setIsUserMockEnabled((prev) => !prev);
  }, []);

  const setSelectedUser = useCallback((user: MockUser | null) => {
    setSelectedUserState(user);
  }, []);

  return {
    isMockEnabled,
    toggleMock,
    isUserMockEnabled: isUserMockEnabledState,
    toggleUserMock,
    selectedUser,
    availableUsers: _mockUsers,
    setSelectedUser,
  };
}
