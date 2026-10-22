import type { MockUser } from '@core/platform-mock';

/**
 * Mock users for platform testing in debug mode (fake data — replace freely)
 */
export const MOCK_USERS: MockUser[] = [
  {
    user_id: 123456789,
    username: 'alex_demo',
    display_name: 'Alex Demo',
    avatar_url: undefined,
    user_type: 'REGISTERED',
  },
  {
    user_id: 987654321,
    username: 'dev',
    display_name: 'Dev User',
    avatar_url: undefined,
    user_type: 'REGISTERED',
  },
  {
    user_id: 111222333,
    username: 'sam_demo',
    display_name: 'Sam Demo',
    avatar_url: undefined,
    user_type: 'REGISTERED',
  },
];
