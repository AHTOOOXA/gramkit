import { computed, ref, watch, type WritableComputedRef } from 'vue';

export interface MockUser {
  user_id: number;
  username: string;
  display_name?: string;
  avatar_url?: string;
  user_type: 'REGISTERED';
}

export interface UsePlatformMockReturn {
  isMockEnabled: WritableComputedRef<boolean>;
  toggleMock: () => void;
  selectedUser: WritableComputedRef<MockUser | null>;
  availableUsers: MockUser[];
  setSelectedUser: (user: MockUser | null) => void;
}

const STORAGE_KEY = 'telegram-platform-mock';
const USER_STORAGE_KEY = 'telegram-platform-mock-user';
const _rawMockEnabled = ref(false);
const _selectedUser = ref<MockUser | null>(null);
let isInitialized = false;

// Injectable mock users (provided from app layer)
let _mockUsers: MockUser[] = [];

/**
 * Initialize mock users (call from app bootstrap)
 */
export function initPlatformMock(users: MockUser[]): void {
  _mockUsers = users;
  // Set default user if none selected and users are provided
  if (!_selectedUser.value && users.length > 0) {
    _selectedUser.value = users[0];
  }
}

// Auto-initialize on first access (lazy loading)
const mockState = computed({
  get() {
    if (!isInitialized) {
      try {
        const storedValue = localStorage.getItem(STORAGE_KEY);
        _rawMockEnabled.value = storedValue === 'true';

        // Load selected user from localStorage
        const storedUser = localStorage.getItem(USER_STORAGE_KEY);
        if (storedUser) {
          _selectedUser.value = JSON.parse(storedUser);
        } else if (_mockUsers.length > 0) {
          // Default to first user if none selected
          _selectedUser.value = _mockUsers[0];
        }

        isInitialized = true;
      } catch (error) {
        console.warn('Failed to read platform mock state from localStorage:', error);
        _rawMockEnabled.value = false;
        _selectedUser.value = _mockUsers[0] || null; // Default user
        isInitialized = true;
      }
    }
    return _rawMockEnabled.value;
  },
  set(value: boolean) {
    _rawMockEnabled.value = value;
  },
});

// Selected user computed property
const selectedUserState = computed({
  get() {
    // Trigger initialization if needed
    void mockState.value;
    return _selectedUser.value;
  },
  set(value: MockUser | null) {
    _selectedUser.value = value;
  },
});

// Toggle mock state
function toggleMock(): void {
  mockState.value = !mockState.value;
}

// Set selected user
function setSelectedUser(user: MockUser | null): void {
  selectedUserState.value = user;
}

// Watch for changes and persist to localStorage
watch(_rawMockEnabled, newValue => {
  try {
    localStorage.setItem(STORAGE_KEY, newValue.toString());
  } catch (error) {
    console.warn('Failed to save platform mock state to localStorage:', error);
  }
});

// Watch for user changes and persist to localStorage
watch(_selectedUser, newUser => {
  try {
    if (newUser) {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(newUser));
    } else {
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  } catch (error) {
    console.warn('Failed to save platform mock user to localStorage:', error);
  }
});

/**
 * Create mock initData string for a user
 */
export function createMockInitDataString(user: MockUser): string {
  const displayName = user.display_name ?? user.username ?? 'User';
  const userJson = JSON.stringify({
    id: user.user_id,
    user_id: user.user_id,
    first_name: displayName.split(' ')[0] ?? displayName,
    last_name: displayName.split(' ').slice(1).join(' ') || undefined,
    username: user.username,
    photo_url: user.avatar_url,
    language_code: 'en',
    is_premium: false,
  });

  const encodedUser = encodeURIComponent(userJson);

  // Create mock initData string with mock_init_data=true flag
  const params = [
    'mock_init_data=true',
    `user=${encodedUser}`,
  ];

  return params.join('&');
}

/**
 * Inject mock initData into window.Telegram.WebApp for API client to read
 */
export function injectMockInitData(user: MockUser): void {
  const initDataString = createMockInitDataString(user);

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

      console.log('[Mock] Injected mock initData for user:', user.username);
    } catch (error) {
      console.warn('[Mock] Failed to inject initData:', error);
    }
  }
}

/**
 * Get currently selected mock user from localStorage
 */
export function getSelectedMockUser(): MockUser | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(USER_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

/**
 * Check if mock mode is enabled
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
 * Composable for managing Telegram platform mocking in debug mode
 *
 * Auto-initializes on first property access, no manual setup required.
 * Now includes user account selection for testing different user scenarios.
 *
 * IMPORTANT: Call initPlatformMock(users) from app bootstrap before using this composable.
 */
export function usePlatformMock(): UsePlatformMockReturn {
  return {
    isMockEnabled: mockState,
    toggleMock,
    selectedUser: selectedUserState,
    availableUsers: _mockUsers,
    setSelectedUser,
  };
}
